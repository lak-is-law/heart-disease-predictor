"""The external-validation tool must run on a multi-site file. Uses a synthetic multi-site file built from
Cleveland (no real external data is in the repo), so this tests the code path, not external performance."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

import core
import external_validation as ev


class TestModelTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

        raw = core.load_raw().copy()
        rng = np.random.default_rng(0)
        raw["dataset"] = rng.choice(["Cleveland", "Hungary", "VA Long Beach"], size=len(raw), p=[0.5, 0.3, 0.2])
        raw.loc[raw["dataset"] == "VA Long Beach", "thal"] = np.nan
        self.multisite_csv = str(self.tmp_path / "multi.csv")
        raw.to_csv(self.multisite_csv, index=False)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_external_validation_runs_and_reports(self):
        res = ev.run(self.multisite_csv)
        self.assertEqual(set(res["external"]), {"all_13", "first_visit"})
        hung = res["external"]["all_13"]["hungary"]
        self.assertTrue(0.5 < hung["auc"] <= 1 and hung["n"] > 20)
        self.assertTrue("at_0.28" in hung and "calibration_slope" in hung)
        self.assertTrue("thal" in res["external"]["all_13"]["va long beach"]["missing_fraction"])
        self.assertTrue("cleveland" in res["leave_one_site_out"]["all_13"])

    def test_external_validation_requires_site_column(self):
        p = self.tmp_path / "single.csv"
        core.load_raw().to_csv(p, index=False)
        with self.assertRaises(SystemExit):
            ev.run(str(p))

    def test_public_claims_match_the_experiment_outputs(self):
        """The numbers on the research page and in the paper must come from artifacts/*.json, not from memory."""
        root = Path(__file__).resolve().parent.parent
        esc = json.loads((root / "artifacts" / "escalation.json").read_text())["alphas"]
        page = (root / "portal" / "research.html").read_text()
        paper = (root / "docs" / "PAPER.md").read_text()
        for alpha, skip in (("0.05", "34%"), ("0.1", "60%")):
            expected = f"{(1 - esc[alpha]['cp']['escalation'][0]) * 100:.0f}%"
            self.assertEqual(expected, skip)
            self.assertIn(skip, page)
            self.assertIn(skip, paper)
        rig = json.loads((root / "artifacts" / "rigor.json").read_text())
        self.assertIn(f"{rig['all_13']['optimism']['corrected_auc']:.3f}", paper)
        self.assertIn(f"{rig['first_visit']['optimism']['corrected_auc']:.3f}", paper)


if __name__ == "__main__":
    unittest.main()
