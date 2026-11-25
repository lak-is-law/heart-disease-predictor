"""Honest evaluation of the CardioSense model on the Cleveland data.

    python evaluate.py              # writes artifacts/validation.json and prints a summary

Method: 20 repeats of stratified 5-fold cross-validation. Every patient gets an out-of-fold
probability in every repeat (the model never sees that patient when scoring them). Metrics are
computed on the repeat-averaged probabilities with bootstrap 95% intervals over patients.
This is internal validation on one 1980s US clinic dataset. It is not external validation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

import core

SEED = 7
SETS = {
    "all_13": core.FEATURES,
    # needs no exercise test, fluoroscopy or nuclear scan: what a clinic can collect at a first visit
    "first_visit": ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg"],
    # same, without the resting ECG
    "no_tests": ["age", "sex", "cp", "trestbps", "chol", "fbs"],
}


def oof(X, y, cols, repeats=20):
    pipe = core.build_models(SEED)["Logistic Regression"]
    if cols != core.FEATURES:  # rebuild the preprocessor for the reduced column set
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sklearn.linear_model import LogisticRegression as LR
        num = [c for c in cols if c not in core.CATEGORICAL]
        cat = [c for c in cols if c in core.CATEGORICAL]
        pre = ColumnTransformer([
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
            ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat),
        ])
        pipe = Pipeline([("prep", pre), ("clf", LR(max_iter=3000, C=0.7))])
    n = len(y)
    acc = np.zeros((repeats, n))
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=SEED)
    for i, (tr, te) in enumerate(rskf.split(X, y)):
        m = clone(pipe).fit(X.iloc[tr][cols], y.iloc[tr])
        acc[i // 5, te] = m.predict_proba(X.iloc[te][cols])[:, 1]
    return acc


def boot(fn, y, p, n=1000, rng=np.random.default_rng(SEED)):
    vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        s = rng.choice(idx, len(idx))
        if y[s].min() == y[s].max():
            continue
        vals.append(fn(y[s], p[s]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def at(y, p, t):
    pred = p >= t
    tp = int(((pred) & (y == 1)).sum()); fn = int(((~pred) & (y == 1)).sum())
    tn = int(((~pred) & (y == 0)).sum()); fp = int(((pred) & (y == 0)).sum())
    return {
        "threshold": t, "sensitivity": tp / (tp + fn), "specificity": tn / (tn + fp),
        "ppv": tp / (tp + fp) if tp + fp else None, "npv": tn / (tn + fn) if tn + fn else None,
        "missed_cases": fn, "false_alarms": fp,
    }


def main():
    X, y = core.normalize(core.load_raw())
    yv = y.to_numpy()
    out = {"n": int(len(y)), "prevalence": float(yv.mean()), "method": "20x repeated stratified 5-fold CV, out-of-fold, bootstrap 95% CI", "sets": {}}
    for name, cols in SETS.items():
        acc = oof(X, y, cols)
        p = acc.mean(axis=0)
        per_repeat = [roc_auc_score(yv, a) for a in acc]
        lo, hi = boot(roc_auc_score, yv, p)
        logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
        cal = LogisticRegression(C=1e6).fit(logit.reshape(-1, 1), yv)
        res = {
            "features": cols, "auc": float(roc_auc_score(yv, p)), "auc_ci95": [lo, hi],
            "auc_repeat_sd": float(np.std(per_repeat)), "brier": float(brier_score_loss(yv, p)),
            "calibration_slope": float(cal.coef_[0, 0]), "calibration_intercept": float(cal.intercept_[0]),
            "operating_points": [at(yv, p, t) for t in (0.28, 0.33, 0.5)],
        }
        for label, mask in (("female", X["sex"].to_numpy() == 0), ("male", X["sex"].to_numpy() == 1)):
            if len(set(yv[mask])) == 2:
                res[f"auc_{label}"] = float(roc_auc_score(yv[mask], p[mask]))
                res[f"n_{label}"] = int(mask.sum())
        for lo_age, hi_age, label in ((0, 54, "under55"), (55, 200, "55plus")):
            m = (X["age"].to_numpy() >= lo_age) & (X["age"].to_numpy() <= hi_age)
            res[f"auc_{label}"] = float(roc_auc_score(yv[m], p[m]))
        out["sets"][name] = res
    path = Path(__file__).parent / "artifacts" / "validation.json"
    path.write_text(json.dumps(out, indent=2))
    for name, r in out["sets"].items():
        o = r["operating_points"][0]
        print(f"{name:12s} AUC {r['auc']:.3f} (95% CI {r['auc_ci95'][0]:.3f}-{r['auc_ci95'][1]:.3f}) | "
              f"@0.28 sens {o['sensitivity']:.3f} spec {o['specificity']:.3f} missed {o['missed_cases']} | "
              f"F {r.get('auc_female', 0):.3f} M {r.get('auc_male', 0):.3f} slope {r['calibration_slope']:.2f}")


if __name__ == "__main__":
    main()
