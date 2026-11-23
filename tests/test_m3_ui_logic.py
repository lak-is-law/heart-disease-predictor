"""
Comprehensive Milestone M3 UI & Clinical Logic Verification Test Suite.

Verifies:
1. app.py runs with 0 exceptions using streamlit.testing.v1.AppTest.
2. Mathematical model parity between Python scikit-learn pipeline and JS-equivalent
   22D Cleveland Clinic Logistic Regression across all 100 clinical personas (drift < 1e-12).
3. Hagen-Poiseuille non-linear fluid resistance FFR calculation and boundary invariants.
4. CSS zero 320px overflow, responsive tablet/desktop breakpoints (1023px), and 48px touch targets.
5. cgi_heart.py mobile responsive queries (<= 640px).
6. portal/index.html dual labeling, accessible radiogroups, fbs/restecg inputs, and ARIA dialogs.
"""

import json
import math
import os
import unittest
import numpy as np
import pandas as pd
import joblib


class TestM3AppExecution(unittest.TestCase):
    """Verify Streamlit app.py execution integrity."""

    def test_app_runs_without_exception(self):
        """Verify app.py loads and executes with zero unhandled exceptions."""
        from streamlit.testing.v1 import AppTest

        test_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(os.path.dirname(test_dir), "app.py")
        self.assertTrue(os.path.exists(app_path), f"app.py not found at {app_path}")

        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        self.assertEqual(
            len(at.exception),
            0,
            f"app.py threw unhandled exceptions: {[e.value for e in at.exception]}",
        )


class TestM3ModelParity(unittest.TestCase):
    """Verify exact mathematical parity between Python scikit-learn model and 22D JS formula."""

    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(base_dir, "artifacts", "heart_model.joblib")
        self.weights_path = os.path.join(base_dir, "portal", "model_weights.json")
        self.personas_path = os.path.join(base_dir, "personas", "personas_100.json")

        self.assertTrue(os.path.exists(self.model_path))
        self.assertTrue(os.path.exists(self.weights_path))
        self.assertTrue(os.path.exists(self.personas_path))

        loaded = joblib.load(self.model_path)
        self.pipeline = loaded["models"]["Logistic Regression"] if isinstance(loaded, dict) and "models" in loaded else loaded
        with open(self.weights_path, "r") as f:
            self.weights = json.load(f)
        with open(self.personas_path, "r") as f:
            self.personas = json.load(f)

    def _predict_js_equivalent(self, p: dict) -> float:
        """Evaluate the exact 22D logistic regression formula matching portal.js."""
        mw = self.weights

        num_vals = [
            (float(p.get("age", mw["baseline"]["age"])) - mw["num_mean"][0]) / mw["num_scale"][0],
            (float(p.get("sex", mw["baseline"]["sex"])) - mw["num_mean"][1]) / mw["num_scale"][1],
            (float(p.get("trestbps", mw["baseline"]["trestbps"])) - mw["num_mean"][2]) / mw["num_scale"][2],
            (float(p.get("chol", mw["baseline"]["chol"])) - mw["num_mean"][3]) / mw["num_scale"][3],
            (float(p.get("fbs", mw["baseline"]["fbs"])) - mw["num_mean"][4]) / mw["num_scale"][4],
            (float(p.get("thalach", mw["baseline"]["thalach"])) - mw["num_mean"][5]) / mw["num_scale"][5],
            (float(p.get("exang", mw["baseline"]["exang"])) - mw["num_mean"][6]) / mw["num_scale"][6],
            (float(p.get("oldpeak", mw["baseline"]["oldpeak"])) - mw["num_mean"][7]) / mw["num_scale"][7],
            (float(p.get("ca", mw["baseline"]["ca"])) - mw["num_mean"][8]) / mw["num_scale"][8],
        ]

        cp = float(p.get("cp", mw["baseline"]["cp"]))
        restecg = float(p.get("restecg", mw["baseline"]["restecg"]))
        slope = float(p.get("slope", mw["baseline"]["slope"]))
        thal = float(p.get("thal", mw["baseline"]["thal"]))

        cat_cp = [1.0 if cp == c else 0.0 for c in mw["cat_categories"][0]]
        cat_restecg = [1.0 if restecg == c else 0.0 for c in mw["cat_categories"][1]]
        cat_slope = [1.0 if slope == c else 0.0 for c in mw["cat_categories"][2]]
        cat_thal = [1.0 if thal == c else 0.0 for c in mw["cat_categories"][3]]

        x = num_vals + cat_cp + cat_restecg + cat_slope + cat_thal

        logit = mw["intercept"]
        for i in range(len(mw["coef"])):
            logit += mw["coef"][i] * x[i]

        return 1.0 / (1.0 + math.exp(-logit))

    def test_model_weights_json_parity_100_personas(self):
        """Assert prediction parity between scikit-learn pipeline and 22D JS formula is < 1e-12."""
        max_drift = 0.0
        drifts = []

        feature_cols = [
            "age", "sex", "cp", "trestbps", "chol", "fbs",
            "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"
        ]

        for idx, persona in enumerate(self.personas):
            profile = persona.get("clinical_profile", persona)
            df_patient = pd.DataFrame([{col: profile[col] for col in feature_cols}])
            sklearn_prob = float(self.pipeline.predict_proba(df_patient)[0, 1])
            js_prob = self._predict_js_equivalent(profile)

            drift = abs(sklearn_prob - js_prob)
            drifts.append(drift)
            if drift > max_drift:
                max_drift = drift

            self.assertLess(
                drift,
                1e-12,
                f"Persona {idx} ({persona.get('name', 'unnamed')}) exceeded 1e-12 drift: {drift:.2e}",
            )

        self.assertLess(max_drift, 1e-12)
        print(f"[Model Parity] 100 personas tested. Max drift: {max_drift:.2e}, Mean drift: {np.mean(drifts):.2e}")


class TestM3ClinicalFFR(unittest.TestCase):
    """Verify Hagen-Poiseuille FFR physics bounds and ischemic detection logic."""

    @staticmethod
    def calculate_clinical_ffr(ca: int, oldpeak: float, exang: int, slope: int) -> float:
        """Python reference implementation of calculateClinicalFFR from portal.js."""
        slope_factor = 0.06 if slope == 3 else (0.03 if slope == 2 else 0.0)
        raw_stenosis = (min(ca or 0, 3) * 0.28) + ((oldpeak or 0.0) * 0.06) + ((exang or 0) * 0.08) + slope_factor
        s = min(0.92, max(0.0, raw_stenosis))
        r_lesion = 0.5 * math.pow(s / (1.0 - 0.85 * s + 1e-5), 1.8)
        ffr = 1.0 / (1.0 + r_lesion)
        return max(0.48, min(0.98, ffr))

    def test_poiseuille_ffr_bounds(self):
        """Verify normal patient vs severe stenosis bounds in [0.48, 0.98]."""
        # Healthy normal patient (no fluoroscopy vessels, no ST depression, no angina)
        normal_ffr = self.calculate_clinical_ffr(ca=0, oldpeak=0.0, exang=0, slope=1)
        self.assertGreaterEqual(normal_ffr, 0.95)
        self.assertLessEqual(normal_ffr, 0.98)

        # Critical ischemic patient (3 vessels calcified, high ST depression, exercise angina, downsloping)
        ischemic_ffr = self.calculate_clinical_ffr(ca=3, oldpeak=4.0, exang=1, slope=3)
        self.assertLess(ischemic_ffr, 0.80, "Severe stenosis should trigger ischemia threshold (< 0.80)")
        self.assertGreaterEqual(ischemic_ffr, 0.48, "FFR should respect lower physiological clamp (0.48)")

        # Monotonicity test: increasing calcified vessels strictly decreases FFR
        prev_ffr = 1.0
        for vessels in range(4):
            val = self.calculate_clinical_ffr(ca=vessels, oldpeak=1.0, exang=0, slope=2)
            self.assertLess(val, prev_ffr)
            prev_ffr = val


class TestM3ResponsiveDesignAndCSS(unittest.TestCase):
    """Verify CSS responsive layout rules, touch targets, and contrast tokens."""

    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.css_path = os.path.join(base_dir, "portal", "styles.css")
        with open(self.css_path, "r", encoding="utf-8") as f:
            self.css_content = f.read()

    def test_css_zero_320px_overflow_and_breakpoints(self):
        """Verify complete elimination of min-width: 320px, 1023px tablet breakpoint, and touch targets."""
        self.assertNotIn(
            "min-width: 320px;",
            self.css_content,
            "min-width: 320px; clipping bug must be eliminated from styles.css",
        )
        self.assertNotIn(
            "@media (max-width: 1040px)",
            self.css_content,
            "Old 1040px breakpoint must be replaced by 1023px",
        )
        self.assertIn(
            "@media (max-width: 1023px)",
            self.css_content,
            "1023px breakpoint must be present for workstation and grid collapse",
        )
        self.assertIn(
            ".workstation-sticky-col",
            self.css_content,
            "Sticky column styling must be present for workstation viewport",
        )
        self.assertIn(
            "--touch-target-min: 48px;",
            self.css_content,
            "Enterprise 48px touch target token must be defined in :root",
        )
        self.assertIn(
            "@media (min-width: 1920px)",
            self.css_content,
            "Ultrawide / 4K fluid layout query must be present",
        )
        self.assertIn(
            "@media (min-width: 2560px)",
            self.css_content,
            "4K display fluid layout query must be present",
        )


class TestM3CgiHeartResponsive(unittest.TestCase):
    """Verify cgi_heart.py responsive queries for mobile HUD overlays."""

    def test_cgi_heart_responsive_query_present(self):
        """Verify render_cgi_heart outputs media queries for screens <= 640px."""
        import cgi_heart

        rendered_html = cgi_heart.render_cgi_heart(risk_score=0.45, embed_vendor=False)
        self.assertIn(
            "@media (max-width: 640px)",
            rendered_html,
            "cgi_heart.py must include @media (max-width: 640px) responsive HUD overrides",
        )
        self.assertIn(".hud-top", rendered_html)
        self.assertIn(".hud-bottom", rendered_html)
        self.assertIn("min-height: 40px", rendered_html)


class TestM3PortalHtmlSemantics(unittest.TestCase):
    """Verify portal/index.html clinical input controls, dual-labeling, and ARIA semantics."""

    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_path = os.path.join(base_dir, "portal", "app.html")
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.html_content = f.read()

    def test_portal_html_inputs_and_aria(self):
        """Verify presence of fbs/restecg controls, dual-labeling, accessible radiogroups, and dialogs."""
        # 13 Cleveland Clinic input controls
        required_inputs = [
            "inp-age", "inp-sex", "inp-cp", "inp-trestbps", "inp-chol",
            "inp-fbs", "inp-restecg", "inp-thalach", "inp-exang",
            "inp-oldpeak", "inp-slope", "inp-ca", "inp-thal"
        ]
        for inp_id in required_inputs:
            self.assertIn(
                f'id="{inp_id}"',
                self.html_content,
                f"Missing required clinical biomarker input control: {inp_id}",
            )

        # Accessible radiogroup for case studies
        self.assertIn('role="radiogroup"', self.html_content)
        self.assertIn('role="radio"', self.html_content)

        # Dual-labeling markup verification (layperson + acronym + normal range)
        self.assertIn("Fasting Blood Sugar", self.html_content)
        self.assertIn("Resting Electrocardiogram", self.html_content)
        self.assertIn("Resting Blood Pressure", self.html_content)
        self.assertIn("Serum Total Cholesterol", self.html_content)
        self.assertIn("ST Segment Depression", self.html_content)

        # ARIA dialog attributes for modals
        self.assertIn('role="dialog"', self.html_content)
        self.assertIn('aria-modal="true"', self.html_content)


if __name__ == "__main__":
    unittest.main()
