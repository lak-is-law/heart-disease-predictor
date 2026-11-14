"""components/lab_report_parser.py
Clinical NLP Lab Report Parser & Data Ingestion Pipeline.
Extracts 13 Cleveland Clinic biomarkers from unstructured clinical notes, discharge summaries,
lab panels (lipid, metabolic), and PDF/JSON/CSV documents.
Features scope-based clinical negation handling, false-positive elimination, zero-bias screening defaults,
and structured confidence scoring.
"""

from __future__ import annotations

import io
import json
import re
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO, Union

# Optional pypdf import with graceful fallback
try:
    import pypdf
except ImportError:
    pypdf = None


# Safe, non-pathological clinical screening baseline (Zero-Risk Bias)
SAFE_SCREENING_DEFAULTS: dict[str, Any] = {
    "age": 50,
    "sex": 1,         # Baseline male (imputed confidence = 0.0)
    "cp": 4,          # Class 4: Asymptomatic (NOT Class 1 typical angina!)
    "trestbps": 120,  # 120 mmHg normal systolic
    "chol": 195,      # 195 mg/dL normal serum cholesterol (<200)
    "fbs": 0,         # Fasting sugar <= 120 mg/dL (normal)
    "restecg": 0,     # Normal sinus rhythm / normal ECG
    "thalach": 150,   # Normal expected exercise peak heart rate
    "exang": 0,       # No exercise-induced angina
    "oldpeak": 0.0,   # 0.0 mm ST depression (NOT 1.2 mm!)
    "slope": 1,       # Upsloping (normal physiologic response)
    "ca": 0,          # 0 occluded/calcified coronary vessels (NOT 1!)
    "thal": 3,        # Normal myocardial perfusion
}


@dataclass
class BiomarkerExtraction:
    value: Union[int, float]
    extracted: bool
    confidence: float
    raw_match: str
    is_negated: bool = False


@dataclass
class ClinicalParseResult:
    biomarkers: dict[str, Union[int, float]]
    metadata: dict[str, BiomarkerExtraction]
    extracted_count: int
    total_count: int
    confidence_score: float
    missing_fields: list[str]
    warnings: list[str]
    safe_to_predict: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "biomarkers": self.biomarkers,
            "metadata": {k: asdict(v) for k, v in self.metadata.items()},
            "extracted_count": self.extracted_count,
            "total_count": self.total_count,
            "confidence_score": self.confidence_score,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "safe_to_predict": self.safe_to_predict,
        }


def is_clinically_negated(text: str, match_start: int, match_end: int | None = None, window_words: int = 6) -> bool:
    """Evaluates whether a target clinical finding falls within a negation scope.
    Checks pre-negation triggers within a sentence/clause boundary (1-6 words before match),
    and post-negation patterns (e.g. ': none', ': negative', ': absent') immediately following match.
    """
    pre_text = text[:match_start]
    # Split on sentence terminals and contrasting conjunctions
    clauses = re.split(r'[\.;\!\?\n]|(?:,\s*(?:but|however|although))', pre_text)
    last_clause = clauses[-1] if clauses else ""
    words = last_clause.strip().split()
    recent_words = " ".join(words[-window_words:]) if len(words) >= window_words else last_clause

    neg_pattern = r'\b(no|not|denies|denied|denying|negative\s+for|without|free\s+of|rules?\s+out|ruled\s+out|absence\s+of|zero|none|nil|unremarkable\s+for)\b'
    if re.search(neg_pattern, recent_words, re.IGNORECASE):
        return True

    if match_end is not None:
        post_text = text[match_end : match_end + 32]
        post_pattern = r'^\s*[:=-]?\s*(?:none|nil|negative|absent|0|no|denied|resolved|normal)\b'
        if re.search(post_pattern, post_text, re.IGNORECASE):
            return True

    return False


class ClinicalLabReportParser:
    """Robust parser extracting 13 clinical biomarkers from clinical text and documents."""

    def __init__(self, min_extracted_for_prediction: int = 3):
        self.min_extracted = min_extracted_for_prediction

    def parse_text(self, text: str) -> ClinicalParseResult:
        clean = text.replace("\r", " ")
        extracted: dict[str, BiomarkerExtraction] = {}
        missing_fields: list[str] = []
        warnings: list[str] = []

        # ------------------------------------------------------------------ 1. age
        m_age = re.search(r'\b(?:patient\s+)?age[\s:=]+([1-9][0-9])\b', clean, re.IGNORECASE)
        if not m_age:
            m_age = re.search(r'\b([1-9][0-9])[\s-]*(?:yo\b|y\.o\.|years?[\s-]old|years?\s+of\s+age)\b', clean, re.IGNORECASE)
        if m_age:
            val = int(m_age.group(1))
            val = max(18, min(100, val))
            extracted["age"] = BiomarkerExtraction(val, True, 0.98, m_age.group(0))
        else:
            extracted["age"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["age"], False, 0.0, "imputed_baseline")
            missing_fields.append("age")

        # ------------------------------------------------------------------ 2. sex (1: Male, 0: Female)
        m_sex_exp = re.search(r'\b(?:sex|gender)[\s:=]+(female|woman|f\b|male|man|m\b)', clean, re.IGNORECASE)
        if m_sex_exp:
            s_val = 0 if re.match(r'^(?:female|woman|f)$', m_sex_exp.group(1), re.IGNORECASE) else 1
            extracted["sex"] = BiomarkerExtraction(s_val, True, 0.99, m_sex_exp.group(0))
        else:
            m_fem = re.search(r'\b(female|woman|lady|she|her)\b', clean, re.IGNORECASE)
            m_male = re.search(r'\b(male|gentleman|man|he|him|his)\b', clean, re.IGNORECASE)
            if m_fem and not m_male:
                extracted["sex"] = BiomarkerExtraction(0, True, 0.95, m_fem.group(0))
            elif m_male and not m_fem:
                extracted["sex"] = BiomarkerExtraction(1, True, 0.95, m_male.group(0))
            elif m_fem and m_male:
                s_val = 0 if m_fem.start() < m_male.start() else 1
                extracted["sex"] = BiomarkerExtraction(s_val, True, 0.85, "demographic_context_precedence")
            else:
                extracted["sex"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["sex"], False, 0.0, "imputed_male")
                missing_fields.append("sex")

        # ------------------------------------------------------------------ 3. cp (Chest Pain Type 1-4)
        m_asymp = re.search(r'\b(?:asymptomatic|no\s+(?:angina|chest\s+(?:pain|tightness|pressure|discomfort))|denies\s+(?:angina|chest\s+(?:pain|tightness|pressure|discomfort))|free\s+of\s+chest\s+pain)\b', clean, re.IGNORECASE)
        m_cp_any = re.search(r'\b(?:chest\s+(?:pain|discomfort)|angina)\b', clean, re.IGNORECASE)
        if m_asymp:
            extracted["cp"] = BiomarkerExtraction(4, True, 0.98, m_asymp.group(0), is_negated=True)
        elif m_cp_any and is_clinically_negated(clean, m_cp_any.start(), m_cp_any.end()):
            extracted["cp"] = BiomarkerExtraction(4, True, 0.95, clean[m_cp_any.start():m_cp_any.end()] + " (negated)", is_negated=True)
        else:
            m_nonang = re.search(r'\b(non-anginal|nonanginal|pleuritic|musculoskeletal|gastroesophageal|reflux)\s+(?:chest\s+)?(?:pain|discomfort)\b', clean, re.IGNORECASE)
            m_atyp = re.search(r'\b(atypical\s+(?:angina|chest\s+(?:pain|tightness|discomfort))|unlikely\s+ischemic)\b', clean, re.IGNORECASE)
            m_typ = re.search(r'\b(typical\s+angina|substernal\s+(?:pressure|heaviness|pain)|crushing\s+chest\s+(?:pain|pressure)|exertional\s+(?:angina|chest\s+pain))\b', clean, re.IGNORECASE)
            if m_nonang and not is_clinically_negated(clean, m_nonang.start(), m_nonang.end()):
                extracted["cp"] = BiomarkerExtraction(3, True, 0.95, m_nonang.group(0))
            elif m_atyp and not is_clinically_negated(clean, m_atyp.start(), m_atyp.end()):
                extracted["cp"] = BiomarkerExtraction(2, True, 0.95, m_atyp.group(0))
            elif m_typ and not is_clinically_negated(clean, m_typ.start(), m_typ.end()):
                extracted["cp"] = BiomarkerExtraction(1, True, 0.95, m_typ.group(0))
            elif m_cp_any and not is_clinically_negated(clean, m_cp_any.start(), m_cp_any.end()):
                extracted["cp"] = BiomarkerExtraction(1, True, 0.80, m_cp_any.group(0))
            else:
                extracted["cp"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["cp"], False, 0.0, "imputed_asymptomatic")
                missing_fields.append("cp")

        # ------------------------------------------------------------------ 4. trestbps (Resting Blood Pressure mmHg)
        m_bp_pair = re.search(r'\b(?:blood\s+pressure|resting\s+bp|b\.?p\.?)[\s:=]*([0-9]{2,3})\s*/\s*[0-9]{2,3}\b', clean, re.IGNORECASE)
        m_bp_mmhg = re.search(r'\b(?:blood\s+pressure|resting\s+bp|trestbps|b\.?p\.?)[\s:=]*([0-9]{2,3})\s*(?:mm\s*hg)?\b', clean, re.IGNORECASE)
        if m_bp_pair and 80 <= int(m_bp_pair.group(1)) <= 240:
            extracted["trestbps"] = BiomarkerExtraction(int(m_bp_pair.group(1)), True, 0.99, m_bp_pair.group(0))
        elif m_bp_mmhg and 80 <= int(m_bp_mmhg.group(1)) <= 240:
            extracted["trestbps"] = BiomarkerExtraction(int(m_bp_mmhg.group(1)), True, 0.95, m_bp_mmhg.group(0))
        else:
            extracted["trestbps"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["trestbps"], False, 0.0, "imputed_120")
            missing_fields.append("trestbps")

        # ------------------------------------------------------------------ 5. chol (Serum Total Cholesterol mg/dL)
        m_chol_tot = re.search(r'\b(?:total\s+cholesterol|serum\s+cholesterol|cholesterol[,\s]+total)[\s:=]+([0-9]{2,3})\b', clean, re.IGNORECASE)
        if m_chol_tot and 100 <= int(m_chol_tot.group(1)) <= 600:
            extracted["chol"] = BiomarkerExtraction(int(m_chol_tot.group(1)), True, 0.99, m_chol_tot.group(0))
        else:
            found_chol = False
            for m in re.finditer(r'\b(?:chol(?:esterol)?)[\s:=]+([0-9]{2,3})\b', clean, re.IGNORECASE):
                prefix = clean[max(0, m.start() - 15) : m.start()].lower()
                if "hdl" in prefix or "ldl" in prefix or "ratio" in prefix:
                    continue
                v = int(m.group(1))
                if 100 <= v <= 600:
                    extracted["chol"] = BiomarkerExtraction(v, True, 0.90, m.group(0))
                    found_chol = True
                    break
            if not found_chol:
                extracted["chol"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["chol"], False, 0.0, "imputed_195")
                missing_fields.append("chol")

        # ------------------------------------------------------------------ 6. fbs (Fasting Blood Sugar > 120 mg/dL: 1 / 0)
        m_fbs_num = re.search(r'\b(?:fasting\s+(?:blood\s+)?(?:sugar|glucose)|fbs|fbg)[\s:=]+([0-9]{2,3})\s*(?:mg\s*/\s*d[lL])?\b', clean, re.IGNORECASE)
        if m_fbs_num:
            val_num = float(m_fbs_num.group(1))
            f_val = 1 if val_num > 120 else 0
            extracted["fbs"] = BiomarkerExtraction(f_val, True, 0.98, m_fbs_num.group(0))
        else:
            m_dm = re.search(r'\b(diabetes(?:\s+mellitus)?|diabetic|t2dm|t1dm|iddm|niddm)\b', clean, re.IGNORECASE)
            if m_dm:
                if is_clinically_negated(clean, m_dm.start(), m_dm.end()):
                    extracted["fbs"] = BiomarkerExtraction(0, True, 0.95, clean[m_dm.start():m_dm.end()] + " (negated)", is_negated=True)
                else:
                    extracted["fbs"] = BiomarkerExtraction(1, True, 0.95, m_dm.group(0))
            else:
                extracted["fbs"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["fbs"], False, 0.0, "imputed_0")
                missing_fields.append("fbs")

        # ------------------------------------------------------------------ 7. restecg (Resting ECG 0, 1, 2)
        m_lvh = re.search(r'\b(left\s+ventricular\s+hypertrophy|lvh|voltage\s+criteria\s+for\s+lvh|estes(?:\'?s)?\s+criteria)\b', clean, re.IGNORECASE)
        m_stt = re.search(r'\b(st-t(?:\s+wave)?\s+abnormality|t-wave\s+inversion|t\s+wave\s+inversion|st\s+elevation|ischemic\s+st\s+changes|repolarization\s+abnormality)\b', clean, re.IGNORECASE)
        m_norm_ecg = re.search(r'\b(normal\s+sinus\s+rhythm|nsr|normal\s+ecg|normal\s+ekg|unremarkable\s+ecg|ecg\s+within\s+normal\s+limits|ecg\s+wnl)\b', clean, re.IGNORECASE)
        m_restecg_kv = re.search(r'\brestecg[\s:=]+([0-2])\b', clean, re.IGNORECASE)
        if m_restecg_kv:
            extracted["restecg"] = BiomarkerExtraction(int(m_restecg_kv.group(1)), True, 0.99, m_restecg_kv.group(0))
        elif m_lvh and not is_clinically_negated(clean, m_lvh.start(), m_lvh.end()):
            extracted["restecg"] = BiomarkerExtraction(2, True, 0.98, m_lvh.group(0))
        elif m_stt and not is_clinically_negated(clean, m_stt.start(), m_stt.end()):
            extracted["restecg"] = BiomarkerExtraction(1, True, 0.98, m_stt.group(0))
        elif m_norm_ecg:
            extracted["restecg"] = BiomarkerExtraction(0, True, 0.98, m_norm_ecg.group(0))
        elif (m_lvh and is_clinically_negated(clean, m_lvh.start(), m_lvh.end())) or (m_stt and is_clinically_negated(clean, m_stt.start(), m_stt.end())):
            extracted["restecg"] = BiomarkerExtraction(0, True, 0.95, "negated_ecg_abnormality", is_negated=True)
        else:
            extracted["restecg"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["restecg"], False, 0.0, "imputed_0")
            missing_fields.append("restecg")

        # ------------------------------------------------------------------ 8. thalach (Max Heart Rate Achieved)
        m_peak = re.search(r'\b(?:max(?:imum)?|peak)(?:\s+exercise)?\s+(?:heart\s+rate|hr|pulse|thalach)(?:[^\d\n\.;]{0,40}?)[\s:=]+([0-9]{2,3})\b', clean, re.IGNORECASE)
        if m_peak and 60 <= int(m_peak.group(1)) <= 230:
            extracted["thalach"] = BiomarkerExtraction(int(m_peak.group(1)), True, 0.99, m_peak.group(0))
        else:
            m_gen_hr = re.search(r'\b(?:heart\s+rate|pulse|hr|bpm)[\s:=]+([0-9]{2,3})\b', clean, re.IGNORECASE)
            if m_gen_hr and "resting" not in clean[max(0, m_gen_hr.start() - 15) : m_gen_hr.start()].lower() and 60 <= int(m_gen_hr.group(1)) <= 230:
                extracted["thalach"] = BiomarkerExtraction(int(m_gen_hr.group(1)), True, 0.80, m_gen_hr.group(0))
            else:
                extracted["thalach"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["thalach"], False, 0.0, "imputed_150")
                missing_fields.append("thalach")

        # ------------------------------------------------------------------ 9. exang (Exercise Angina 1 / 0)
        m_exang_kv = re.search(r'\b(?:exercise[- ]induced\s+angina|exang|stress\s+angina)[\s:=]+(yes|true|1|positive|no|false|0|negative|denied)\b', clean, re.IGNORECASE)
        if m_exang_kv:
            ex_val = 1 if re.match(r'^(?:yes|true|1|positive)$', m_exang_kv.group(1), re.IGNORECASE) else 0
            extracted["exang"] = BiomarkerExtraction(ex_val, True, 0.99, m_exang_kv.group(0))
        else:
            m_ex_term = re.search(r'\b(exercise[- ]induced\s+angina|stress[- ]induced\s+angina|exertional\s+angina|angina\s+on\s+exertion|chest\s+tightness\s+(?:during|with|on)\s+exercise)\b', clean, re.IGNORECASE)
            if m_ex_term:
                if is_clinically_negated(clean, m_ex_term.start(), m_ex_term.end()):
                    extracted["exang"] = BiomarkerExtraction(0, True, 0.95, clean[m_ex_term.start():m_ex_term.end()] + " (negated)", is_negated=True)
                else:
                    extracted["exang"] = BiomarkerExtraction(1, True, 0.95, m_ex_term.group(0))
            else:
                m_broad_ang = re.search(r'\b(angina|ischemic\s+chest\s+pain|chest\s+tightness)\b', clean, re.IGNORECASE)
                if m_broad_ang:
                    if is_clinically_negated(clean, m_broad_ang.start(), m_broad_ang.end()):
                        extracted["exang"] = BiomarkerExtraction(0, True, 0.90, clean[m_broad_ang.start():m_broad_ang.end()] + " (negated)", is_negated=True)
                    elif re.search(r'\b(exercise|treadmill|stress|bruce|exertion)\b', clean, re.IGNORECASE):
                        extracted["exang"] = BiomarkerExtraction(1, True, 0.85, m_broad_ang.group(0))
                    else:
                        extracted["exang"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["exang"], False, 0.0, "imputed_0")
                        missing_fields.append("exang")
                else:
                    extracted["exang"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["exang"], False, 0.0, "imputed_0")
                    missing_fields.append("exang")

        # ------------------------------------------------------------------ 10. oldpeak (ST Depression mm)
        m_st_dep = re.search(r'\b(st\s+(?:segment\s+)?depression|oldpeak)\b', clean, re.IGNORECASE)
        if m_st_dep and is_clinically_negated(clean, m_st_dep.start(), m_st_dep.end()):
            extracted["oldpeak"] = BiomarkerExtraction(0.0, True, 0.95, clean[m_st_dep.start():m_st_dep.end()] + " (negated)", is_negated=True)
        else:
            m_old_num = re.search(r'\b(?:st\s+(?:segment\s+)?depression|oldpeak)[\s:=]+([+-]?[0-9]+(?:\.[0-9]+)?)\s*(?:mm)?\b', clean, re.IGNORECASE)
            if m_old_num:
                v = min(6.0, abs(float(m_old_num.group(1))))
                extracted["oldpeak"] = BiomarkerExtraction(v, True, 0.98, m_old_num.group(0))
            else:
                extracted["oldpeak"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["oldpeak"], False, 0.0, "imputed_0.0")
                missing_fields.append("oldpeak")

        # ------------------------------------------------------------------ 11. slope (ST Slope 1: Up, 2: Flat, 3: Down)
        m_slope_kv = re.search(r'\b(?:st\s+)?slope[\s:=]+([1-3]|upsloping|flat|horizontal|downsloping)\b', clean, re.IGNORECASE)
        if m_slope_kv:
            s_str = m_slope_kv.group(1).lower()
            s_val = 3 if s_str in ["3", "downsloping"] else (2 if s_str in ["2", "flat", "horizontal"] else 1)
            extracted["slope"] = BiomarkerExtraction(s_val, True, 0.99, m_slope_kv.group(0))
        else:
            m_down = re.search(r'\b(?:downsloping|down-sloping|descending)\b', clean, re.IGNORECASE)
            m_flat = re.search(r'\b(?:flat|horizontal)\s+(?:st|st-segment|st\s+depression|st\s+slope)\b', clean, re.IGNORECASE)
            m_up = re.search(r'\b(?:upsloping|up-sloping|physiologic\s+st\s+slope)\b', clean, re.IGNORECASE)
            if m_down and not is_clinically_negated(clean, m_down.start(), m_down.end()):
                extracted["slope"] = BiomarkerExtraction(3, True, 0.95, m_down.group(0))
            elif m_flat and not is_clinically_negated(clean, m_flat.start(), m_flat.end()):
                extracted["slope"] = BiomarkerExtraction(2, True, 0.95, m_flat.group(0))
            elif m_up:
                extracted["slope"] = BiomarkerExtraction(1, True, 0.95, m_up.group(0))
            else:
                extracted["slope"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["slope"], False, 0.0, "imputed_1")
                missing_fields.append("slope")

        # ------------------------------------------------------------------ 12. ca (Fluoroscopy Vessels 0-3)
        m_clear_vessels = re.search(r'\b(?:normal\s+coronary\s+arteries|no\s+(?:significant\s+)?(?:coronary\s+)?(?:stenosis|disease|cad|vessel\s+disease)|0\s+(?:major\s+)?vessels?|clean\s+coronaries)\b', clean, re.IGNORECASE)
        if m_clear_vessels:
            extracted["ca"] = BiomarkerExtraction(0, True, 0.98, m_clear_vessels.group(0))
        elif re.search(r'\b(?:triple[- ]vessel\s+(?:disease|cad)|3[- ]vessel\s+(?:disease|cad))\b', clean, re.IGNORECASE):
            extracted["ca"] = BiomarkerExtraction(3, True, 0.98, "triple_vessel_cad")
        elif re.search(r'\b(?:double[- ]vessel\s+(?:disease|cad)|two[- ]vessel\s+(?:disease|cad)|2[- ]vessel\s+(?:disease|cad))\b', clean, re.IGNORECASE):
            extracted["ca"] = BiomarkerExtraction(2, True, 0.98, "two_vessel_cad")
        elif re.search(r'\b(?:single[- ]vessel\s+(?:disease|cad)|one[- ]vessel\s+(?:disease|cad)|1[- ]vessel\s+(?:disease|cad))\b', clean, re.IGNORECASE):
            extracted["ca"] = BiomarkerExtraction(1, True, 0.98, "single_vessel_cad")
        else:
            m_ca_kv = re.search(r'\b(?:ca|fluoroscopy|calcified\s+vessels|major\s+vessels)[\s:=]+([0-3])\b', clean, re.IGNORECASE)
            m_ca_cnt = re.search(r'\b([0-3])[\s-]*(?:major\s+)?vessels?\s+(?:calcified|occluded|stenosed|diseased)\b', clean, re.IGNORECASE)
            if m_ca_kv:
                extracted["ca"] = BiomarkerExtraction(int(m_ca_kv.group(1)), True, 0.98, m_ca_kv.group(0))
            elif m_ca_cnt:
                extracted["ca"] = BiomarkerExtraction(int(m_ca_cnt.group(1)), True, 0.95, m_ca_cnt.group(0))
            else:
                extracted["ca"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["ca"], False, 0.0, "imputed_0")
                missing_fields.append("ca")

        # ------------------------------------------------------------------ 13. thal (Scintigraphy Defect 3, 6, 7)
        m_thal_kv = re.search(r'\b(?:thal|thalassemia|myocardial\s+scintigraphy)[\s:=]+([367]|normal|fixed|reversible)\b', clean, re.IGNORECASE)
        if m_thal_kv:
            t_str = m_thal_kv.group(1).lower()
            t_val = 7 if t_str in ["7", "reversible"] else (6 if t_str in ["6", "fixed"] else 3)
            extracted["thal"] = BiomarkerExtraction(t_val, True, 0.99, m_thal_kv.group(0))
        else:
            m_rev_perf = re.search(r'\b(?:reversible\s+(?:perfusion\s+)?defect|reversible\s+ischemia)\b', clean, re.IGNORECASE)
            m_fix_perf = re.search(r'\b(?:fixed\s+(?:perfusion\s+)?defect|fixed\s+(?:myocardial\s+)?scar|prior\s+(?:infarct|infarction)\s+scar)\b', clean, re.IGNORECASE)
            m_norm_perf = re.search(r'\b(?:normal\s+(?:myocardial\s+)?perfusion|no\s+(?:perfusion\s+)?defects?|unremarkable\s+spect)\b', clean, re.IGNORECASE)
            if m_rev_perf:
                if is_clinically_negated(clean, m_rev_perf.start(), m_rev_perf.end()):
                    extracted["thal"] = BiomarkerExtraction(3, True, 0.90, clean[m_rev_perf.start():m_rev_perf.end()] + " (negated)", is_negated=True)
                else:
                    extracted["thal"] = BiomarkerExtraction(7, True, 0.98, m_rev_perf.group(0))
            elif m_fix_perf:
                if is_clinically_negated(clean, m_fix_perf.start(), m_fix_perf.end()):
                    extracted["thal"] = BiomarkerExtraction(3, True, 0.90, clean[m_fix_perf.start():m_fix_perf.end()] + " (negated)", is_negated=True)
                else:
                    extracted["thal"] = BiomarkerExtraction(6, True, 0.98, m_fix_perf.group(0))
            elif m_norm_perf:
                extracted["thal"] = BiomarkerExtraction(3, True, 0.98, m_norm_perf.group(0))
            else:
                extracted["thal"] = BiomarkerExtraction(SAFE_SCREENING_DEFAULTS["thal"], False, 0.0, "imputed_3")
                missing_fields.append("thal")

        # ------------------------------------------------------------------ Summary & Quality Scoring
        extracted_count = sum(1 for v in extracted.values() if v.extracted)
        confidence_score = round(extracted_count / 13.0, 3)

        if missing_fields:
            warnings.append(
                f"{len(missing_fields)} of 13 biomarkers were absent ({', '.join(missing_fields)}) and assigned non-pathological screening defaults."
            )

        safe_to_predict = extracted_count >= self.min_extracted
        if not safe_to_predict:
            warnings.append(
                f"Insufficient clinical biomarkers ({extracted_count}/13 found). Automated risk prediction suspended to prevent diagnostic error."
            )

        return ClinicalParseResult(
            biomarkers={k: v.value for k, v in extracted.items()},
            metadata=extracted,
            extracted_count=extracted_count,
            total_count=13,
            confidence_score=confidence_score,
            missing_fields=missing_fields,
            warnings=warnings,
            safe_to_predict=safe_to_predict,
        )

    def extract_text_from_pdf_stream(self, data: bytes) -> str:
        """Extracts text from PDF bytes without requiring third-party libraries."""
        # Tier 1: pypdf if available
        if pypdf is not None:
            try:
                reader = pypdf.PdfReader(io.BytesIO(data))
                text_pages = [p.extract_text() or "" for p in reader.pages]
                full_text = " ".join(text_pages).strip()
                if full_text:
                    return full_text
            except Exception:
                pass

        # Tier 2: Built-in pure-Python FlateDecode stream decompressor
        text_parts: list[str] = []
        for m in re.finditer(rb'<<[^>]*?/Filter\s*/FlateDecode[^>]*?>>\s*stream\r?\n(.*?)\r?\nendstream', data, re.DOTALL):
            raw_stream = m.group(1)
            decomp = None
            for wbits in (zlib.MAX_WBITS, -15):
                try:
                    decomp = zlib.decompress(raw_stream, wbits)
                    break
                except Exception:
                    continue
            if decomp:
                for block in re.findall(rb'BT(.*?)ET', decomp, re.DOTALL):
                    for tj in re.findall(rb'\((.*?)\)\s*Tj', block):
                        text_parts.append(tj.decode("latin1", errors="ignore"))
                    for tj_arr in re.findall(rb'\[(.*?)\]\s*TJ', block):
                        for part in re.findall(rb'\((.*?)\)', tj_arr):
                            text_parts.append(part.decode("latin1", errors="ignore"))

        # Also search raw uncompressed text streams
        for block in re.findall(rb'BT(.*?)ET', data, re.DOTALL):
            for tj in re.findall(rb'\((.*?)\)\s*Tj', block):
                text_parts.append(tj.decode("latin1", errors="ignore"))
            for tj_arr in re.findall(rb'\[(.*?)\]\s*TJ', block):
                for part in re.findall(rb'\((.*?)\)', tj_arr):
                    text_parts.append(part.decode("latin1", errors="ignore"))

        extracted_text = " ".join(text_parts).strip()
        if not extracted_text:
            # Check if scanned document (has images)
            if re.search(rb'/Subtype\s*/Image', data) or re.search(rb'/Type\s*/XObject', data):
                raise ValueError("Uploaded PDF appears to be a scanned image document without digital text. OCR required.")
        return extracted_text

    def parse_file(self, file_source: Union[str, Path, bytes, BinaryIO], filename: str = "") -> ClinicalParseResult:
        if isinstance(file_source, (str, Path)):
            p = Path(file_source)
            filename = filename or p.name
            raw_bytes = p.read_bytes()
        elif isinstance(file_source, bytes):
            raw_bytes = file_source
        elif hasattr(file_source, "read"):
            raw_bytes = file_source.read()
        else:
            raise TypeError(f"Unsupported file source: {type(file_source)}")

        lower_name = filename.lower()
        if lower_name.endswith(".pdf") or raw_bytes.startswith(b"%PDF"):
            try:
                text = self.extract_text_from_pdf_stream(raw_bytes)
            except ValueError as ve:
                res = self.parse_text("")
                res.warnings.append(str(ve))
                res.safe_to_predict = False
                return res
            return self.parse_text(text)

        if lower_name.endswith(".json"):
            try:
                data = json.loads(raw_bytes.decode("utf-8", errors="ignore"))
                # If structured biomarker object:
                if isinstance(data, dict):
                    # Check if keys match biomarkers
                    vitals = {}
                    for k in SAFE_SCREENING_DEFAULTS:
                        if k in data:
                            vitals[k] = float(data[k])
                    if len(vitals) >= self.min_extracted:
                        text_repr = "\n".join(f"{k}: {v}" for k, v in vitals.items())
                        return self.parse_text(text_repr)
            except Exception:
                pass

        # Default text decode
        text = raw_bytes.decode("utf-8", errors="ignore")
        return self.parse_text(text)
