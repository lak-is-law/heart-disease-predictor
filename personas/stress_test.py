"""Independent Empirical Stress Testing Harness for CardioSense AI Personas (Milestone M1).

Author: teamwork_challenger (Adversarial Critic)
Target: personas/personas_100.json & core.py / artifacts/heart_model.joblib
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from collections import Counter

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import core
import joblib

def run_stress_suite() -> dict:
    results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "failures": [],
        "metrics": {},
    }

    def record_test(name: str, passed: bool, detail: str = ""):
        results["tests_run"] += 1
        if passed:
            results["tests_passed"] += 1
            print(f"[PASS] {name}")
        else:
            results["tests_failed"] += 1
            results["failures"].append({"test": name, "detail": detail})
            print(f"[FAIL] {name}: {detail}")

    json_path = REPO_ROOT / "personas" / "personas_100.json"
    if not json_path.exists():
        record_test("file_existence", False, f"File not found: {json_path}")
        return results
    record_test("file_existence", True)

    with open(json_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    # 1. Exact count
    count = len(personas)
    record_test("exact_100_count", count == 100, f"Expected 100 personas, got {count}")

    # 2. Key uniqueness and format
    persona_ids = [p.get("persona_id") for p in personas]
    expected_ids = [f"PERS-{i:03d}" for i in range(1, 101)]
    record_test("persona_id_sequential_and_unique", persona_ids == expected_ids, f"ID sequence mismatch")

    names = [p.get("name") for p in personas]
    unique_names = set(names)
    record_test("all_names_pairwise_unique", len(unique_names) == 100, f"Found only {len(unique_names)} unique names")

    all_names_valid = all(isinstance(n, str) and len(n.strip()) >= 3 for n in names)
    record_test("all_names_valid_length", all_names_valid, "One or more names too short or invalid")

    expected_top_keys = {
        "persona_id", "name", "archetype", "demographics",
        "clinical_profile", "user_journey", "observed_pain_points", "feedback_evaluation"
    }
    top_keys_match = all(set(p.keys()) == expected_top_keys for p in personas)
    record_test("top_level_keys_exact_match", top_keys_match, "Schema key mismatch in top level")

    # 3. Demographic Balance
    sex_counter = Counter(p["demographics"]["sex"] for p in personas)
    record_test("sex_50_50_balance", sex_counter == {0: 50, 1: 50}, f"Sex counts: {dict(sex_counter)}")

    sex_sync = all(p["demographics"]["sex"] == p["clinical_profile"]["sex"] for p in personas)
    record_test("demographic_clinical_sex_sync", sex_sync, "Sex mismatch between demo and clinical profile")

    age_sync = all(p["demographics"]["age"] == p["clinical_profile"]["age"] for p in personas)
    record_test("demographic_clinical_age_sync", age_sync, "Age mismatch between demo and clinical profile")

    age_tiers = Counter()
    for p in personas:
        a = p["demographics"]["age"]
        if 18 <= a <= 39:
            age_tiers["18-39"] += 1
        elif 40 <= a <= 59:
            age_tiers["40-59"] += 1
        elif 60 <= a <= 79:
            age_tiers["60-79"] += 1
        elif a >= 80:
            age_tiers["80+"] += 1
    expected_age_tiers = {"18-39": 15, "40-59": 45, "60-79": 32, "80+": 8}
    record_test("age_tiers_exact_balance", age_tiers == expected_age_tiers, f"Age tiers: {dict(age_tiers)}")

    ethnicity_counter = Counter(p["demographics"]["ethnicity"] for p in personas)
    expected_ethnicities = {
        "Caucasian": 42,
        "African American": 22,
        "Hispanic/Latino": 18,
        "Asian/Pacific Islander": 14,
        "Native American/Multiracial": 4,
    }
    record_test("ethnicity_exact_balance", ethnicity_counter == expected_ethnicities, f"Ethnicities: {dict(ethnicity_counter)}")

    socio_counter = Counter(p["demographics"]["socioeconomic_tier"] for p in personas)
    expected_socio = {"Middle": 35, "Low": 25, "High": 25, "Uninsured/Safety-Net": 15}
    record_test("socioeconomic_exact_balance", socio_counter == expected_socio, f"Socio: {dict(socio_counter)}")

    setting_counter = Counter(p["demographics"]["clinical_setting"] for p in personas)
    expected_setting = {
        "Community Hospital": 25,
        "Academic Medical Center": 25,
        "Outpatient Cardiology Practice": 20,
        "Rural Critical Access Clinic": 15,
        "Home/Remote Telehealth": 15,
    }
    record_test("clinical_setting_exact_balance", setting_counter == expected_setting, f"Setting: {dict(setting_counter)}")

    literacy_counter = Counter(p["demographics"]["digital_health_literacy"] for p in personas)
    expected_literacy = {"Intermediate": 50, "Advanced Power User": 30, "Basic/Screen-Reader": 20}
    record_test("digital_literacy_exact_balance", literacy_counter == expected_literacy, f"Literacy: {dict(literacy_counter)}")

    archetype_counter = Counter(p["archetype"] for p in personas)
    record_test("archetypes_all_11_present", len(archetype_counter) == 11, f"Found {len(archetype_counter)} archetypes")

    # 4. Biomarker Integrity & Physiological Bounds
    biomarkers_valid = True
    biomarker_error = ""
    for p in personas:
        pid = p["persona_id"]
        cp = p["clinical_profile"]
        for f_name in core.FEATURES:
            if f_name not in cp or cp[f_name] is None:
                biomarkers_valid = False
                biomarker_error = f"{pid}: Missing or null feature '{f_name}'"
                break
        if "ground_truth_cad" not in cp or cp["ground_truth_cad"] not in (0, 1):
            biomarkers_valid = False
            biomarker_error = f"{pid}: Invalid ground_truth_cad"
            break
        # Enum values
        if cp["cp"] not in (1, 2, 3, 4):
            biomarkers_valid = False
            biomarker_error = f"{pid}: cp={cp['cp']} not in (1,2,3,4)"
            break
        if cp["fbs"] not in (0, 1):
            biomarkers_valid = False
            biomarker_error = f"{pid}: fbs={cp['fbs']} not in (0,1)"
            break
        if cp["restecg"] not in (0, 1, 2):
            biomarkers_valid = False
            biomarker_error = f"{pid}: restecg={cp['restecg']} not in (0,1,2)"
            break
        if cp["exang"] not in (0, 1):
            biomarkers_valid = False
            biomarker_error = f"{pid}: exang={cp['exang']} not in (0,1)"
            break
        if cp["slope"] not in (1, 2, 3):
            biomarkers_valid = False
            biomarker_error = f"{pid}: slope={cp['slope']} not in (1,2,3)"
            break
        if cp["ca"] not in (0, 1, 2, 3):
            biomarkers_valid = False
            biomarker_error = f"{pid}: ca={cp['ca']} not in (0,1,2,3)"
            break
        if cp["thal"] not in (3, 6, 7):
            biomarkers_valid = False
            biomarker_error = f"{pid}: thal={cp['thal']} not in (3,6,7)"
            break
        # Ranges
        if not (18 <= cp["age"] <= 95):
            biomarkers_valid = False
            biomarker_error = f"{pid}: age={cp['age']} out of [18, 95]"
            break
        if not (80.0 <= cp["trestbps"] <= 220.0):
            biomarkers_valid = False
            biomarker_error = f"{pid}: trestbps={cp['trestbps']} out of [80, 220]"
            break
        if not (100.0 <= cp["chol"] <= 580.0):
            biomarkers_valid = False
            biomarker_error = f"{pid}: chol={cp['chol']} out of [100, 580]"
            break
        if not (60.0 <= cp["thalach"] <= 215.0):
            biomarkers_valid = False
            biomarker_error = f"{pid}: thalach={cp['thalach']} out of [60, 215]"
            break
        if not (0.0 <= cp["oldpeak"] <= 6.5):
            biomarkers_valid = False
            biomarker_error = f"{pid}: oldpeak={cp['oldpeak']} out of [0, 6.5]"
            break
        # Physiological HR envelope
        max_physio_hr = 220 - cp["age"] + 20
        if cp["thalach"] > max_physio_hr:
            biomarkers_valid = False
            biomarker_error = f"{pid}: thalach={cp['thalach']} exceeds physiological limit {max_physio_hr} for age {cp['age']}"
            break
    record_test("biomarkers_bounds_and_enums", biomarkers_valid, biomarker_error)

    # 5. Planning Committee Dissection & Quotes
    feedback_cat_counter = Counter(p["feedback_evaluation"]["dissected_category"] for p in personas)
    expected_feedback_cats = {
        "Software Bug": 29,
        "UI/UX Friction": 31,
        "Biomarker Data Gap": 20,
        "Model Generalization Concern": 20,
    }
    record_test("feedback_categories_4_quadrants", feedback_cat_counter == expected_feedback_cats, f"Categories: {dict(feedback_cat_counter)}")

    completion_counter = Counter(p["user_journey"]["completion_status"] for p in personas)
    expected_completion = {
        "Success": 66,
        "Blocked by Bug": 23,
        "Abandoned Due to UX Confusion": 11,
    }
    record_test("completion_statuses_exact_balance", completion_counter == expected_completion, f"Completion: {dict(completion_counter)}")

    quotes = [p["feedback_evaluation"]["verbatim_quote"] for p in personas]
    record_test("all_quotes_pairwise_unique", len(set(quotes)) == 100, f"Found only {len(set(quotes))} unique quotes")

    # 6. ML Model Inference Robustness
    model_bundle = joblib.load(REPO_ROOT / "artifacts" / "heart_model.joblib")
    models = model_bundle.get("models", {})
    record_test("model_bundle_contains_models", len(models) >= 2, f"Found models: {list(models.keys())}")

    best_name = model_bundle.get("best", "Logistic Regression")
    best_pipe = models[best_name]

    inference_success = True
    nan_or_inf_detected = False
    out_of_range_detected = False
    all_probs = []
    ground_truths = []

    for p in personas:
        cp = p["clinical_profile"]
        gt = cp["ground_truth_cad"]
        ground_truths.append(gt)

        try:
            prob = core.predict_proba(best_pipe, cp)
        except Exception as exc:
            inference_success = False
            print(f"Inference exception on {p['persona_id']}: {exc}")
            break

        if np.isnan(prob) or np.isinf(prob):
            nan_or_inf_detected = True
            break
        if prob < 0.0 or prob > 1.0:
            out_of_range_detected = True
            break

        all_probs.append(prob)

    record_test("ml_inference_zero_exceptions", inference_success, "Exception occurred during inference")
    record_test("ml_inference_no_nan_or_inf", not nan_or_inf_detected, "NaN or Inf detected in probability")
    record_test("ml_inference_bounds_0_1", not out_of_range_detected, "Probability outside [0.0, 1.0]")

    # Check across ALL models in the bundle
    all_models_clean = True
    for m_name, pipe in models.items():
        for p in personas:
            try:
                pr = core.predict_proba(pipe, p["clinical_profile"])
                if np.isnan(pr) or np.isinf(pr) or not (0.0 <= pr <= 1.0):
                    all_models_clean = False
                    print(f"Model {m_name} failed on {p['persona_id']}: prob={pr}")
                    break
            except Exception as e:
                all_models_clean = False
                print(f"Model {m_name} threw exception on {p['persona_id']}: {e}")
                break
    record_test("all_models_in_bundle_predict_cleanly", all_models_clean, "One or more secondary models failed")

    # Batch vs single inference parity
    df_all = core._frame([p["clinical_profile"] for p in personas])
    batch_probs = best_pipe.predict_proba(df_all)[:, 1]
    single_probs = np.array(all_probs)
    max_batch_diff = float(np.max(np.abs(batch_probs - single_probs)))
    record_test("batch_vs_single_inference_parity", max_batch_diff < 1e-12, f"Max difference: {max_batch_diff}")

    # Risk band distribution
    bands = [core.risk_band(pr)[0] for pr in all_probs]
    band_counts = Counter(bands)
    print(f"Risk band distribution across 100 personas: {dict(band_counts)}")
    all_bands_represented = len(band_counts) == 3
    record_test("all_3_risk_bands_represented", all_bands_represented, f"Risk bands: {dict(band_counts)}")

    # Discriminative validation: High risk archetype vs Low risk archetype
    acute_probs = [
        core.predict_proba(best_pipe, p["clinical_profile"])
        for p in personas if p["archetype"] == "Patient: Acute Chest Pain (High Risk)"
    ]
    routine_probs = [
        core.predict_proba(best_pipe, p["clinical_profile"])
        for p in personas if p["archetype"] == "Patient: Routine Executive Screen (Low Risk)"
    ]
    mean_acute = float(np.mean(acute_probs))
    mean_routine = float(np.mean(routine_probs))
    record_test("clinical_discrimination_acute_vs_routine", mean_acute > mean_routine + 0.35,
                f"Acute mean={mean_acute:.3f}, Routine mean={mean_routine:.3f}")

    # Model discrimination on Ground Truth CAD
    from sklearn.metrics import roc_auc_score, accuracy_score
    cad_roc_auc = float(roc_auc_score(ground_truths, all_probs))
    binary_preds = [1 if pr >= 0.5 else 0 for pr in all_probs]
    cad_acc = float(accuracy_score(ground_truths, binary_preds))
    print(f"Persona cohort ML Metrics: ROC AUC = {cad_roc_auc:.4f}, Accuracy = {cad_acc:.4f}")
    record_test("persona_ml_roc_auc_exceeds_0_80", cad_roc_auc >= 0.80, f"ROC AUC = {cad_roc_auc}")

    # Explainability Stress Test
    baseline = model_bundle.get("baseline")
    explain_ok = True
    if baseline:
        for p in personas:
            try:
                p_exp, deltas = core.explain(best_pipe, p["clinical_profile"], baseline)
                if not (0.0 <= p_exp <= 1.0) or len(deltas) != 13:
                    explain_ok = False
                    break
                if any(np.isnan(d[1]) or np.isinf(d[1]) for d in deltas):
                    explain_ok = False
                    break
            except Exception as e:
                explain_ok = False
                print(f"Explain exception on {p['persona_id']}: {e}")
                break
    record_test("explainability_pipeline_100_percent_pass", explain_ok, "Explainability failed on one or more personas")

    # Extreme edge cases
    youngest = min(personas, key=lambda p: p["clinical_profile"]["age"])
    oldest = max(personas, key=lambda p: p["clinical_profile"]["age"])
    lowest_bp = min(personas, key=lambda p: p["clinical_profile"]["trestbps"])
    highest_bp = max(personas, key=lambda p: p["clinical_profile"]["trestbps"])
    lowest_chol = min(personas, key=lambda p: p["clinical_profile"]["chol"])
    highest_chol = max(personas, key=lambda p: p["clinical_profile"]["chol"])

    print(f"Youngest: {youngest['name']} ({youngest['clinical_profile']['age']}y) -> p={core.predict_proba(best_pipe, youngest['clinical_profile']):.3f}")
    print(f"Oldest: {oldest['name']} ({oldest['clinical_profile']['age']}y) -> p={core.predict_proba(best_pipe, oldest['clinical_profile']):.3f}")
    print(f"Lowest BP: {lowest_bp['name']} ({lowest_bp['clinical_profile']['trestbps']} mmHg) -> p={core.predict_proba(best_pipe, lowest_bp['clinical_profile']):.3f}")
    print(f"Highest BP: {highest_bp['name']} ({highest_bp['clinical_profile']['trestbps']} mmHg) -> p={core.predict_proba(best_pipe, highest_bp['clinical_profile']):.3f}")
    print(f"Lowest Chol: {lowest_chol['name']} ({lowest_chol['clinical_profile']['chol']} mg/dL) -> p={core.predict_proba(best_pipe, lowest_chol['clinical_profile']):.3f}")
    print(f"Highest Chol: {highest_chol['name']} ({highest_chol['clinical_profile']['chol']} mg/dL) -> p={core.predict_proba(best_pipe, highest_chol['clinical_profile']):.3f}")

    results["metrics"] = {
        "total_personas": count,
        "unique_names": len(unique_names),
        "mean_prob": float(np.mean(all_probs)),
        "median_prob": float(np.median(all_probs)),
        "min_prob": float(np.min(all_probs)),
        "max_prob": float(np.max(all_probs)),
        "std_prob": float(np.std(all_probs)),
        "roc_auc": cad_roc_auc,
        "accuracy": cad_acc,
        "band_distribution": dict(band_counts),
        "mean_acute_prob": mean_acute,
        "mean_routine_prob": mean_routine,
        "youngest_age": youngest['clinical_profile']['age'],
        "oldest_age": oldest['clinical_profile']['age'],
        "min_trestbps": lowest_bp['clinical_profile']['trestbps'],
        "max_trestbps": highest_bp['clinical_profile']['trestbps'],
        "min_chol": lowest_chol['clinical_profile']['chol'],
        "max_chol": highest_chol['clinical_profile']['chol'],
    }

    return results

if __name__ == "__main__":
    res = run_stress_suite()
    print("\n================ STRESS SUITE SUMMARY ================")
    print(f"Total Tests Run: {res['tests_run']}")
    print(f"Total Passed:    {res['tests_passed']}")
    print(f"Total Failed:    {res['tests_failed']}")
    if res['tests_failed'] > 0:
        print("\nFailures:")
        for f in res['failures']:
            print(f" - {f['test']}: {f['detail']}")
        sys.exit(1)
    else:
        print("\n[ALL STRESS TESTS PASSED EMPIRICALLY]")
        sys.exit(0)
