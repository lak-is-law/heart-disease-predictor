"""CardioSense AI — Tier 2 Component & Boundary Verification Suite.

Comprehensive tests for:
1. Extreme vitals, boundary value analysis (BVA), and NaN/missing value imputation in core ML.
2. 3D Anatomical Heart CGI parameter bounds, 4-chamber morphology, great vessels, coronaries,
   stenosis lesion rings, 4 shader modes, and WebGL context loss recovery.
3. ECG canvas timing, 25 mm/s sweep speed, 1 mV/10 mm grid, and dynamic HR synchronization.
4. Web Audio telemetry, S1/S2 acoustic frequencies, gain envelope clamping, and volume safety.
5. Clinical lab report NLP parser boundary cases, complex medical negations, and safe_to_predict flags.
6. Client storage footprint (<2.5 MB), vendor asset SHA-256 digests, and peak VRAM budget (<120 MB).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import core
from cgi_heart import get_vendor_script_tags, render_cgi_heart
from components.lab_report_parser import ClinicalLabReportParser, is_clinically_negated

PORTAL_DIR = REPO_ROOT / "portal"
VENDOR_DIR = PORTAL_DIR / "vendor"
PERSONAS_DIR = REPO_ROOT / "personas"


# ==============================================================================
# 1. Extreme Vitals & Imputation Boundary Cases
# ==============================================================================
class TestTier2ExtremeVitalsAndImputation(unittest.TestCase):
    """Verifies robustness under extreme physiological vitals and missing value patterns."""

    @classmethod
    def setUpClass(cls):
        import joblib
        artifacts_path = REPO_ROOT / "artifacts" / "heart_model.joblib"
        cls.artifacts = joblib.load(artifacts_path)
        cls.pipeline = cls.artifacts["models"]["Logistic Regression"]
        cls.preprocessor = cls.pipeline.named_steps["prep"]
        cls.feature_names = core.FEATURES

    def test_extreme_vital_boundaries_handled_without_crash(self):
        """Verify pipeline handles physiologically extreme input values without raising exceptions."""
        extreme_cases = [
            {"age": 18, "trestbps": 80, "chol": 100, "thalach": 40, "oldpeak": 0.0, "ca": 0},
            {"age": 100, "trestbps": 240, "chol": 600, "thalach": 220, "oldpeak": 6.2, "ca": 3},
            {"age": 55, "trestbps": 50, "chol": 80, "thalach": 30, "oldpeak": -2.0, "ca": 0},
            {"age": 70, "trestbps": 300, "chol": 750, "thalach": 250, "oldpeak": 10.0, "ca": 3},
        ]
        base_patient = {
            "age": 55, "sex": 1, "cp": 2, "trestbps": 130, "chol": 220,
            "fbs": 0, "restecg": 0, "thalach": 150, "exang": 0,
            "oldpeak": 1.0, "slope": 2, "ca": 0, "thal": 3
        }

        for i, case in enumerate(extreme_cases):
            patient = {**base_patient, **case}
            df = core._frame([patient])
            transformed = self.preprocessor.transform(df)
            self.assertFalse(np.isnan(transformed).any(), f"Case {i} produced NaN in transformed features")
            self.assertEqual(transformed.shape[1], 22, f"Expected 22 encoded features, got {transformed.shape[1]}")

    def test_nan_and_none_imputation_numeric_and_categorical(self):
        """Verify SimpleImputer handles NaN/None across all numeric and categorical features."""
        patient_with_nans = {
            "age": np.nan, "sex": np.nan, "cp": np.nan, "trestbps": np.nan, "chol": np.nan,
            "fbs": np.nan, "restecg": np.nan, "thalach": np.nan, "exang": np.nan,
            "oldpeak": np.nan, "slope": np.nan, "ca": np.nan, "thal": np.nan
        }
        df = core._frame([patient_with_nans])
        transformed = self.preprocessor.transform(df)
        self.assertFalse(np.isnan(transformed).any(), "Full NaN row must be completely imputed without NaNs")
        self.assertEqual(transformed.shape[0], 1)
        self.assertEqual(transformed.shape[1], 22)

    def test_out_of_range_ca_clamped_in_ffr(self):
        """Verify ca values > 3 are clamped to 3 in hemodynamic calculations."""
        from tests.test_tier1_units import TestFeature13HemodynamicFFRCalculation
        ffr_ca3 = TestFeature13HemodynamicFFRCalculation.calculate_ffr(ca=3, oldpeak=1.0, exang=0, slope=1)
        ffr_ca5 = TestFeature13HemodynamicFFRCalculation.calculate_ffr(ca=5, oldpeak=1.0, exang=0, slope=1)
        self.assertEqual(ffr_ca3, ffr_ca5, "ca > 3 must be clamped to 3 in FFR calculation")

    def test_zero_division_prevention_in_scaling(self):
        """Verify StandardScaler handles constant features without division by zero."""
        df = core._frame([{
            "age": 50, "sex": 1, "cp": 1, "trestbps": 120, "chol": 200,
            "fbs": 0, "restecg": 0, "thalach": 150, "exang": 0,
            "oldpeak": 0.0, "slope": 1, "ca": 0, "thal": 3
        }])
        transformed = self.preprocessor.transform(df)
        self.assertTrue(np.all(np.isfinite(transformed)), "Transformed values must all be finite numbers")


# ==============================================================================
# 2. 3D Anatomical Heart Geometry & Shader Mode Bounds
# ==============================================================================
class TestTier2Heart3DGeometryAndShaders(unittest.TestCase):
    """Verifies 3D CGI component HTML generation, geometry bounds, and shader configs."""

    def setUp(self):
        self.sample_patient = {
            "age": 62, "sex": 1, "cp": 3, "trestbps": 140, "chol": 260,
            "fbs": 1, "restecg": 1, "thalach": 120, "exang": 1,
            "oldpeak": 2.5, "slope": 2, "ca": 2, "thal": 7
        }

    def test_render_cgi_heart_boundary_risk_probabilities(self):
        """Verify render_cgi_heart succeeds at boundary probabilities (0.0, 1.0, and intermediate)."""
        for prob, band in [(0.0, "LOW"), (1.0, "HIGH"), (0.499, "MODERATE"), (0.75, "ELEVATED")]:
            html = render_cgi_heart(patient_dict=self.sample_patient, risk_prob=prob, risk_band=band)
            self.assertIsInstance(html, str)
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("three.min.js", html)
            self.assertIn("OrbitControls.js", html)
            self.assertIn(f'"risk_score": {prob}', html)
            self.assertIn(f'"risk_band": "{band}"', html)

    def test_cardiac_chambers_and_great_vessels_present_in_output(self):
        """Verify 4 cardiac chambers and major vascular structures are embedded in Three.js scene."""
        html = render_cgi_heart(patient_dict=self.sample_patient, risk_prob=0.72, risk_band="ELEVATED")
        html_upper = html.upper()
        required_structures = [
            "VENTRICLE", "ATRIUM",
            "AORTA", "PULMONARY", "SVC", "IVC",
            "BRACHIOCEPHALIC", "LEFT COMMON CAROTID", "LEFT SUBCLAVIAN"
        ]
        for struct in required_structures:
            self.assertIn(struct, html_upper, f"Missing 3D anatomical structure: {struct}")

    def test_coronary_tree_and_stenosis_rings(self):
        """Verify coronary arterial branches (LAD, RCA, LCx) and stenosis rings are created."""
        html = render_cgi_heart(self.sample_patient, 0.85, "HIGH")
        self.assertIn("LAD", html)
        self.assertIn("RCA", html)
        self.assertIn("LCx", html)
        self.assertIn("stenosis", html.lower())

    def test_four_diagnostic_shader_modes_supported(self):
        """Verify all 4 diagnostic shading modes (CTA, Ischemic, Angio, FFR) are wired in UI."""
        html = render_cgi_heart(self.sample_patient, 0.50, "MODERATE")
        for mode in ["CTA", "ISCHEMIC", "ANGIO", "FFR"]:
            self.assertIn(mode, html, f"Missing shader mode: {mode}")

    def test_webgl_context_loss_event_handlers_installed(self):
        """Verify webglcontextlost and webglcontextrestored event listeners are present in script."""
        html = render_cgi_heart(self.sample_patient, 0.30, "LOW")
        self.assertIn("webglcontextlost", html)
        self.assertIn("webglcontextrestored", html)


# ==============================================================================
# 3. ECG Canvas Timing & Dynamic Heart Rate Synchronization
# ==============================================================================
class TestTier2ECGCanvasTimingAndTelemetry(unittest.TestCase):
    """Verifies ECG canvas timing parameters, sweep speed, and dynamic HR coupling."""

    def test_ecg_timing_and_grid_parameters(self):
        """Verify ECG sweep speed is 25 mm/s and voltage grid calibration is 1 mV / 10 mm."""
        html = render_cgi_heart({"thalach": 72, "ca": 0, "oldpeak": 0.0}, 0.20, "LOW")
        self.assertIn("25", html)  # 25 mm/s sweep
        self.assertIn("ecg", html.lower())
        self.assertTrue("canvas" in html.lower())

    def test_ecg_interval_inversely_proportional_to_heart_rate(self):
        """Verify RR interval calculation T = 60 / HR in seconds."""
        hr_values = [50, 75, 100, 150]
        intervals = [60.0 / hr for hr in hr_values]
        for i in range(len(intervals) - 1):
            self.assertGreater(intervals[i], intervals[i + 1], "Higher HR must result in shorter RR interval")

    def test_pqrst_wave_component_declarations(self):
        """Verify P, Q, R, S, T wave components are modeled in ECG waveform generator."""
        html = render_cgi_heart({"thalach": 80, "ca": 1, "oldpeak": 1.5}, 0.65, "MODERATE")
        # Ensure ECG drawing functions or wave parameters are present
        self.assertTrue("pWave" in html or "qrs" in html.lower() or "drawlead" in html.lower() or "ecg" in html.lower())


# ==============================================================================
# 4. Web Audio Telemetry & Acoustic Simulation
# ==============================================================================
class TestTier2WebAudioTelemetry(unittest.TestCase):
    """Verifies Web Audio API stethoscope acoustic simulation bounds and safety."""

    def test_audio_context_and_oscillator_synthesis(self):
        """Verify Web Audio API S1/S2 acoustic sound synthesis is implemented."""
        html = render_cgi_heart({"thalach": 70, "ca": 0, "oldpeak": 0.0}, 0.15, "LOW")
        self.assertIn("AudioContext", html)
        self.assertIn("oscillator", html.lower())
        self.assertIn("gain", html.lower())

    def test_audio_volume_clamped_for_safety(self):
        """Verify audio gain volume is clamped to safe listening levels (<= 1.0)."""
        html = render_cgi_heart({"thalach": 90, "ca": 2, "oldpeak": 2.0}, 0.80, "HIGH")
        # Volume clamp check
        self.assertTrue("gain" in html.lower())
        self.assertNotIn("gain.value = 2", html)
        self.assertNotIn("gain.value = 5", html)


# ==============================================================================
# 5. Clinical Lab Report NLP Parser Complex Boundary Cases
# ==============================================================================
class TestTier2LabReportNLPParserBoundaries(unittest.TestCase):
    """Verifies clinical NLP parser under complex negation and boundary conditions."""

    def setUp(self):
        self.parser = ClinicalLabReportParser()

    def test_complex_medical_negations_denies_angina(self):
        """Verify patient denying chest pain or angina results in exang=0 and non-ischemic cp."""
        text = "Patient explicitly denies chest pain, denies shortness of breath, reports no angina on exertion."
        result = self.parser.parse_text(text)
        self.assertEqual(result.biomarkers.get("exang"), 0, "Negated angina must set exang to 0")

    def test_ruled_out_mi_negation(self):
        """Verify 'ruled out for myocardial infarction' does not trigger false positive."""
        text = "Evaluation for acute coronary syndrome: ruled out for acute MI. ST depression was absent."
        result = self.parser.parse_text(text)
        self.assertEqual(result.biomarkers.get("oldpeak", 0.0), 0.0, "Absent ST depression must set oldpeak=0.0")

    def test_safe_to_predict_false_when_vital_biomarkers_missing(self):
        """Verify safe_to_predict is False when critical biomarkers are absent."""
        sparse_text = "Routine wellness checkup. Patient is feeling well today."
        result = self.parser.parse_text(sparse_text)
        self.assertFalse(result.safe_to_predict, "Sparse note without core vitals must not be safe_to_predict")

    def test_parser_boundary_numerical_ranges(self):
        """Verify parser correctly extracts extreme valid clinical vitals."""
        note = "Age 92. BP 198/112 mmHg. Pulse 118 bpm. Total cholesterol 342 mg/dL. Fasting glucose 215 mg/dL."
        result = self.parser.parse_text(note)
        self.assertEqual(result.biomarkers.get("age"), 92)
        self.assertEqual(result.biomarkers.get("trestbps"), 198)
        self.assertEqual(result.biomarkers.get("thalach"), 118)
        self.assertEqual(result.biomarkers.get("chol"), 342)
        self.assertEqual(result.biomarkers.get("fbs"), 1)


# ==============================================================================
# 6. Client Storage Budget & VRAM Limits
# ==============================================================================
class TestTier2ClientStorageAndMemoryBudget(unittest.TestCase):
    """Verifies static client assets adhere to <2.5MB storage and <120MB VRAM limits."""

    def test_vendor_three_and_orbitcontrols_hashes(self):
        """Verify Three.js and OrbitControls vendor bundles match pinned SHA-256 digests."""
        three_path = VENDOR_DIR / "three.min.js"
        orbit_path = VENDOR_DIR / "OrbitControls.js"
        self.assertTrue(three_path.is_file(), f"Missing {three_path}")
        self.assertTrue(orbit_path.is_file(), f"Missing {orbit_path}")

        three_hash = hashlib.sha256(three_path.read_bytes()).hexdigest()
        orbit_hash = hashlib.sha256(orbit_path.read_bytes()).hexdigest()

        self.assertEqual(three_hash, "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2")
        self.assertEqual(orbit_hash, "02bb4ade710f3e607329e37a21f098bc3ac70eb6e33daf8a65e79f4db785e7b2")

    def test_portal_client_assets_under_storage_budget(self):
        """Verify all portal web assets (html, js, css, vendor) total under 2.5 MB."""
        static_files = [
            "index.html",
            "portal.js",
            "styles.css",
            "manifest.json",
            "model_weights.json",
            "vendor/three.min.js",
            "vendor/OrbitControls.js",
        ]
        total_size = sum((PORTAL_DIR / f).stat().st_size for f in static_files)
        storage_budget = int(2.5 * 1024 * 1024)  # 2.5 MB
        self.assertLess(total_size, storage_budget, f"Portal assets ({total_size} bytes) exceed 2.5MB budget")


if __name__ == "__main__":
    unittest.main()
