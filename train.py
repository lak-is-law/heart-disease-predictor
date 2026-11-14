"""Train Logistic Regression, Random Forest and XGBoost on the UCI Heart Disease data.

    python train.py                       # auto-loads data/ file, else downloads from UCI (Cleveland)
    python train.py --data data/heart_disease_uci.csv
    python train.py --data data/heart_disease_uci.csv --cleveland-only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from core import CATEGORICAL, FEATURES, NUMERIC, ROOT, build_models, load_raw, normalize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="path to csv / .data file (optional)")
    ap.add_argument("--cleveland-only", action="store_true", help="use only the Cleveland subset")
    ap.add_argument("--out", default=str(ROOT / "artifacts"), help="output folder")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    X, y = normalize(load_raw(args.data), cleveland_only=args.cleveland_only)
    print(f"Loaded {len(X)} patients | disease prevalence {y.mean():.1%}")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=args.seed
    )
    cv = StratifiedKFold(5, shuffle=True, random_state=args.seed)

    models = build_models(args.seed)
    metrics, roc, importance, cv_auc = {}, {}, {}, {}
    for name, pipe in models.items():
        cv_auc[name] = float(cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="roc_auc").mean())
        pipe.fit(X_tr, y_tr)
        proba = pipe.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics[name] = {
            "accuracy": accuracy_score(y_te, pred),
            "precision": precision_score(y_te, pred, zero_division=0),
            "recall": recall_score(y_te, pred, zero_division=0),
            "f1": f1_score(y_te, pred, zero_division=0),
            "roc_auc": roc_auc_score(y_te, proba),
            "cv_roc_auc": cv_auc[name],
            "confusion": confusion_matrix(y_te, pred).tolist(),
        }
        metrics[name] = {k: (float(v) if not isinstance(v, list) else v) for k, v in metrics[name].items()}
        fpr, tpr, _ = roc_curve(y_te, proba)
        roc[name] = {"fpr": np.round(fpr, 4).tolist(), "tpr": np.round(tpr, 4).tolist()}
        pi = permutation_importance(
            pipe, X_te, y_te, scoring="roc_auc", n_repeats=20, random_state=args.seed
        )
        importance[name] = {f: float(v) for f, v in zip(FEATURES, pi.importances_mean)}

    best = max(cv_auc, key=cv_auc.get)  # chosen on CV (train only), not on the test set
    baseline = {f: float(X_tr[f].median()) for f in NUMERIC}
    baseline.update({f: float(X_tr[f].mode().iloc[0]) for f in CATEGORICAL})

    bundle = {
        "models": models,
        "best": best,
        "metrics": metrics,
        "roc": roc,
        "importance": importance,
        "baseline": baseline,
        "meta": {
            "n_total": int(len(X)), "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
            "prevalence": float(y.mean()), "features": FEATURES,
        },
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out / "heart_model.joblib")
    (out / "metrics.json").write_text(json.dumps(
        {"best": best, "metrics": metrics, "meta": bundle["meta"]}, indent=2))

    # Auto-export Logistic Regression weights to portal/model_weights.json
    lr_pipe = models["Logistic Regression"]
    prep = lr_pipe.named_steps["prep"]
    scaler = prep.named_transformers_["num"].named_steps["sc"]
    ohe = prep.named_transformers_["cat"].named_steps["oh"]
    clf = lr_pipe.named_steps["clf"]

    portal_weights = {
        "features": FEATURES,
        "baseline": baseline,
        "numeric": NUMERIC,
        "categorical": CATEGORICAL,
        "intercept": float(clf.intercept_[0]),
        "coef": [float(c) for c in clf.coef_[0]],
        "num_mean": [float(m) for m in scaler.mean_],
        "num_scale": [float(s) for s in scaler.scale_],
        "cat_categories": [[float(c) for c in cat_arr] for cat_arr in ohe.categories_],
        "metrics": metrics
    }
    portal_weights_path = ROOT / "portal" / "model_weights.json"
    if portal_weights_path.parent.exists():
        portal_weights_path.write_text(json.dumps(portal_weights, indent=2))

    print(f"\n{'Model':<22}{'CV AUC':>8}{'Acc':>8}{'Prec':>8}{'Recall':>8}{'F1':>8}{'AUC':>8}")
    for n, m in metrics.items():
        star = " *" if n == best else ""
        print(f"{n:<22}{m['cv_roc_auc']:>8.3f}{m['accuracy']:>8.3f}{m['precision']:>8.3f}"
              f"{m['recall']:>8.3f}{m['f1']:>8.3f}{m['roc_auc']:>8.3f}{star}")
    print(f"\nBest by cross-validation: {best}\nSaved -> {out / 'heart_model.joblib'}")


if __name__ == "__main__":
    main()
