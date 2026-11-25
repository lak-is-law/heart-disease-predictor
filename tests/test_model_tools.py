"""The external-validation tool must run on a multi-site file. Uses a synthetic multi-site file built from
Cleveland (no real external data is in the repo), so this tests the code path, not external performance."""
import numpy as np
import pandas as pd
import pytest

import core
import external_validation as ev


@pytest.fixture()
def multisite_csv(tmp_path):
    raw = core.load_raw()
    raw = raw.copy()
    rng = np.random.default_rng(0)
    raw["dataset"] = rng.choice(["Cleveland", "Hungary", "VA Long Beach"], size=len(raw), p=[0.5, 0.3, 0.2])
    raw.loc[raw["dataset"] == "VA Long Beach", "thal"] = np.nan
    path = tmp_path / "multi.csv"
    raw.to_csv(path, index=False)
    return str(path)


def test_external_validation_runs_and_reports(multisite_csv):
    res = ev.run(multisite_csv)
    assert set(res["external"]) == {"all_13", "first_visit"}
    hung = res["external"]["all_13"]["hungary"]
    assert 0.5 < hung["auc"] <= 1 and hung["n"] > 20
    assert "at_0.28" in hung and "calibration_slope" in hung
    assert "thal" in res["external"]["all_13"]["va long beach"]["missing_fraction"]
    assert "cleveland" in res["leave_one_site_out"]["all_13"]


def test_external_validation_requires_site_column(tmp_path):
    p = tmp_path / "single.csv"
    core.load_raw().to_csv(p, index=False)
    with pytest.raises(SystemExit):
        ev.run(str(p))


def test_public_claims_match_the_experiment_outputs():
    """The numbers on the research page and in the paper must come from artifacts/*.json, not from memory."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    esc = json.loads((root / "artifacts" / "escalation.json").read_text())["alphas"]
    page = (root / "portal" / "research.html").read_text()
    paper = (root / "docs" / "PAPER.md").read_text()
    for alpha, skip in (("0.05", "34%"), ("0.1", "60%")):
        assert f"{(1 - esc[alpha]['cp']['escalation'][0]) * 100:.0f}%" == skip
        assert skip in page and skip in paper
    rig = json.loads((root / "artifacts" / "rigor.json").read_text())
    assert f"{rig['all_13']['optimism']['corrected_auc']:.3f}" in paper
    assert f"{rig['first_visit']['optimism']['corrected_auc']:.3f}" in paper
