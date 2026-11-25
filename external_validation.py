"""External validation of the CardioSense model on other hospitals.

    python external_validation.py --data data/heart_disease_uci.csv

The Kaggle/UCI multi-site file (920 patients: Cleveland, Hungary, Switzerland, VA Long Beach) has a
`dataset` column. The model is trained on Cleveland only (as shipped) and then scored, untouched, on
each other site. That is a far stronger test than cross-validation inside Cleveland, because the
patients come from different hospitals, countries and referral patterns.

It also reports leave-one-site-out results, calibration, and how much of each site's data was missing
(Switzerland and the VA file are missing many vessel and thallium values, which the model fills with
the Cleveland median; that is itself a finding).

Writes artifacts/external_validation.json. Needs the multi-site file, which is not in the repo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

import core

SEED = 7
FIRST_VISIT = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg"]


def load_sites(path: str):
    raw = core.load_raw(path)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    if "dataset" not in raw.columns:
        raise SystemExit("This file has no 'dataset' column, so sites cannot be told apart. "
                         "Use the multi-site Kaggle file (heart_disease_uci.csv).")
    keep = pd.to_numeric(raw["num"], errors="coerce").notna().to_numpy()
    site = raw["dataset"].astype(str).str.strip().str.lower().to_numpy()[keep]
    X, y = core.normalize(raw)
    return X, y.to_numpy(), site


def boot_ci(y, p, n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y)); vals = []
    for _ in range(n):
        s = rng.choice(idx, len(idx))
        if y[s].min() != y[s].max():
            vals.append(roc_auc_score(y[s], p[s]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [None, None]


def summarize(y, p, X, cols):
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    out = {"n": int(len(y)), "prevalence": float(y.mean())}
    if y.min() == y.max():
        out["note"] = "only one outcome class present; AUC undefined"
        return out
    cal = LogisticRegression(C=1e6).fit(logit.reshape(-1, 1), y)
    out.update({
        "auc": float(roc_auc_score(y, p)), "auc_ci95": boot_ci(y, p), "brier": float(brier_score_loss(y, p)),
        "calibration_slope": float(cal.coef_[0, 0]), "calibration_intercept": float(cal.intercept_[0]),
        "mean_predicted": float(p.mean()),
        "missing_fraction": {c: float(X[c].isna().mean()) for c in cols if X[c].isna().mean() > 0.05},
    })
    for t in (0.5, 0.28):
        pred = p >= t
        tp = int((pred & (y == 1)).sum()); fn = int((~pred & (y == 1)).sum())
        tn = int((~pred & (y == 0)).sum()); fp = int((pred & (y == 0)).sum())
        out[f"at_{t}"] = {"sensitivity": tp / max(tp + fn, 1), "specificity": tn / max(tn + fp, 1), "missed": fn, "false_alarms": fp}
    return out


def fit(X, y, cols):
    return clone(core.build_models(SEED)["Logistic Regression"]).fit(X[core.FEATURES], y) if cols == core.FEATURES else _fit_cols(X, y, cols)


def _fit_cols(X, y, cols):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    num = [c for c in cols if c not in core.CATEGORICAL]; cat = [c for c in cols if c in core.CATEGORICAL]
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat)])
    return Pipeline([("prep", pre), ("clf", LogisticRegression(max_iter=3000, C=0.7))]).fit(X[cols], y)


def run(path: str, train_site: str = "cleveland") -> dict:
    X, y, site = load_sites(path)
    res = {"train_site": train_site, "sites": {s: int((site == s).sum()) for s in sorted(set(site))}, "external": {}, "leave_one_site_out": {}}
    if train_site not in res["sites"]:
        raise SystemExit(f"No rows for site '{train_site}'. Sites present: {sorted(res['sites'])}")
    for set_name, cols in (("all_13", core.FEATURES), ("first_visit", FIRST_VISIT)):
        tr = site == train_site
        m = fit(X[tr].reset_index(drop=True), y[tr], cols)
        res["external"][set_name] = {}
        for s in sorted(set(site) - {train_site}):
            te = site == s
            res["external"][set_name][s] = summarize(y[te], m.predict_proba(X[te][cols])[:, 1], X[te], cols)
        res["leave_one_site_out"][set_name] = {}
        for s in sorted(set(site)):
            te = site == s
            if (~te).sum() < 50:
                continue
            m = fit(X[~te].reset_index(drop=True), y[~te], cols)
            res["leave_one_site_out"][set_name][s] = summarize(y[te], m.predict_proba(X[te][cols])[:, 1], X[te], cols)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train-site", default="cleveland")
    a = ap.parse_args()
    res = run(a.data, a.train_site.lower())
    Path(__file__).parent.joinpath("artifacts", "external_validation.json").write_text(json.dumps(res, indent=2))
    for set_name, sites in res["external"].items():
        for s, r in sites.items():
            if "auc" in r:
                print(f"{set_name:12s} {s:14s} n={r['n']:3d} AUC {r['auc']:.3f} ({r['auc_ci95'][0]:.3f}-{r['auc_ci95'][1]:.3f}) "
                      f"slope {r['calibration_slope']:.2f} sens@0.5 {r['at_0.5']['sensitivity']:.2f} spec@0.5 {r['at_0.5']['specificity']:.2f}")
            else:
                print(f"{set_name:12s} {s:14s} {r.get('note')}")


if __name__ == "__main__":
    main()
