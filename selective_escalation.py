"""Selective escalation: who actually needs the expensive tests?

Research question. The full CardioSense model needs results from an exercise test, fluoroscopy and a nuclear
scan. A first-visit model (age, sex, chest pain, blood pressure, cholesterol, glucose, resting ECG) needs none
of them but is less accurate (AUC 0.84 vs 0.91). Can a conformal uncertainty estimate from the first-visit model
decide which patients can be handled at the first visit and which should be escalated to the full work-up,
while keeping the decisions of the full pipeline?

Policy (two stages)
  1. Fit the first-visit model and calibrate a split-conformal predictor at miscoverage level alpha.
  2. If the conformal set holds ONE class, accept that class (no further tests).
     If it holds both classes, escalate: obtain the full work-up and use the full model.
Reference policy: send EVERYONE to the full work-up (full model at 0.5).

Metrics, per patient, out of fold: escalation rate (share who need the extra tests), accuracy, sensitivity,
specificity, and missed cases. A matched non-conformal band policy (escalate when the first-visit probability is
in a central band chosen to give the same escalation rate) is the control, to test whether conformal adds anything.

    python selective_escalation.py     # writes artifacts/escalation.json

Internal validation on Cleveland (303 patients). Not external validation. Escalation here means "the extra
tests are available for the patient"; the cost of the tests is not modelled.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split

import core
from benchmark import models

warnings.filterwarnings("ignore")
SEED = 7
FIRST = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg"]
ALPHAS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30]


def lr(cols):
    return models(cols)["LR C=0.7 (shipped)"]


def conformal_q(p_cal, y_cal, alpha):
    s = np.where(y_cal == 1, 1 - p_cal, p_cal)
    k = int(np.ceil((len(s) + 1) * (1 - alpha)))
    return np.sort(s)[min(k, len(s)) - 1]


def metrics(y, pred, esc):
    tp = int(((pred == 1) & (y == 1)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    return {"escalation": float(esc.mean()), "accuracy": (tp + tn) / len(y), "sensitivity": tp / max(tp + fn, 1),
            "specificity": tn / max(tn + fp, 1), "missed": fn, "false_alarms": fp}


def run(repeats=10):
    X, y = core.normalize(core.load_raw()); yv = y.to_numpy(); n = len(yv)
    rec = {a: {"cp": [], "band": []} for a in ALPHAS}; ref = []
    per_patient = {a: {"correct_cp": np.zeros(n), "esc": np.zeros(n)} for a in ALPHAS}; ref_correct = np.zeros(n)
    rng = np.random.default_rng(SEED)
    for r in range(repeats):
        pred_ref = np.zeros(n, int)
        cp_pred = {a: np.zeros(n, int) for a in ALPHAS}; cp_esc = {a: np.zeros(n, bool) for a in ALPHAS}
        band_pred = {a: np.zeros(n, int) for a in ALPHAS}; band_esc = {a: np.zeros(n, bool) for a in ALPHAS}
        folds = list(StratifiedKFold(5, shuffle=True, random_state=int(rng.integers(1e9))).split(X, yv))
        for tr, te in folds:
            fit_i, cal_i = train_test_split(tr, test_size=0.3, stratify=yv[tr], random_state=int(rng.integers(1e9)))
            Xf, yf = X.iloc[fit_i], yv[fit_i]
            m1 = lr(FIRST).fit(Xf[FIRST], yf); m2 = lr(core.FEATURES).fit(Xf[core.FEATURES], yf)
            pc = m1.predict_proba(X.iloc[cal_i][FIRST])[:, 1]
            p1 = m1.predict_proba(X.iloc[te][FIRST])[:, 1]; p2 = m2.predict_proba(X.iloc[te][core.FEATURES])[:, 1]
            pred_ref[te] = (p2 >= 0.5).astype(int)
            for a in ALPHAS:
                q = conformal_q(pc, yv[cal_i], a)
                in1 = (1 - p1) <= q; in0 = p1 <= q
                single = in1 ^ in0
                esc = ~single
                pred = np.where(single, in1.astype(int), (p2 >= 0.5).astype(int))
                cp_pred[a][te] = pred; cp_esc[a][te] = esc
                # control: central band on the first-visit probability with the same escalation rate on this test fold
                rate = esc.mean()
                if rate > 0:
                    d = np.abs(p1 - 0.5); thr = np.quantile(d, rate); bsc = d <= thr
                else:
                    bsc = np.zeros(len(te), bool)
                band_pred[a][te] = np.where(bsc, (p2 >= 0.5).astype(int), (p1 >= 0.5).astype(int)); band_esc[a][te] = bsc
        ref.append(metrics(yv, pred_ref, np.ones(n, bool))); ref_correct += (pred_ref == yv)
        for a in ALPHAS:
            rec[a]["cp"].append(metrics(yv, cp_pred[a], cp_esc[a])); rec[a]["band"].append(metrics(yv, band_pred[a], band_esc[a]))
            per_patient[a]["correct_cp"] += (cp_pred[a] == yv); per_patient[a]["esc"] += cp_esc[a]
    agg = lambda L, k: [float(np.mean([m[k] for m in L])), float(np.std([m[k] for m in L]))]
    out = {"n": n, "repeats": repeats, "reference_full_model_everyone": {k: agg(ref, k) for k in ("accuracy", "sensitivity", "specificity", "missed")}, "alphas": {}}
    brng = np.random.default_rng(SEED)
    for a in ALPHAS:
        entry = {}
        for pol in ("cp", "band"):
            entry[pol] = {k: agg(rec[a][pol], k) for k in ("escalation", "accuracy", "sensitivity", "specificity", "missed", "false_alarms")}
        # paired bootstrap over patients: accuracy difference (conformal policy minus reference)
        d = per_patient[a]["correct_cp"] / repeats - ref_correct / repeats
        boots = [d[brng.integers(0, n, n)].mean() for _ in range(2000)]
        entry["accuracy_diff_vs_reference"] = {"mean": float(d.mean()), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
        out["alphas"][str(a)] = entry
    return out


def main():
    out = run()
    Path(__file__).parent.joinpath("artifacts", "escalation.json").write_text(json.dumps(out, indent=2))
    ref = out["reference_full_model_everyone"]
    print(f"Reference (everyone gets full work-up): acc {ref['accuracy'][0]:.3f} sens {ref['sensitivity'][0]:.3f} spec {ref['specificity'][0]:.3f} missed {ref['missed'][0]:.1f}")
    print("alpha | escalate | acc | sens | spec | missed || band-control: acc sens | acc diff vs ref (95% CI)")
    for a, e in out["alphas"].items():
        c, b, d = e["cp"], e["band"], e["accuracy_diff_vs_reference"]
        print(f"{a:>5} | {c['escalation'][0]:.2f} | {c['accuracy'][0]:.3f} | {c['sensitivity'][0]:.3f} | {c['specificity'][0]:.3f} | {c['missed'][0]:.1f} || {b['accuracy'][0]:.3f} {b['sensitivity'][0]:.3f} | {d['mean']:+.3f} ({d['ci95'][0]:+.3f},{d['ci95'][1]:+.3f})")


if __name__ == "__main__":
    main()
