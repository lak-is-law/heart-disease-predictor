"""Compare model families on the same repeated cross-validation folds (Cleveland, internal validation).

    python benchmark.py [--repeats 6]

Prints out-of-fold AUC and Brier score for each model on the full 13-input set and on the first-visit set.
Result recorded in docs/MODEL_REPORT.md: nothing beats the shipped logistic regression by more than noise.
"""
from __future__ import annotations

import argparse
import warnings

import numpy as np
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler
from sklearn.svm import SVC

import core

warnings.filterwarnings("ignore")
SETS = {"all_13": core.FEATURES, "first_visit": ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg"]}


def pre(cols, spline=False):
    num = [c for c in cols if c not in core.CATEGORICAL]; cat = [c for c in cols if c in core.CATEGORICAL]
    n = [("imp", SimpleImputer(strategy="median"))] + ([("sp", SplineTransformer(n_knots=4, degree=2))] if spline else []) + [("sc", StandardScaler())]
    return ColumnTransformer([("num", Pipeline(n), num),
                              ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat)])


def models(cols):
    P = lambda c, s=False: Pipeline([("p", pre(cols, s)), ("c", c)])
    return {
        "LR C=0.7 (shipped)": P(LogisticRegression(max_iter=3000, C=0.7)),
        "LR tuned C": P(LogisticRegressionCV(Cs=np.logspace(-2.5, 1, 12), cv=5, scoring="neg_log_loss", max_iter=3000)),
        "LR L1": P(LogisticRegression(penalty="l1", solver="liblinear", C=0.3)),
        "LR splines": P(LogisticRegression(max_iter=3000, C=0.1), True),
        "Random forest": P(RandomForestClassifier(300, min_samples_leaf=3, random_state=1, n_jobs=2)),
        "Boosting (shallow)": P(HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=150, l2_regularization=1.0, random_state=1)),
        "SVM (rbf)": P(SVC(C=0.5, probability=True, random_state=1)),
    }


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=6); a = ap.parse_args()
    X, y = core.normalize(core.load_raw()); yv = y.to_numpy()
    for sname, cols in SETS.items():
        ms = models(cols); oof = {k: np.zeros((a.repeats, len(yv))) for k in ms}
        for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=a.repeats, random_state=11).split(X, yv)):
            for k, m in ms.items():
                oof[k][i // 5, te] = clone(m).fit(X.iloc[tr][cols], yv[tr]).predict_proba(X.iloc[te][cols])[:, 1]
        base = np.mean([roc_auc_score(yv, q) for q in oof["LR C=0.7 (shipped)"]])
        print(f"\n{sname}")
        for k, p in oof.items():
            auc = np.mean([roc_auc_score(yv, q) for q in p]); br = np.mean([brier_score_loss(yv, q) for q in p])
            print(f"  {k:22s} AUC {auc:.4f}  Brier {br:.4f}  vs shipped {auc - base:+.4f}")


if __name__ == "__main__":
    main()
