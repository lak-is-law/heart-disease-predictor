"""Empirical Challenge & Stress Test Suite for Milestone M3.
Authored by m3_challenger_1.

Empirically verifies:
1. Exact mathematical parity between Python artifacts/heart_model.joblib and
   JavaScript portal/portal.js (executed directly in Node.js) across all 100
   clinical personas in personas/personas_100.json (max drift < 1e-12) and edge cases.
2. Clinical Hagen-Poiseuille FFR bounds [0.48, 0.98] and monotonicity under multi-vessel CAD.
3. Adversarial clinical NLP parsing in components/lab_report_parser.py:
   - Inverted negations and contrasting conjunction boundaries.
   - Disguised false positive tokens (98.6 F, 500 bp, 10 mg fixed, flat affect, Page 12).
   - Multi-page, corrupt, zero-byte, and scanned PDF streams.
   - Strict < 3 biomarker safety abort guardrail.
4. Streamlit app.py Tab 5 execution stability under simulated randomized user sessions.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import unittest
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
PORTAL_DIR = REPO_ROOT / "portal"
PERSONAS_FILE = REPO_ROOT / "personas" / "personas_100.json"
MODEL_FILE = ARTIFACTS_DIR / "heart_model.joblib"
WEIGHTS_FILE = PORTAL_DIR / "model_weights.json"
PORTAL_JS_FILE = PORTAL_DIR / "portal.js"


def run_node_eval(script: str, args: list[str] | None = None) -> str:
    """Executes a Node.js snippet with mock browser DOM globals and returns stdout."""
    harness = """
const fs = require('fs');
global.window = global;
global.document = {
  addEventListener: () => {},
  getElementById: () => null,
  querySelectorAll: () => [],
  createElement: () => ({ setAttribute: () => {}, style: {}, appendChild: () => {} }),
  body: { appendChild: () => {}, removeChild: () => {} }
};
global.navigator = { userAgent: 'node', clipboard: { writeText: async () => {} } };
const code = fs.readFileSync('""" + str(PORTAL_JS_FILE).replace("\\", "/") + """', 'utf8');
eval(code + '\\nglobal.MODEL_WEIGHTS = MODEL_WEIGHTS;\\nglobal.predictClinicalRisk = predictClinicalRisk;\\nglobal.calculateClinicalFFR = calculateClinicalFFR;');
""" + script

    cmd = ["node", "-e", harness]
    if args:
        cmd.extend(args)
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()


class TestM3ChallengerMathematicalParity(unittest.TestCase):
    """Empirical mathematical parity stress tests between Python and Node.js."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = joblib.load(MODEL_FILE)
        cls.pipe = cls.bundle["models"]["Logistic Regression"]
        cls.features = cls.bundle["meta"]["features"]
        cls.baseline = cls.bundle["baseline"]

        with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
            cls.personas = json.load(f)
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            cls.weights = json.load(f)

    def test_model_weights_json_ast_parity_with_portal_js(self):
        """portal/model_weights.json must match embedded MODEL_WEIGHTS in portal.js."""
        res = run_node_eval("console.log(JSON.stringify(MODEL_WEIGHTS));")
        js_weights = json.loads(res)

        self.assertAlmostEqual(self.weights["intercept"], js_weights["intercept"], places=14)
        for i, (c1, c2) in enumerate(zip(self.weights["coef"], js_weights["coef"])):
            self.assertAlmostEqual(c1, c2, places=14, msg=f"Coef {i} mismatch")
        for i, (m1, m2) in enumerate(zip(self.weights["num_mean"], js_weights["num_mean"])):
            self.assertAlmostEqual(m1, m2, places=14, msg=f"Mean {i} mismatch")
        for i, (s1, s2) in enumerate(zip(self.weights["num_scale"], js_weights["num_scale"])):
            self.assertAlmostEqual(s1, s2, places=14, msg=f"Scale {i} mismatch")

    def test_exact_parity_across_all_100_personas_in_node(self):
        """Python scikit-learn vs Node.js portal.js across all 100 personas must drift < 1e-12."""
        profiles = [p["clinical_profile"] for p in self.personas]

        # Python prediction
        df = pd.DataFrame(profiles)[self.features].astype(float)
        py_preds = self.pipe.predict_proba(df)[:, 1]

        # Node.js prediction
        node_script = """
const profiles = JSON.parse(process.argv[1]);
const preds = profiles.map(p => predictClinicalRisk(p));
console.log(JSON.stringify(preds));
"""
        res = run_node_eval(node_script, [json.dumps(profiles)])
        js_preds = np.array(json.loads(res))

        drifts = np.abs(py_preds - js_preds)
        max_drift = float(np.max(drifts))
        mean_drift = float(np.mean(drifts))

        print(f"\n[M3 Challenger] 100 Personas Node.js vs Python drift: max={max_drift:.3e}, mean={mean_drift:.3e}")
        self.assertLess(max_drift, 1e-12, f"Persona drift exceeded 1e-12: max={max_drift}")

    def test_edge_case_patient_vectors_parity(self):
        """Extreme edge case vectors in Python vs Node.js must maintain parity < 1e-12."""
        edge_cases = [
            # 1. All min values
            {"age": 18, "sex": 0, "cp": 1, "trestbps": 80, "chol": 100, "fbs": 0, "restecg": 0, "thalach": 60, "exang": 0, "oldpeak": 0.0, "slope": 1, "ca": 0, "thal": 3},
            # 2. All max values
            {"age": 100, "sex": 1, "cp": 4, "trestbps": 240, "chol": 600, "fbs": 1, "restecg": 2, "thalach": 230, "exang": 1, "oldpeak": 6.2, "slope": 3, "ca": 3, "thal": 7},
            # 3. Alternating extremes
            {"age": 18, "sex": 1, "cp": 1, "trestbps": 240, "chol": 100, "fbs": 1, "restecg": 0, "thalach": 230, "exang": 0, "oldpeak": 6.2, "slope": 1, "ca": 3, "thal": 3},
            # 4. Zero values
            {"age": 0, "sex": 0, "cp": 0, "trestbps": 0, "chol": 0, "fbs": 0, "restecg": 0, "thalach": 0, "exang": 0, "oldpeak": 0.0, "slope": 0, "ca": 0, "thal": 0},
            # 5. Missing values (empty dict defaults to baseline)
            {},
            # 6. Partial dictionary (only age and chol)
            {"age": 68, "chol": 340},
            # 7. Unseen categorical levels (cp=99, restecg=99, slope=99, thal=99)
            {"age": 55, "sex": 1, "cp": 99, "trestbps": 130, "chol": 240, "fbs": 0, "restecg": 99, "thalach": 150, "exang": 0, "oldpeak": 1.0, "slope": 99, "ca": 0, "thal": 99},
            # 8. Negative biomarker inputs
            {"age": -20, "trestbps": -10, "chol": -50, "thalach": -80, "oldpeak": -2.5},
        ]

        # In Python, fill missing keys with baseline
        filled_cases = []
        for ec in edge_cases:
            c = dict(self.baseline)
            c.update(ec)
            filled_cases.append(c)

        df = pd.DataFrame(filled_cases)[self.features].astype(float)
        py_preds = self.pipe.predict_proba(df)[:, 1]

        node_script = """
const cases = JSON.parse(process.argv[1]);
const preds = cases.map(p => predictClinicalRisk(p));
console.log(JSON.stringify(preds));
"""
        res = run_node_eval(node_script, [json.dumps(edge_cases)])
        js_preds = np.array(json.loads(res))

        drifts = np.abs(py_preds - js_preds)
        max_drift = float(np.max(drifts))

        print(f"[M3 Challenger] Edge cases Node.js vs Python drift: max={max_drift:.3e}")
        self.assertLess(max_drift, 1e-12, f"Edge case drift exceeded 1e-12: max={max_drift}")


class TestM3ChallengerClinicalFFR(unittest.TestCase):
    """Stress testing Hagen-Poiseuille FFR calculations in Node.js and Python."""

    def test_ffr_bounds_and_monotonicity_in_node(self):
        """calculateClinicalFFR in Node.js must stay bounded in [0.48, 0.98] with 0 monotonicity violations."""
        node_script = """
let minVal = 1.0;
let maxVal = 0.0;
let violations = 0;

for (let ca = 0; ca <= 4; ca += 0.5) {
  for (let oldpeak = -2; oldpeak <= 8; oldpeak += 0.25) {
    for (let exang of [0, 1]) {
      for (let slope of [1, 2, 3]) {
        const val = calculateClinicalFFR(ca, oldpeak, exang, slope);
        if (val < minVal) minVal = val;
        if (val > maxVal) maxVal = val;
        if (val < 0.48 || val > 0.98 || isNaN(val)) {
          violations++;
        }
      }
    }
  }
}

// Monotonicity check across ca levels (0 -> 1 -> 2 -> 3)
let caMonotonicityViolations = 0;
for (let oldpeak = 0; oldpeak <= 5.0; oldpeak += 0.5) {
  for (let exang of [0, 1]) {
    for (let slope of [1, 2, 3]) {
      let prev = calculateClinicalFFR(0, oldpeak, exang, slope);
      for (let ca = 1; ca <= 3; ca++) {
        const curr = calculateClinicalFFR(ca, oldpeak, exang, slope);
        if (curr > prev + 1e-12) {
          caMonotonicityViolations++;
        }
        prev = curr;
      }
    }
  }
}

console.log(JSON.stringify({ minVal, maxVal, violations, caMonotonicityViolations }));
"""
        res = run_node_eval(node_script)
        data = json.loads(res)

        self.assertGreaterEqual(data["minVal"], 0.48)
        self.assertLessEqual(data["maxVal"], 0.98)
        self.assertEqual(data["violations"], 0)
        self.assertEqual(data["caMonotonicityViolations"], 0)

    def test_ffr_adversarial_null_undefined_extremes(self):
        """calculateClinicalFFR must gracefully handle non-numeric inputs without crashing."""
        node_script = """
const testInputs = [
  [null, null, null, null],
  [undefined, undefined, undefined, undefined],
  [NaN, NaN, NaN, NaN],
  [-999, -999, -999, -999],
  [9999, 9999, 9999, 9999]
];
const results = testInputs.map(([c, o, e, s]) => calculateClinicalFFR(c, o, e, s));
console.log(JSON.stringify(results));
"""
        res = run_node_eval(node_script)
        results = json.loads(res)

        for val in results:
            self.assertFalse(math.isnan(val))
            self.assertGreaterEqual(val, 0.48)
            self.assertLessEqual(val, 0.98)


class TestM3ChallengerLabReportParserAdversarial(unittest.TestCase):
    """Adversarial challenge for components/lab_report_parser.py."""

    @classmethod
    def setUpClass(cls):
        from components.lab_report_parser import ClinicalLabReportParser
        cls.parser = ClinicalLabReportParser(min_extracted_for_prediction=3)

    def test_disguised_false_positive_tokens(self):
        """Adversarial non-clinical tokens must NOT trigger biomarker extractions."""
        # 1. Body temperature 98.6 F must not be heart rate or blood pressure
        r1 = self.parser.parse_text("Patient afebrile at 98.6 F. Routine physical.")
        self.assertFalse(r1.metadata["thalach"].extracted)
        self.assertFalse(r1.metadata["trestbps"].extracted)

        # 2. DNA basepairs (500 bp) must not be resting blood pressure
        r2 = self.parser.parse_text("Gel electrophoresis showed a distinct 500 bp band.")
        self.assertFalse(r2.metadata["trestbps"].extracted)

        # 3. Fixed medication dose (10 mg fixed) must not trigger thal=6 (fixed defect)
        r3 = self.parser.parse_text("Prescribed lisinopril 10 mg fixed daily dose.")
        self.assertFalse(r3.metadata["thal"].extracted)

        # 4. Psychiatric 'flat affect' must not trigger slope=2 (flat ST)
        r4 = self.parser.parse_text("Psychiatric evaluation reveals depressed mood and flat affect.")
        self.assertFalse(r4.metadata["slope"].extracted)

        # 5. Page number (Page 12 of 20) must not trigger age=12
        r5 = self.parser.parse_text("Clinical Record Page 12 of 20.")
        self.assertFalse(r5.metadata["age"].extracted)

        # 6. HDL cholesterol must not overwrite total cholesterol
        r6 = self.parser.parse_text("Lipid panel: HDL cholesterol 45 mg/dL. Triglycerides 150 mg/dL.")
        self.assertFalse(r6.metadata["chol"].extracted)

    def test_clinical_negation_scope_and_contrast_boundaries(self):
        """Clinical negations with contrasting conjunctions (but, however) must respect clause bounds."""
        # Affirmative finding followed by negation
        text1 = "Patient presents with crushing chest pain, but denies shortness of breath or nausea."
        r1 = self.parser.parse_text(text1)
        self.assertTrue(r1.metadata["cp"].extracted)
        self.assertEqual(r1.biomarkers["cp"], 1)  # Typical angina preserved
        self.assertFalse(r1.metadata["cp"].is_negated)

        # Direct explicit negation
        text2 = "Patient denies chest pain, denies exertional angina, free of dyspnea."
        r2 = self.parser.parse_text(text2)
        self.assertTrue(r2.metadata["cp"].extracted)
        self.assertEqual(r2.biomarkers["cp"], 4)  # Asymptomatic
        self.assertTrue(r2.metadata["cp"].is_negated)

        # Negated exercise angina
        text3 = "Stress ECG: exercise-induced angina: negative. No ischemic ST changes."
        r3 = self.parser.parse_text(text3)
        self.assertTrue(r3.metadata["exang"].extracted)
        self.assertEqual(r3.biomarkers["exang"], 0)

    def test_safety_abort_guardrail_thresholds(self):
        """Parser must enforce < 3 biomarker safety abort guardrail."""
        # 0 biomarkers
        r0 = self.parser.parse_text("General hospital intake without vitals.")
        self.assertEqual(r0.extracted_count, 0)
        self.assertFalse(r0.safe_to_predict)

        # 1 biomarker (age only)
        r1 = self.parser.parse_text("Patient is a 62 year old individual.")
        self.assertEqual(r1.extracted_count, 1)
        self.assertFalse(r1.safe_to_predict)

        # 2 biomarkers (age + BP)
        r2 = self.parser.parse_text("Patient is 62 yo, BP 138/84.")
        self.assertEqual(r2.extracted_count, 2)
        self.assertFalse(r2.safe_to_predict)

        # 3 biomarkers (age + BP + cholesterol) -> Meets minimum safety threshold
        r3 = self.parser.parse_text("Patient 62 yo, BP 138/84, total cholesterol: 245.")
        self.assertEqual(r3.extracted_count, 3)
        self.assertTrue(r3.safe_to_predict)

    def test_corrupted_and_scanned_pdf_handling(self):
        """Parser must safely process corrupt and scanned PDF streams without crashing."""
        # Zero-byte input
        r_zero = self.parser.parse_file(b"", "empty.pdf")
        self.assertEqual(r_zero.extracted_count, 0)
        self.assertFalse(r_zero.safe_to_predict)

        # Corrupted PDF bytes
        r_corrupt = self.parser.parse_file(b"%PDF-1.4 \x00\xff truncated invalid", "corrupt.pdf")
        self.assertEqual(r_corrupt.extracted_count, 0)
        self.assertFalse(r_corrupt.safe_to_predict)

        # Scanned PDF image stream
        scanned_pdf = b"%PDF-1.4\n<< /Type /XObject /Subtype /Image >>\nstream\nendstream\n%%EOF"
        r_scan = self.parser.parse_file(scanned_pdf, "scan.pdf")
        self.assertFalse(r_scan.safe_to_predict)
        self.assertTrue(any("OCR required" in w for w in r_scan.warnings))


class TestM3ChallengerAppTestTab5(unittest.TestCase):
    """Stress testing Streamlit app.py Tab 5 execution with AppTest."""

    def test_app_tab5_initial_and_randomized_session_execution(self):
        """app.py must execute cleanly under empty session state and randomized user sessions."""
        from streamlit.testing.v1 import AppTest

        app_path = str(REPO_ROOT / "app.py")

        # 1. Initial execution with empty session state
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Initial run threw exceptions: {[e.value for e in at.exception]}")

        # Verify Tab 5 security controls and cryptographic seal in output
        md_vals = [m.value for m in at.markdown]
        self.assertTrue(any("Enterprise Security Architecture & Clinical Checkup" in t for t in md_vals))
        self.assertTrue(any("CARDIOSENSE-SEAL" in t for t in md_vals))
        self.assertTrue(any("ALL CONTROLS COMPLIANT" in t for t in md_vals))
        self.assertEqual(len(at.download_button), 1)

        # 2. Simulated randomized user sessions
        valid_options = {
            "sex": [0, 1],
            "fbs": [0, 1],
            "cp": [1, 2, 3, 4],
            "restecg": [0, 1, 2],
            "thal": [3, 6, 7],
            "exang": [0, 1],
            "slope": [1, 2, 3],
            "ca": [0, 1, 2, 3],
            None: ["Logistic Regression", "Random Forest", "Gradient Boosting"],
        }

        for session_idx in range(5):
            for s in at.slider:
                val = float(random.choice([int(s.min), int(s.max), int((s.min + s.max) / 2)]))
                s.set_value(val)

            for sb in at.selectbox:
                opts = valid_options.get(sb.key)
                if opts:
                    sb.select(random.choice(opts))

            at.run()
            self.assertEqual(
                len(at.exception),
                0,
                f"Session {session_idx + 1} threw exceptions: {[e.value for e in at.exception]}",
            )


if __name__ == "__main__":
    unittest.main()
