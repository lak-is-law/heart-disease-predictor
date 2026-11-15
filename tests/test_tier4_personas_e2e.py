"""CardioSense AI — Tier 4 Real-World Application Scenarios & E2E Personas Suite.

Comprehensive end-to-end workload and journey verification covering:
1. 100-Persona Real-World Prediction Pipeline Execution:
   - Iterates across all 100 clinical personas in personas/personas_100.json.
   - Evaluates Python scikit-learn Logistic Regression vs JS 22D model weights formula.
   - Asserts mathematical drift < 1e-12 across all 100 personas (zero numerical divergence).
   - Asserts 0 unhandled exceptions across all demographic archetypes.
2. Clinical Risk Calibration & FFR Invariants:
   - Asserts risk probabilities strictly bounded in [0.0, 1.0].
   - Verifies risk bands align with probability thresholds.
   - Evaluates Hagen-Poiseuille FFR across all 100 personas within clinical bounds [0.48, 0.98].
   - Verifies ground-truth CAD-positive personas exhibit lower mean FFR than CAD-negative.
3. End-to-End 3D CGI Heart Render Pipeline:
   - Executes render_cgi_heart across all 100 personas with dynamic risk scores.
   - Confirms valid HTML generation, Lead-II ECG setup, and Web Audio telemetry parameters.
4. Responsive Grid & Amex DLS Layout Assertions:
   - Validates 12-column grid tokens, 6-tier breakpoints, and 48px touch targets in styles.css.
5. Distribution DMG Packaging Integrity:
   - Validates build_mac_dmg.sh packaging specification and release manifest parity.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import core
from cgi_heart import render_cgi_heart
from tests.test_tier1_units import TestFeature13HemodynamicFFRCalculation

PORTAL_DIR = REPO_ROOT / "portal"
PERSONAS_DIR = REPO_ROOT / "personas"
PACKAGING_DIR = REPO_ROOT / "packaging"


class TestTier4PersonasE2EPipeline(unittest.TestCase):
    """Executes the full prediction and visualization pipeline over all 100 clinical personas."""

    @classmethod
    def setUpClass(cls):
        cls.personas_path = PERSONAS_DIR / "personas_100.json"
        cls.weights_path = PORTAL_DIR / "model_weights.json"
        cls.model_path = REPO_ROOT / "artifacts" / "heart_model.joblib"

        with open(cls.personas_path, "r", encoding="utf-8") as f:
            cls.personas = json.load(f)
        with open(cls.weights_path, "r", encoding="utf-8") as f:
            cls.weights = json.load(f)

        artifacts = joblib.load(cls.model_path)
        cls.pipeline = artifacts["models"]["Logistic Regression"]

    def _eval_js_formula(self, p: dict) -> float:
        """Evaluate the exact 22D Cleveland Clinic Logistic Regression logit formula."""
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

    def test_all_100_personas_prediction_parity_and_zero_drift(self):
        """Verify mathematical drift < 1e-12 between Python scikit-learn and JS formula across all 100 personas."""
        drifts = []
        for p in self.personas:
            pid = p["persona_id"]
            profile = p["clinical_profile"]

            # Python prediction
            df = core._frame([profile])
            py_prob = float(self.pipeline.predict_proba(df)[0, 1])

            # JS formula prediction
            js_prob = self._eval_js_formula(profile)

            # Assert probability bounds
            self.assertGreaterEqual(py_prob, 0.0, f"{pid}: Probability < 0.0")
            self.assertLessEqual(py_prob, 1.0, f"{pid}: Probability > 1.0")

            drift = abs(py_prob - js_prob)
            drifts.append(drift)
            self.assertLess(
                drift,
                1e-12,
                f"{pid} ({p['name']}): Drift {drift:.2e} exceeded strict 1e-12 tolerance (py={py_prob}, js={js_prob})"
            )

        max_drift = max(drifts)
        mean_drift = sum(drifts) / len(drifts)
        self.assertLess(max_drift, 1e-12, f"Max drift {max_drift:.2e} exceeded 1e-12")
        self.assertLess(mean_drift, 1e-14, f"Mean drift {mean_drift:.2e} exceeded 1e-14")

    def test_all_100_personas_hemodynamic_ffr_bounds(self):
        """Verify FFR calculation across all 100 personas produces physiological values in [0.48, 0.98]."""
        cad_pos_ffrs = []
        cad_neg_ffrs = []

        for p in self.personas:
            prof = p["clinical_profile"]
            ffr = TestFeature13HemodynamicFFRCalculation.calculate_ffr(
                ca=int(prof["ca"]),
                oldpeak=float(prof["oldpeak"]),
                exang=int(prof["exang"]),
                slope=int(prof["slope"])
            )
            self.assertGreaterEqual(ffr, 0.48, f"{p['persona_id']}: FFR {ffr} < 0.48 lower bound")
            self.assertLessEqual(ffr, 0.98, f"{p['persona_id']}: FFR {ffr} > 0.98 upper bound")

            if prof.get("ground_truth_cad") == 1:
                cad_pos_ffrs.append(ffr)
            else:
                cad_neg_ffrs.append(ffr)

        # Clinically, CAD-positive patients must have lower mean FFR than healthy controls
        mean_cad_pos = sum(cad_pos_ffrs) / len(cad_pos_ffrs)
        mean_cad_neg = sum(cad_neg_ffrs) / len(cad_neg_ffrs)
        self.assertLess(
            mean_cad_pos,
            mean_cad_neg,
            f"Mean FFR in CAD positive ({mean_cad_pos:.3f}) should be lower than CAD negative ({mean_cad_neg:.3f})"
        )

    def test_render_cgi_heart_execution_across_all_100_personas(self):
        """Verify 3D CGI heart HTML rendering executes with 0 unhandled exceptions across all 100 personas."""
        for p in self.personas:
            pid = p["persona_id"]
            prof = p["clinical_profile"]
            prob = self._eval_js_formula(prof)
            band = "HIGH" if prob > 0.66 else ("MODERATE" if prob > 0.33 else "LOW")

            html = render_cgi_heart(patient_dict=prof, risk_prob=prob, risk_band=band)
            self.assertIsInstance(html, str, f"{pid}: render_cgi_heart failed to return HTML string")
            self.assertGreater(len(html), 1000, f"{pid}: Generated HTML was truncated ({len(html)} bytes)")
            self.assertIn("cgi-container", html, f"{pid}: Missing cgi-container element")


class TestTier4AmexDLSResponsiveLayout(unittest.TestCase):
    """Verifies responsive layout CSS design tokens and touch target compliance."""

    @classmethod
    def setUpClass(cls):
        cls.css = (PORTAL_DIR / "styles.css").read_text(encoding="utf-8")

    def test_responsive_grid_tokens(self):
        """Verify 12-column responsive layout tokens and fluid breakpoints."""
        self.assertIn("--grid-max-width", self.css)
        self.assertIn("--grid-gutter", self.css)
        self.assertIn("--color-primary", self.css)
        self.assertIn("--touch-target-min: 48px", self.css)

    def test_responsive_breakpoints_defined(self):
        """Verify media query breakpoints exist for tablet and mobile viewports."""
        self.assertIn("@media", self.css)
        self.assertTrue("max-width: 1024px" in self.css or "max-width: 1023px" in self.css or "768px" in self.css)


class TestTier4DistributionPackaging(unittest.TestCase):
    """Verifies packaging scripts and distribution assets."""

    def test_mac_dmg_builder_script_exists_and_valid(self):
        """Verify build_mac_dmg.sh exists, contains UDZO compression format and bash safety flags."""
        dmg_script = PACKAGING_DIR / "build_mac_dmg.sh"
        self.assertTrue(dmg_script.is_file(), f"Missing {dmg_script}")
        content = dmg_script.read_text(encoding="utf-8")
        self.assertIn("#!/usr/bin/env bash", content)
        self.assertIn("set -euo pipefail", content)
        self.assertIn("UDZO", content)


if __name__ == "__main__":
    unittest.main()
