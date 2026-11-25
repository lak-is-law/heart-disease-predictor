"""Regenerate every figure in docs/figures and portal/img/research from the experiments.

    python make_figures.py      # needs artifacts/rigor.json and artifacts/escalation.json (run rigor.py and selective_escalation.py first)

Figures are transparent SVGs in mid-tone colours so they read on both the light and dark site themes.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

import core
import rigor

ROOT = Path(__file__).parent
TEAL, ORANGE, GREY = "#14A3BF", "#E08A2E", "#8A99A8"
plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif", "font.size": 10, "text.color": GREY, "axes.labelcolor": GREY,
                     "xtick.color": GREY, "ytick.color": GREY, "axes.edgecolor": GREY, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.facecolor": "none", "figure.facecolor": "none", "savefig.transparent": True, "legend.frameon": False})


def save(fig, name):
    p = ROOT / "docs" / "figures" / name
    fig.savefig(p, format="svg", bbox_inches="tight"); plt.close(fig)
    t = p.read_text(); t = re.sub(r"<!DOCTYPE[^>]*>\s*", "", t); p.write_text(t)  # DTD-free so hosts accept the SVG
    shutil.copy(p, ROOT / "portal" / "img" / "research" / name)


def main():
    X, y = core.normalize(core.load_raw()); yv = y.to_numpy()
    rj = json.loads((ROOT / "artifacts" / "rigor.json").read_text()); ej = json.loads((ROOT / "artifacts" / "escalation.json").read_text())
    sets = {"13 inputs": core.FEATURES, "First-visit (7 inputs)": rigor.FIRST}
    P = {k: rigor.oof_probs(X, yv, c) for k, c in sets.items()}
    cols = {"13 inputs": TEAL, "First-visit (7 inputs)": ORANGE}

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    for k, p in P.items():
        f, t, _ = roc_curve(yv, p); ax.plot(f, t, color=cols[k], lw=2, label=f"{k}, AUC {roc_auc_score(yv, p):.2f}")
    ax.plot([0, 1], [0, 1], color=GREY, lw=1, ls="--"); ax.set_xlabel("1 - specificity"); ax.set_ylabel("Sensitivity"); ax.legend(loc="lower right")
    ax.set_title("Out-of-fold ROC (Cleveland, n=303)", loc="left"); save(fig, "roc.svg")

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    for k, p in P.items():
        q = np.quantile(p, np.linspace(0, 1, 9)); idx = np.clip(np.digitize(p, q[1:-1]), 0, 7)
        mx = [p[idx == i].mean() for i in range(8)]; my = [yv[idx == i].mean() for i in range(8)]
        ax.plot(mx, my, "o-", color=cols[k], lw=1.6, label=k)
    ax.plot([0, 1], [0, 1], color=GREY, lw=1, ls="--"); ax.set_xlabel("Predicted probability"); ax.set_ylabel("Observed share with disease"); ax.legend(loc="upper left")
    ax.set_title("Calibration (octiles of risk)", loc="left"); save(fig, "calibration.svg")

    fig, ax = plt.subplots(figsize=(4.6, 4.2)); th = np.linspace(0.05, 0.8, 76)
    prev = yv.mean(); ax.plot(th, prev - (1 - prev) * th / (1 - th), color=GREY, lw=1.4, ls=":", label="Treat everyone"); ax.axhline(0, color=GREY, lw=1, label="Treat no one")
    for k, p in P.items():
        nb = [((p >= t) & (yv == 1)).mean() - ((p >= t) & (yv == 0)).mean() * t / (1 - t) for t in th]; ax.plot(th, nb, color=cols[k], lw=2, label=k)
    ax.set_ylim(-0.1, 0.5); ax.set_xlabel("Risk threshold for acting"); ax.set_ylabel("Net benefit"); ax.legend(loc="upper right")
    ax.set_title("Decision curve", loc="left"); save(fig, "decision_curve.svg")

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    for k, key in (("13 inputs", "all_13"), ("First-visit (7 inputs)", "first_visit")):
        lc = rj[key]["learning_curve"]; ns = [int(n) for n in lc]; m = [lc[str(n)][0] for n in ns]; se = [lc[str(n)][1] for n in ns]
        ax.errorbar(ns, m, yerr=np.array(se) * 1.96, color=cols[k], marker="o", lw=1.8, capsize=3, label=k)
    ax.set_xlabel("Training patients"); ax.set_ylabel("Held-out AUC"); ax.legend(loc="lower right"); ax.set_title("Learning curve (95% band over resamples)", loc="left"); save(fig, "learning_curve.svg")

    fig, ax = plt.subplots(figsize=(4.6, 4.2)); A = ej["alphas"]; ref = ej["reference_full_model_everyone"]
    pts = sorted(((1 - A[a]["cp"]["escalation"][0], A[a]["cp"]["accuracy"][0], A[a]["cp"]["accuracy"][1], a) for a in A))
    ax.errorbar([p[0] for p in pts], [p[1] for p in pts], yerr=[p[2] for p in pts], color=TEAL, marker="o", lw=1.8, capsize=3, label="Conformal triage")
    ax.axhline(ref["accuracy"][0], color=GREY, ls="--", lw=1.2, label="Everyone gets the full work-up")
    for p in pts: ax.annotate(f"alpha {p[3]}", (p[0], p[1]), textcoords="offset points", xytext=(4, -12), fontsize=8)
    ax.set_xlabel("Share of patients who skip the extra tests"); ax.set_ylabel("Accuracy"); ax.legend(loc="lower left"); ax.set_title("Selective escalation trade-off", loc="left"); save(fig, "escalation.svg")
    print("wrote", sorted(p.name for p in (ROOT / "docs" / "figures").glob("*.svg")))


if __name__ == "__main__":
    main()
