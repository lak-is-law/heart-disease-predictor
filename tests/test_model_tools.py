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
