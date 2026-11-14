"""Comprehensive validation suite for heart-disease-predictor/personas/personas_100.json.

Verifies schema compliance, demographic distributions, biomarker integrity, and ML inference.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

import jsonschema

# Locate repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import core
import joblib


SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ClinicalPersonaDataset",
    "type": "array",
    "minItems": 100,
    "maxItems": 100,
    "items": {
        "type": "object",
        "required": [
            "persona_id",
            "name",
            "archetype",
            "demographics",
            "clinical_profile",
            "user_journey",
            "observed_pain_points",
            "feedback_evaluation",
        ],
        "properties": {
            "persona_id": {
                "type": "string",
                "pattern": "^PERS-(0[0-9]{2}|100)$",
            },
            "name": {
                "type": "string",
                "minLength": 3,
            },
            "archetype": {
                "type": "string",
                "enum": [
                    "Patient: Acute Chest Pain (High Risk)",
                    "Patient: Diabetic Silent Ischemia",
                    "Patient: Routine Executive Screen (Low Risk)",
                    "Patient: Female Atypical Microvascular Angina",
                    "Patient: Geriatric Multi-Morbidity",
                    "Clinician: Interventional Cardiologist",
                    "Clinician: Emergency Department Attending",
                    "Clinician: Primary Care Physician (PCP)",
                    "Clinician: Cardiac Care Nurse Practitioner",
                    "Administrator: Chief Medical Officer (CMO)",
                    "Administrator: Hospital IT Security & HIPAA Officer",
                ],
            },
            "demographics": {
                "type": "object",
                "required": [
                    "age",
                    "sex",
                    "ethnicity",
                    "socioeconomic_tier",
                    "clinical_setting",
                    "digital_health_literacy",
                ],
                "properties": {
                    "age": {"type": "integer", "minimum": 18, "maximum": 95},
                    "sex": {"type": "integer", "enum": [0, 1]},
                    "ethnicity": {
                        "type": "string",
                        "enum": [
                            "Caucasian",
                            "African American",
                            "Hispanic/Latino",
                            "Asian/Pacific Islander",
                            "Native American/Multiracial",
                        ],
                    },
                    "socioeconomic_tier": {
                        "type": "string",
                        "enum": ["Low", "Middle", "High", "Uninsured/Safety-Net"],
                    },
                    "clinical_setting": {
                        "type": "string",
                        "enum": [
                            "Academic Medical Center",
                            "Community Hospital",
                            "Rural Critical Access Clinic",
                            "Outpatient Cardiology Practice",
                            "Home/Remote Telehealth",
                        ],
                    },
                    "digital_health_literacy": {
                        "type": "string",
                        "enum": [
                            "Basic/Screen-Reader",
                            "Intermediate",
                            "Advanced Power User",
                        ],
                    },
                },
            },
            "clinical_profile": {
                "type": "object",
                "description": "Complete 13-feature clinical vector compatible with core.py:FEATURES plus ground truth CAD label",
                "required": [
                    "age",
                    "sex",
                    "cp",
                    "trestbps",
                    "chol",
                    "fbs",
                    "restecg",
                    "thalach",
                    "exang",
                    "oldpeak",
                    "slope",
                    "ca",
                    "thal",
                    "ground_truth_cad",
                ],
                "properties": {
                    "age": {"type": "integer", "minimum": 18, "maximum": 95},
                    "sex": {"type": "integer", "enum": [0, 1]},
                    "cp": {"type": "integer", "enum": [1, 2, 3, 4]},
                    "trestbps": {"type": "number", "minimum": 80.0, "maximum": 220.0},
                    "chol": {"type": "number", "minimum": 100.0, "maximum": 580.0},
                    "fbs": {"type": "integer", "enum": [0, 1]},
                    "restecg": {"type": "integer", "enum": [0, 1, 2]},
                    "thalach": {"type": "number", "minimum": 60.0, "maximum": 215.0},
                    "exang": {"type": "integer", "enum": [0, 1]},
                    "oldpeak": {"type": "number", "minimum": 0.0, "maximum": 6.5},
                    "slope": {"type": "integer", "enum": [1, 2, 3]},
                    "ca": {"type": "integer", "enum": [0, 1, 2, 3]},
                    "thal": {"type": "integer", "enum": [3, 6, 7]},
                    "ground_truth_cad": {"type": "integer", "enum": [0, 1]},
                },
            },
            "user_journey": {
                "type": "object",
                "required": [
                    "entry_point",
                    "primary_task",
                    "secondary_action",
                    "completion_status",
                    "time_on_task_sec",
                ],
                "properties": {
                    "entry_point": {"type": "string"},
                    "primary_task": {"type": "string"},
                    "secondary_action": {"type": "string"},
                    "completion_status": {
                        "type": "string",
                        "enum": [
                            "Success",
                            "Blocked by Bug",
                            "Abandoned Due to UX Confusion",
                        ],
                    },
                    "time_on_task_sec": {"type": "number", "minimum": 10.0},
                },
            },
            "observed_pain_points": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
            },
            "feedback_evaluation": {
                "type": "object",
                "required": [
                    "usability_score",
                    "clinical_trust_score",
                    "visual_clarity_score",
                    "verbatim_quote",
                    "dissected_category",
                ],
                "properties": {
                    "usability_score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "clinical_trust_score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "visual_clarity_score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "verbatim_quote": {"type": "string", "minLength": 15},
                    "dissected_category": {
                        "type": "string",
                        "enum": [
                            "Software Bug",
                            "UI/UX Friction",
                            "Biomarker Data Gap",
                            "Model Generalization Concern",
                        ],
                    },
                },
            },
        },
    },
}


def validate_personas() -> None:
    json_path = REPO_ROOT / "personas" / "personas_100.json"
    assert json_path.exists(), f"Missing dataset file: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    print(f"Loaded {len(personas)} personas from {json_path}")
    assert len(personas) == 100, f"Expected exactly 100 personas, found {len(personas)}"

    # 0. Strict JSON Schema Validation
    print("Validating dataset against JSON Schema draft-07...")
    jsonschema.validate(instance=personas, schema=SCHEMA)
    print("✓ JSON Schema validation passed.")

    # Load ML pipeline to verify inference compatibility
    model_bundle = joblib.load(REPO_ROOT / "artifacts" / "heart_model.joblib")
    best_pipe = model_bundle["models"][model_bundle["best"]]

    # Counters for demographic auditing
    sex_counts = {0: 0, 1: 0}
    age_tiers = {"18-39": 0, "40-59": 0, "60-79": 0, "80+": 0}
    ethnicities: dict[str, int] = {}
    socioeconomic: dict[str, int] = {}
    clinical_settings: dict[str, int] = {}
    literacy_levels: dict[str, int] = {}
    archetype_counts: dict[str, int] = {}
    dissected_categories: dict[str, int] = {}
    completion_statuses: dict[str, int] = {}

    for i, p in enumerate(personas):
        pid = p["persona_id"]
        expected_pid = f"PERS-{i+1:03d}"
        assert pid == expected_pid, f"Persona index {i} has id {pid}, expected {expected_pid}"

        # 1. Demographics Verification
        demo = p["demographics"]
        age = demo["age"]
        sex = demo["sex"]
        assert sex in (0, 1), f"{pid}: Invalid sex {sex}"
        assert 18 <= age <= 95, f"{pid}: Age {age} out of range [18, 95]"

        sex_counts[sex] += 1
        if 18 <= age <= 39:
            age_tiers["18-39"] += 1
        elif 40 <= age <= 59:
            age_tiers["40-59"] += 1
        elif 60 <= age <= 79:
            age_tiers["60-79"] += 1
        else:
            age_tiers["80+"] += 1

        ethnicities[demo["ethnicity"]] = ethnicities.get(demo["ethnicity"], 0) + 1
        socioeconomic[demo["socioeconomic_tier"]] = socioeconomic.get(demo["socioeconomic_tier"], 0) + 1
        clinical_settings[demo["clinical_setting"]] = clinical_settings.get(demo["clinical_setting"], 0) + 1
        literacy_levels[demo["digital_health_literacy"]] = literacy_levels.get(demo["digital_health_literacy"], 0) + 1
        archetype_counts[p["archetype"]] = archetype_counts.get(p["archetype"], 0) + 1

        # 2. Clinical Profile & core.py:FEATURES Verification
        cp = p["clinical_profile"]
        assert cp["age"] == age, f"{pid}: Age mismatch between demographics ({age}) and clinical_profile ({cp['age']})"
        assert cp["sex"] == sex, f"{pid}: Sex mismatch between demographics ({sex}) and clinical_profile ({cp['sex']})"

        for feat in core.FEATURES:
            assert feat in cp, f"{pid}: Missing core.py feature '{feat}' in clinical_profile"

        assert cp["cp"] in (1, 2, 3, 4), f"{pid}: Invalid cp {cp['cp']}"
        assert 80.0 <= cp["trestbps"] <= 220.0, f"{pid}: Out of range trestbps {cp['trestbps']}"
        assert 100.0 <= cp["chol"] <= 580.0, f"{pid}: Out of range chol {cp['chol']}"
        assert cp["fbs"] in (0, 1), f"{pid}: Invalid fbs {cp['fbs']}"
        assert cp["restecg"] in (0, 1, 2), f"{pid}: Invalid restecg {cp['restecg']}"
        assert 60.0 <= cp["thalach"] <= 215.0, f"{pid}: Out of range thalach {cp['thalach']}"
        assert cp["exang"] in (0, 1), f"{pid}: Invalid exang {cp['exang']}"
        assert 0.0 <= cp["oldpeak"] <= 6.5, f"{pid}: Out of range oldpeak {cp['oldpeak']}"
        assert cp["slope"] in (1, 2, 3), f"{pid}: Invalid slope {cp['slope']}"
        assert cp["ca"] in (0, 1, 2, 3), f"{pid}: Invalid ca {cp['ca']}"
        assert cp["thal"] in (3, 6, 7), f"{pid}: Invalid thal {cp['thal']}"
        assert cp["ground_truth_cad"] in (0, 1), f"{pid}: Invalid ground_truth_cad {cp['ground_truth_cad']}"

        # Physiological sanity: heart rate ceiling
        max_possible_hr = 220 - age + 20
        assert cp["thalach"] <= max_possible_hr, f"{pid}: Unrealistic thalach {cp['thalach']} for age {age}"

        # 3. Model Inference Test
        prob = core.predict_proba(best_pipe, cp)
        assert 0.0 <= prob <= 1.0, f"{pid}: Probability out of range: {prob}"
        band, _ = core.risk_band(prob)
        assert band in ("Low risk", "Moderate risk", "High risk"), f"{pid}: Invalid risk band {band}"

        # 4. Feedback & User Journey Verification
        uj = p["user_journey"]
        assert uj["completion_status"] in ("Success", "Blocked by Bug", "Abandoned Due to UX Confusion")
        assert uj["time_on_task_sec"] >= 10.0
        completion_statuses[uj["completion_status"]] = completion_statuses.get(uj["completion_status"], 0) + 1

        fb = p["feedback_evaluation"]
        assert 1 <= fb["usability_score"] <= 5
        assert 1 <= fb["clinical_trust_score"] <= 5
        assert 1 <= fb["visual_clarity_score"] <= 5
        assert len(fb["verbatim_quote"]) >= 15
        cat = fb["dissected_category"]
        assert cat in ("Software Bug", "UI/UX Friction", "Biomarker Data Gap", "Model Generalization Concern")
        dissected_categories[cat] = dissected_categories.get(cat, 0) + 1

    # Assert Exact Demographic Balances
    print("\n--- Demographic Stratification Audit ---")
    print(f"Sex counts: {sex_counts}")
    assert sex_counts[0] == 50 and sex_counts[1] == 50, f"Sex imbalance: {sex_counts}"

    print(f"Age tiers: {age_tiers}")
    assert age_tiers["18-39"] == 15, f"Age tier 18-39 mismatch: {age_tiers['18-39']}"
    assert age_tiers["40-59"] == 45, f"Age tier 40-59 mismatch: {age_tiers['40-59']}"
    assert age_tiers["60-79"] == 32, f"Age tier 60-79 mismatch: {age_tiers['60-79']}"
    assert age_tiers["80+"] == 8, f"Age tier 80+ mismatch: {age_tiers['80+']}"

    print(f"Ethnicities: {ethnicities}")
    assert ethnicities.get("Caucasian") == 42, f"Caucasian mismatch: {ethnicities.get('Caucasian')}"
    assert ethnicities.get("African American") == 22, f"African American mismatch: {ethnicities.get('African American')}"
    assert ethnicities.get("Hispanic/Latino") == 18, f"Hispanic/Latino mismatch: {ethnicities.get('Hispanic/Latino')}"
    assert ethnicities.get("Asian/Pacific Islander") == 14, f"Asian/Pacific Islander mismatch: {ethnicities.get('Asian/Pacific Islander')}"
    assert ethnicities.get("Native American/Multiracial") == 4, f"Native American mismatch: {ethnicities.get('Native American/Multiracial')}"

    print(f"Socioeconomic tiers: {socioeconomic}")
    assert socioeconomic.get("Low") == 25, f"Low mismatch: {socioeconomic.get('Low')}"
    assert socioeconomic.get("Middle") == 35, f"Middle mismatch: {socioeconomic.get('Middle')}"
    assert socioeconomic.get("High") == 25, f"High mismatch: {socioeconomic.get('High')}"
    assert socioeconomic.get("Uninsured/Safety-Net") == 15, f"Uninsured mismatch: {socioeconomic.get('Uninsured/Safety-Net')}"

    print(f"Clinical settings: {clinical_settings}")
    assert clinical_settings.get("Academic Medical Center") == 25
    assert clinical_settings.get("Community Hospital") == 25
    assert clinical_settings.get("Rural Critical Access Clinic") == 15
    assert clinical_settings.get("Outpatient Cardiology Practice") == 20
    assert clinical_settings.get("Home/Remote Telehealth") == 15

    print(f"Literacy levels: {literacy_levels}")
    assert literacy_levels.get("Basic/Screen-Reader") == 20
    assert literacy_levels.get("Intermediate") == 50
    assert literacy_levels.get("Advanced Power User") == 30

    print(f"Archetype breakdown (11 archetypes): {len(archetype_counts)} archetypes found")
    assert len(archetype_counts) == 11

    print(f"Feedback categories (4 quadrants): {dissected_categories}")
    assert len(dissected_categories) == 4
    assert dissected_categories.get("Software Bug") == 29
    assert dissected_categories.get("UI/UX Friction") == 31
    assert dissected_categories.get("Biomarker Data Gap") == 20
    assert dissected_categories.get("Model Generalization Concern") == 20

    print(f"Completion statuses: {completion_statuses}")
    assert completion_statuses.get("Success") == 66
    assert completion_statuses.get("Blocked by Bug") == 23
    assert completion_statuses.get("Abandoned Due to UX Confusion") == 11

    # Step 5: Cross-Consistency Audit between personas_100.json and planning_committee_report.md
    validate_report_cross_consistency(personas, REPO_ROOT / "personas" / "planning_committee_report.md")

    print("\n[SUCCESS] All 100 personas strictly adhere to schema, demographic, clinical, inference, and report cross-consistency requirements!")


ARCHETYPE_MAP = {
    "1. Acute Chest Pain (High Risk)": "Patient: Acute Chest Pain (High Risk)",
    "2. Diabetic Silent Ischemia": "Patient: Diabetic Silent Ischemia",
    "3. Routine Executive Screen": "Patient: Routine Executive Screen (Low Risk)",
    "4. Female Atypical Microvasc.": "Patient: Female Atypical Microvascular Angina",
    "5. Geriatric Multi-Morbidity": "Patient: Geriatric Multi-Morbidity",
    "6. Interventional Cardiologist": "Clinician: Interventional Cardiologist",
    "7. Emergency Dept. Attending": "Clinician: Emergency Department Attending",
    "8. Primary Care Physician": "Clinician: Primary Care Physician (PCP)",
    "9. Cardiac Nurse Practitioner": "Clinician: Cardiac Care Nurse Practitioner",
    "10. Chief Medical Officer": "Administrator: Chief Medical Officer (CMO)",
    "11. Hospital IT Security/CISO": "Administrator: Hospital IT Security & HIPAA Officer",
}


def validate_report_cross_consistency(personas: list[dict], report_path: Path) -> None:
    """Step 5: Enforces 100% single-digit statistical parity between personas_100.json and planning_committee_report.md."""
    assert report_path.exists(), f"Missing planning committee report: {report_path}"
    report_text = report_path.read_text(encoding="utf-8")

    print("\n--- Step 5: Cross-Consistency Audit between personas_100.json and planning_committee_report.md ---")

    # 5.1 Table 3.1 Demographic Stratification Parity
    assert "| **Sex** | Female (`0`) | 50 | 50 |" in report_text, "Report Table 3.1 sex female mismatch"
    assert "| | Male (`1`) | 50 | 50 |" in report_text, "Report Table 3.1 sex male mismatch"
    assert "| Young (18–39) | 15 | 15 |" in report_text, "Report Table 3.1 age 18-39 mismatch"
    assert "| Middle (40–59) | 45 | 45 |" in report_text, "Report Table 3.1 age 40-59 mismatch"
    assert "| Older (60–79) | 32 | 32 |" in report_text, "Report Table 3.1 age 60-79 mismatch"
    assert "| Geriatric (80+) | 8 | 8 |" in report_text, "Report Table 3.1 age 80+ mismatch"
    print("✓ Section 3.1 Demographic Stratification Table parity confirmed.")

    # 5.2 Extract and Parse Table 3.2 Dynamically
    table_lines = []
    in_table = False
    for line in report_text.splitlines():
        if "PERSONA COHORT QUANTITATIVE PERFORMANCE SUMMARY" in line:
            in_table = True
            continue
        if in_table:
            table_lines.append(line)
            if line.startswith("└") or line.startswith("```"):
                if line.startswith("└"):
                    break
    assert table_lines, "Could not locate Table 3.2 in planning_committee_report.md"

    by_arch = defaultdict(list)
    for p in personas:
        by_arch[p["archetype"]].append(p)

    cohort_rows_checked = 0
    composite_checked = False

    for line in table_lines:
        if ("│" not in line and "|" not in line) or line.startswith("├") or line.startswith("┌") or line.startswith("└"):
            continue
        delimiter = "│" if "│" in line else "|"
        parts = [p.strip() for p in line.split(delimiter)[1:-1]]
        if not parts or "ARCHETYPE COHORT" in parts[0] or "PERSONA COHORT" in parts[0]:
            continue

        cohort_name = parts[0]
        if cohort_name == "TOTALS / COMPOSITE AVERAGE":
            # Composite row validation
            exp_n = int(parts[1])
            exp_u = float(parts[2].split("/")[0])
            exp_t = float(parts[3].split("/")[0])
            exp_c = float(parts[4].split("/")[0])
            exp_time = float(parts[5].rstrip("s"))

            act_n = len(personas)
            act_u = round(sum(p["feedback_evaluation"]["usability_score"] for p in personas) / act_n, 2)
            act_t = round(sum(p["feedback_evaluation"]["clinical_trust_score"] for p in personas) / act_n, 2)
            act_c = round(sum(p["feedback_evaluation"]["visual_clarity_score"] for p in personas) / act_n, 2)
            act_time = round(sum(p["user_journey"]["time_on_task_sec"] for p in personas) / act_n, 1)

            assert act_n == exp_n, f"Composite count: actual {act_n} != report {exp_n}"
            assert act_u == exp_u, f"Composite usability: actual {act_u} != report {exp_u}"
            assert act_t == exp_t, f"Composite trust: actual {act_t} != report {exp_t}"
            assert act_c == exp_c, f"Composite clarity: actual {act_c} != report {exp_c}"
            assert act_time == exp_time, f"Composite time: actual {act_time} != report {exp_time}"
            composite_checked = True
            print("✓ Table 3.2 Composite summary row parity confirmed.")
            continue

        assert cohort_name in ARCHETYPE_MAP, f"Unknown cohort name in Table 3.2: {cohort_name}"
        full_arch = ARCHETYPE_MAP[cohort_name]
        plist = by_arch[full_arch]
        n = len(plist)

        exp_n = int(parts[1])
        exp_u = float(parts[2].split("/")[0])
        exp_t = float(parts[3].split("/")[0])
        exp_c = float(parts[4].split("/")[0])
        exp_time = float(parts[5].rstrip("s"))
        succ_match = re.search(r"\((\d+)/(\d+)\)", parts[6])
        exp_succ_cnt = int(succ_match.group(1)) if succ_match else None
        exp_issue = parts[7]

        act_u = round(sum(p["feedback_evaluation"]["usability_score"] for p in plist) / n, 2)
        act_t = round(sum(p["feedback_evaluation"]["clinical_trust_score"] for p in plist) / n, 2)
        act_c = round(sum(p["feedback_evaluation"]["visual_clarity_score"] for p in plist) / n, 2)
        act_time = round(sum(p["user_journey"]["time_on_task_sec"] for p in plist) / n, 1)
        act_succ_cnt = sum(1 for p in plist if p["user_journey"]["completion_status"] == "Success")
        act_issue = Counter(p["feedback_evaluation"]["dissected_category"] for p in plist).most_common(1)[0][0]

        assert n == exp_n, f"{cohort_name}: count actual {n} != report {exp_n}"
        assert act_u == exp_u, f"{cohort_name}: usability actual {act_u} != report {exp_u}"
        assert act_t == exp_t, f"{cohort_name}: trust actual {act_t} != report {exp_t}"
        assert act_c == exp_c, f"{cohort_name}: clarity actual {act_c} != report {exp_c}"
        assert act_time == exp_time, f"{cohort_name}: task time actual {act_time} != report {exp_time}"
        if exp_succ_cnt is not None:
            assert act_succ_cnt == exp_succ_cnt, f"{cohort_name}: success count actual {act_succ_cnt} != report {exp_succ_cnt}"
        assert exp_issue == act_issue or ("Model" in exp_issue and "Model" in act_issue), f"{cohort_name}: primary issue actual {act_issue} != report {exp_issue}"
        cohort_rows_checked += 1

    assert cohort_rows_checked == 11, f"Expected 11 cohort rows in Table 3.2, found {cohort_rows_checked}"
    assert composite_checked, "Table 3.2 composite row missing"
    print(f"✓ All {cohort_rows_checked} cohorts in Table 3.2 match empirical metrics down to single digit.")

    # 5.3 Section 3.3 Four-Quadrant Parity
    assert "UI/UX Friction (31% — 31 personas)" in report_text, "Section 3.3 UI/UX Friction count mismatch"
    assert "Software Bugs (29% — 29 personas)" in report_text, "Section 3.3 Software Bugs count mismatch"
    assert "Biomarker Data Gaps (20% — 20 personas)" in report_text, "Section 3.3 Biomarker Data Gaps count mismatch"
    assert "Model Generalization Concerns (20% — 20 personas)" in report_text, "Section 3.3 Model Generalization count mismatch"
    print("✓ Section 3.3 Four-Quadrant categorization counts confirmed.")

    # 5.4 Section 3.4 Completion Statuses and Specific Cohort Blockages
    assert "Success (66 personas / 66%)" in report_text, "Section 3.4 Success count mismatch"
    assert "Blocked by Bug (23 personas / 23%)" in report_text, "Section 3.4 Blocked count mismatch"
    assert "Abandoned Due to UX Confusion (11 personas / 11%)" in report_text, "Section 3.4 Abandoned count mismatch"

    ciso_blocked = sum(1 for p in by_arch["Administrator: Hospital IT Security & HIPAA Officer"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    np_blocked = sum(1 for p in by_arch["Clinician: Cardiac Care Nurse Practitioner"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    diabetic_blocked = sum(1 for p in by_arch["Patient: Diabetic Silent Ischemia"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    ed_blocked = sum(1 for p in by_arch["Clinician: Emergency Department Attending"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    female_blocked = sum(1 for p in by_arch["Patient: Female Atypical Microvascular Angina"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    geriatric_abandoned = sum(1 for p in by_arch["Patient: Geriatric Multi-Morbidity"] if p["user_journey"]["completion_status"] == "Abandoned Due to UX Confusion")
    acute_abandoned = sum(1 for p in by_arch["Patient: Acute Chest Pain (High Risk)"] if p["user_journey"]["completion_status"] == "Abandoned Due to UX Confusion")

    assert ciso_blocked == 7 and np_blocked == 2 and diabetic_blocked == 6 and ed_blocked == 3 and female_blocked == 5
    assert geriatric_abandoned == 7 and acute_abandoned == 4
    print("✓ Section 3.4 specific cohort failure and abandonment counts confirmed.")

    # 5.5 Section 3.5 Verbatim Quotes Traceability
    check_ids = ["PERS-001", "PERS-016", "PERS-040", "PERS-053", "PERS-061", "PERS-069", "PERS-075", "PERS-081", "PERS-086", "PERS-094"]
    p_by_id = {p["persona_id"]: p for p in personas}
    for pid in check_ids:
        quote_snip = p_by_id[pid]["feedback_evaluation"]["verbatim_quote"][:40]
        assert quote_snip in report_text, f"Quote fragment for {pid} not found in report Section 3.5: {quote_snip}"
    print(f"✓ All {len(check_ids)} representative verbatim quotes in Section 3.5 matched exactly.")

    print("\n[SUCCESS] 100% Cross-Consistency Parity between personas_100.json and planning_committee_report.md confirmed!")


if __name__ == "__main__":
    validate_personas()
