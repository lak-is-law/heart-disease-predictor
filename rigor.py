"""Rigour checks for the CardioSense model, in the spirit of TRIPOD and Riley's sample-size criteria.

    python rigor.py     # writes artifacts/rigor.json and prints a summary

1. Optimism-corrected performance (Harrell bootstrap): how much of the apparent AUC is overfitting.
2. Sample-size adequacy (Riley et al. 2020): is 303 patients enough for 22 model parameters?
3. Learning curve: would more patients help, and by how much?
4. Decision curve (Vickers): does acting on the model beat treating everyone or no one, and at which risk thresholds?
5. Conformal prediction: honest per-patient uncertainty, and how often the model should say "uncertain".
All on Cleveland (internal validation). None of this is external validation.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, train_test_split

import core

warnings.filterwarnings("ignore")
SEED = 7
FIRST = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg"]


def model():
    return core.build_models(SEED)["Logistic Regression"]


def fit_pred(Xtr, ytr, Xte, cols):
    from benchmark import models  # same preprocessing for any column set
    m = models(cols)["LR C=0.7 (shipped)"] if cols != core.FEATURES else model()
    m.fit(Xtr[cols], ytr)
    return m.predict_proba(Xte[cols])[:, 1], m


def optimism(X, y, cols, B=200):
    rng = np.random.default_rng(SEED)
    p_app, m0 = fit_pred(X, y, X, cols)
    app_auc = roc_auc_score(y, p_app)
    opt = []; slopes = []
    for _ in range(B):
        i = rng.choice(len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        Xb, yb = X.iloc[i].reset_index(drop=True), y[i]
        pb, mb = fit_pred(Xb, yb, Xb, cols)
        po = mb.predict_proba(X[cols])[:, 1]
        opt.append(roc_auc_score(yb, pb) - roc_auc_score(y, po))
        lg = np.log(np.clip(po, 1e-6, 1 - 1e-6) / (1 - np.clip(po, 1e-6, 1 - 1e-6)))
        from sklearn.linear_model import LogisticRegression
        slopes.append(LogisticRegression(C=1e6).fit(lg.reshape(-1, 1), y).coef_[0, 0])
    return {"apparent_auc": float(app_auc), "optimism": float(np.mean(opt)), "corrected_auc": float(app_auc - np.mean(opt)),
            "bootstrap_calibration_slope": float(np.mean(slopes))}


def riley(X, y, cols):
    """Minimum n for a logistic model: shrinkage >= 0.9 (criterion i), using apparent Cox-Snell R2."""
    p, m = fit_pred(X, y, X, cols)
    n = len(y); ll1 = np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    phi = y.mean(); ll0 = n * (phi * np.log(phi) + (1 - phi) * np.log(1 - phi))
    r2cs = 1 - np.exp(2 * (ll0 - ll1) / n)
    max_r2 = 1 - np.exp(2 * ll0 / n)
    r2_adj = r2cs * 0.9  # conservative, as recommended when only apparent R2 is available
    P = m.named_steps["prep"].transform(X[cols].head(1)).shape[1] if "prep" in m.named_steps else m.named_steps["p"].transform(X[cols].head(1)).shape[1]
    S = 0.9
    n_min = P / ((S - 1) * np.log(1 - r2_adj / S))
    return {"parameters": int(P), "cox_snell_r2_apparent": float(r2cs), "min_n_shrinkage_0.9": float(n_min), "actual_n": int(n), "events": int(y.sum()),
            "events_per_parameter": float(y.sum() / P)}


def learning_curve(X, y, cols, sizes=(60, 90, 120, 160, 200, 240), reps=30):
    rng = np.random.default_rng(SEED); out = {}
    for n in sizes:
        aucs = []
        for _ in range(reps):
            te = StratifiedKFold(5, shuffle=True, random_state=int(rng.integers(1e9)))
            tr_i, te_i = next(te.split(X, y))
            sub = rng.choice(tr_i, min(n, len(tr_i)), replace=False)
            if y[sub].min() == y[sub].max():
                continue
            p, _ = fit_pred(X.iloc[sub].reset_index(drop=True), y[sub], X.iloc[te_i], cols)
            aucs.append(roc_auc_score(y[te_i], p))
        out[int(n)] = [float(np.mean(aucs)), float(np.std(aucs) / np.sqrt(len(aucs)))]
    return out


def oof_probs(X, y, cols, repeats=10):
    acc = np.zeros((repeats, len(y)))
    for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=SEED).split(X, y)):
        acc[i // 5, te] = fit_pred(X.iloc[tr].reset_index(drop=True), y[tr], X.iloc[te], cols)[0]
    return acc.mean(axis=0)


def decision_curve(y, p, thresholds=(0.1, 0.2, 0.28, 0.3, 0.4, 0.5, 0.6, 0.7)):
    n = len(y); out = []
    for t in thresholds:
        pred = p >= t
        tp = ((pred) & (y == 1)).sum(); fp = ((pred) & (y == 0)).sum(); w = t / (1 - t)
        nb = tp / n - fp / n * w
        nb_all = y.mean() - (1 - y.mean()) * w
        out.append({"threshold": t, "net_benefit_model": float(nb), "net_benefit_treat_all": float(nb_all), "net_benefit_treat_none": 0.0})
    return out


def conformal(X, y, cols, alpha=0.1, reps=10):
    """Split-conformal classification sets. Coverage should be about 1 - alpha; 'uncertain' means the set holds both classes."""
    rng = np.random.default_rng(SEED); cov = []; unc = []; acc_single = []; n_single = []
    for r in range(reps):
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=int(rng.integers(1e9))).split(X, y):
            fit_i, cal_i = train_test_split(tr, test_size=0.3, stratify=y[tr], random_state=int(rng.integers(1e9)))
            Xf, yf = X.iloc[fit_i].reset_index(drop=True), y[fit_i]
            m = fit_pred(Xf, yf, X.iloc[cal_i], cols)[1]
            pc = m.predict_proba(X.iloc[cal_i][cols])[:, 1]
            scores = np.where(y[cal_i] == 1, 1 - pc, pc)
            k = int(np.ceil((len(scores) + 1) * (1 - alpha)))
            q = np.sort(scores)[min(k, len(scores)) - 1]
            pt = m.predict_proba(X.iloc[te][cols])[:, 1]
            in1 = (1 - pt) <= q; in0 = pt <= q
            truth_in = np.where(y[te] == 1, in1, in0)
            cov.append(truth_in.mean()); unc.append((in1 & in0).mean())
            single = in1 ^ in0
            if single.sum():
                acc_single.append((np.where(in1, 1, 0)[single] == y[te][single]).mean()); n_single.append(single.mean())
    return {"alpha": alpha, "coverage": float(np.mean(cov)), "uncertain_fraction": float(np.mean(unc)),
            "accuracy_when_confident": float(np.mean(acc_single)), "confident_fraction": float(np.mean(n_single))}


def main():
    X, y = core.normalize(core.load_raw()); yv = y.to_numpy()
    out = {"n": int(len(yv)), "events": int(yv.sum())}
    for name, cols in (("all_13", core.FEATURES), ("first_visit", FIRST)):
        p = oof_probs(X, yv, cols)
        out[name] = {"optimism": optimism(X, yv, cols), "sample_size": riley(X, yv, cols), "learning_curve": learning_curve(X, yv, cols),
                     "decision_curve": decision_curve(yv, p), "conformal": conformal(X, yv, cols)}
    Path(__file__).parent.joinpath("artifacts", "rigor.json").write_text(json.dumps(out, indent=2))
    for name in ("all_13", "first_visit"):
        r = out[name]; o = r["optimism"]; s = r["sample_size"]
        print(f"\n== {name}")
        print(f"optimism-corrected AUC {o['corrected_auc']:.3f} (apparent {o['apparent_auc']:.3f}, optimism {o['optimism']:.3f}); bootstrap calibration slope {o['bootstrap_calibration_slope']:.2f}")
        print(f"Riley minimum n {s['min_n_shrinkage_0.9']:.0f} vs actual {s['actual_n']}; events/parameter {s['events_per_parameter']:.1f}")
        print("learning curve:", {k: round(v[0], 3) for k, v in r["learning_curve"].items()})
        print("decision curve (threshold: model NB / treat-all NB):", {d['threshold']: (round(d['net_benefit_model'], 3), round(d['net_benefit_treat_all'], 3)) for d in r["decision_curve"]})
        c = r["conformal"]; print(f"conformal 90%: coverage {c['coverage']:.3f}, uncertain {c['uncertain_fraction']:.2f}, accuracy when confident {c['accuracy_when_confident']:.3f} ({c['confident_fraction']:.2f} of patients)")


if __name__ == "__main__":
    main()
