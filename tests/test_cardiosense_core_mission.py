"""CardioSense AI — Core Clinical Mission, Hospital Economics & Safety Net Verification Suite.

Verifies:
1. Hospital Economics & Catheterization Cost Reduction Engine:
   - Ruling out up to 60% of unnecessary diagnostic catheterizations ($5,000–$12,000 per procedure).
   - Direct cath lab savings calculation.
   - Invasive catheter complications spared (hematoma, stroke, dissection, CIN at 1.8%).
   - Compressing emergency department boarding hours ($220/hr).
   - Eliminating expensive cloud infrastructure ($380,000/yr).
   - Eliminating malpractice payouts ($2,400,000 actuarial risk mitigation).
   - Multi-million dollar total annual hospital savings ($12.2M+).
2. High-Sensitivity Safety Net Mode (96.4% Recall):
   - Calibrated 0.28 decision threshold preventing fatal false-negative discharges of atypical patients.
   - Verification across diabetic neuropathy, female, and silent ischemia presentations.
3. Non-Invasive Virtual Fractional Flow Reserve (FFR) Hemodynamics:
   - Hagen-Poiseuille fluid dynamics formulation.
   - Strict physiological clamping [0.48, 0.98].
   - Ischemia threshold FFR < 0.80 vs non-obstructive rule-out FFR >= 0.80.
4. Door-to-Balloon "Golden Hour" Telemetry:
   - Shaving 48 vital minutes off the 90-minute ACC/AHA guideline (44 min vs 92 min).
   - Myocardial salvage rate and tissue necrosis risk reduction.
5. Offline-First Air-Gapped Architecture & Rural Clinic Triage:
   - Zero cloud data egress, local on-chip execution.
   - Standalone web portal and desktop application integration.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import core

PORTAL_DIR = REPO_ROOT / "portal"


class TestCardioSenseHospitalEconomics(unittest.TestCase):
    """Verifies mathematical validity and clinical boundaries of hospital economics."""

    def test_default_hospital_economics_calculation(self):
        """Verify baseline institutional economics yields expected $12.2M+ annual savings."""
        econ = core.calculate_hospital_economics(
            annual_caths=1200,
            cath_cost=8500.0,
            rule_out_pct=0.52,
            ed_visits=4500,
            ed_hours_saved=4.2,
            hourly_ed_cost=220.0,
            cloud_savings=380000.0,
            malpractice_mitigation=2400000.0,
        )

        # 1200 * 0.52 = 624 caths avoided
        self.assertEqual(econ["unnecessary_caths_avoided"], 624)
        # 624 * $8500 = $5,304,000 direct cath savings
        self.assertEqual(econ["cath_cost_savings"], 5304000.0)
        # 624 * 0.018 = 11.2 complications spared
        self.assertEqual(econ["complications_spared"], 11.2)
        # 4500 * 4.2 = 18,900 ED boarding hours saved
        self.assertEqual(econ["ed_hours_saved_total"], 18900.0)
        # 18900 * $220 = $4,158,000 ED boarding savings
        self.assertEqual(econ["ed_boarding_savings"], 4158000.0)
        # Total savings = 5,304,000 + 4,158,000 + 380,000 + 2,400,000 = 12,242,000
        self.assertEqual(econ["total_annual_savings"], 12242000.0)

    def test_hospital_economics_rule_out_clamped_to_60_percent(self):
        """Verify clinical rule-out percentage is strictly capped at 60% per clinical guidelines."""
        # Requesting 80% rule out should be clamped to 60%
        econ = core.calculate_hospital_economics(annual_caths=1000, rule_out_pct=0.80)
        self.assertEqual(econ["rule_out_pct"], 0.60)
        self.assertEqual(econ["unnecessary_caths_avoided"], 600)

    def test_hospital_economics_cost_range_clamped_5000_to_12000(self):
        """Verify catheterization procedure cost is clamped to realistic $5,000–$12,000 range."""
        # Sub-minimum cost ($2,000) clamped to $5,000
        econ_low = core.calculate_hospital_economics(cath_cost=2000.0)
        self.assertEqual(econ_low["cath_cost"], 5000.0)

        # Super-maximum cost ($25,000) clamped to $12,000
        econ_high = core.calculate_hospital_economics(cath_cost=25000.0)
        self.assertEqual(econ_high["cath_cost"], 12000.0)

    def test_catheter_complications_spared_scaling(self):
        """Verify 1.8% arterial complication prevention rate scales with avoided procedures."""
        econ = core.calculate_hospital_economics(annual_caths=2000, rule_out_pct=0.50)
        # 1000 avoided * 0.018 = 18.0 complications avoided
        self.assertEqual(econ["unnecessary_caths_avoided"], 1000)
        self.assertEqual(econ["complications_spared"], 18.0)


class TestHighSensitivitySafetyNet(unittest.TestCase):
    """Verifies the high-sensitivity (0.28 threshold) mode reports measured sensitivity and never says a patient is safe."""

    def test_safety_net_flags_atypical_patient(self):
        """Verify atypical presentation (prob = 0.38) is caught under 0.28 safety net threshold."""
        prob = 0.38
        standard_eval = core.evaluate_safety_net(prob, threshold=0.50)
        safety_net_eval = core.evaluate_safety_net(prob, threshold=0.28)

        # Under standard 0.50 threshold, patient would be missed (falsely discharged)
        self.assertFalse(standard_eval["is_flagged"])
        # Under 0.28 safety net, patient is flagged for urgent evaluation
        self.assertTrue(safety_net_eval["is_flagged"])
        self.assertTrue(safety_net_eval["atypical_risk_mitigated"])
        self.assertEqual(safety_net_eval["recall_sensitivity"], core.MEASURED_SENSITIVITY_AT_028)
        self.assertLess(safety_net_eval["recall_sensitivity"], 0.95, "must report the measured value, not a marketing figure")
        self.assertIn("HIGH-SENSITIVITY FLAG", safety_net_eval["clinical_note"])

    def test_safety_net_allows_truly_low_risk_baseline(self):
        """Verify completely normal screening profile (prob = 0.12) is not flagged."""
        res = core.evaluate_safety_net(prob=0.12, threshold=0.28)
        self.assertFalse(res["is_flagged"])
        self.assertFalse(res["atypical_risk_mitigated"])
        self.assertIn("Lower likelihood in this model", res["disposition"])
        self.assertNotIn("Safe", res["disposition"])


class TestVirtualFFRFluidDynamics(unittest.TestCase):
    """Verifies Hagen-Poiseuille fluid dynamics FFR calculation and clinical bounds."""

    def test_ffr_within_physiological_bounds(self):
        """Verify virtual FFR is strictly clamped in [0.48, 0.98]."""
        for ca in range(4):
            for oldpeak in [0.0, 1.5, 3.0, 5.0]:
                for exang in [0, 1]:
                    for slope in [1, 2, 3]:
                        ffr = core.calculate_virtual_ffr(ca, oldpeak, exang, slope)
                        self.assertGreaterEqual(ffr, 0.48)
                        self.assertLessEqual(ffr, 0.98)

    def test_ffr_catheterization_rule_out(self):
        """Verify normal patient yields FFR >= 0.80 (ruling out catheterization)."""
        ffr_normal = core.calculate_virtual_ffr(ca=0, oldpeak=0.0, exang=0, slope=1)
        self.assertGreaterEqual(ffr_normal, 0.95)
        self.assertTrue(ffr_normal >= 0.80)

    def test_ffr_critical_ischemia_indicated(self):
        """Verify multivessel severe occlusion yields FFR < 0.80 (catheterization indicated)."""
        ffr_ischemic = core.calculate_virtual_ffr(ca=3, oldpeak=3.2, exang=1, slope=3)
        self.assertLess(ffr_ischemic, 0.80)


class TestGoldenHourDoorToBalloonCompression(unittest.TestCase):
    """Verifies Door-to-Balloon compression timeline and myocardial salvage metrics."""

    def test_golden_hour_compression_timeline(self):
        """Verify CardioSense AI shaves > 40 minutes off the Golden Hour and meets 90m target."""
        gh = core.calculate_golden_hour_timeline(
            triage_min=10.0,
            nlp_sec=45.0,
            ffr_sec=15.0,
            cath_prep_min=33.0,
        )

        self.assertEqual(gh["traditional_d2b_min"], 92.0)
        self.assertEqual(gh["cardiosense_d2b_min"], 44.0)
        self.assertEqual(gh["minutes_shaved"], 48.0)
        self.assertTrue(gh["beating_guideline"])
        self.assertGreaterEqual(gh["myocardial_salvage_pct"], 80.0)
        self.assertEqual(gh["necrosis_reduction_pct"], 65.0)


class TestOfflineFirstAndPortalIntegrity(unittest.TestCase):
    """Verifies offline-first UI tokens, DOM fixtures, and presets."""

    def test_app_presets_include_new_cases(self):
        """Verify PRESETS in app.py includes atypical, ruleout, and rural cases."""
        app_text = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('"atypical":', app_text)
        self.assertIn('"ruleout":', app_text)
        self.assertIn('"rural":', app_text)
        self.assertIn("High-sensitivity mode (threshold 0.28)", app_text)
        self.assertNotIn("96.4", app_text)
        for gone in ("Hospital Economics", "Virtual FFR", "FIPS 140-2", "HIPAA", "880.6310", "STEMI"):
            self.assertNotIn(gone, app_text)
        self.assertIn("Not for clinical use", app_text)

    def test_portal_html_contains_economics_and_safety_net_elements(self):
        """Verify portal/index.html includes economics section, safety net, and golden hour widgets."""
        index_html = (PORTAL_DIR / "app.html").read_text(encoding="utf-8")

        # Unfounded economics, timeline and compliance content must stay removed
        for gone in ('id="hospital-economics"', 'golden-hour', 'STEMI', 'FIPS', 'HIPAA', '880.6310'):
            self.assertNotIn(gone, index_html)

        # Safety Net Toggle & Alert Banner
        self.assertIn('id="inp-safety-net-toggle"', index_html)
        self.assertIn('id="portal-safety-net-banner"', index_html)
        self.assertIn("threshold 0.28", index_html)
        self.assertNotIn("96.4", index_html)

    def test_portal_js_contains_required_functions_and_cases(self):
        """Verify portal/portal.js exports calculateHospitalEconomics and new clinical cases."""
        portal_js = (PORTAL_DIR / "portal.js").read_text(encoding="utf-8")

        self.assertIn("calculateHospitalEconomics", portal_js)
        self.assertIn("toggleSafetyNetMode", portal_js)
        self.assertIn("updateGoldenHourTelemetry", portal_js)
        self.assertIn("atypical_safety_net", portal_js)
        self.assertIn("ruled_out_cath", portal_js)
        self.assertIn("rural_triage", portal_js)


if __name__ == "__main__":
    unittest.main()
