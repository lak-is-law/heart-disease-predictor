"""Shared logic for the heart disease predictor: data loading, preprocessing,
model construction, prediction and per-patient explanation.

Works with either of the two sources you listed:
  * UCI "processed.cleveland.data" (14 columns, no header, '?' = missing)
  * Kaggle "heart_disease_uci.csv" (redwankarimsony; text-coded, 920 rows, several hospitals)
Everything is normalised to the original UCI numeric coding.
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
import sys
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
UCI_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "heart-disease/processed.cleveland.data"
)
RAW_COLUMNS = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal", "num",
]
FEATURES = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal",
]
CATEGORICAL = ["cp", "restecg", "slope", "thal"]
NUMERIC = [f for f in FEATURES if f not in CATEGORICAL]

FEATURE_LABELS = {
    "age": "Age",
    "sex": "Sex",
    "cp": "Chest pain type",
    "trestbps": "Resting blood pressure",
    "chol": "Cholesterol",
    "fbs": "Fasting sugar > 120",
    "restecg": "Resting ECG",
    "thalach": "Max heart rate",
    "exang": "Exercise angina",
    "oldpeak": "ST depression",
    "slope": "ST slope",
    "ca": "Major vessels (0-3)",
    "thal": "Thalassemia",
}

SEX_OPTIONS = {1: "Male", 0: "Female"}
YESNO_OPTIONS = {0: "No", 1: "Yes"}
CP_OPTIONS = {1: "Typical angina", 2: "Atypical angina", 3: "Non-anginal pain", 4: "Asymptomatic"}
ECG_OPTIONS = {0: "Normal", 1: "ST-T abnormality", 2: "LV hypertrophy"}
SLOPE_OPTIONS = {1: "Upsloping", 2: "Flat", 3: "Downsloping"}
THAL_OPTIONS = {3: "Normal", 6: "Fixed defect", 7: "Reversible defect"}

# Text -> UCI numeric code (for the Kaggle csv)
_TEXT_MAPS = {
    "sex": {"male": 1, "female": 0},
    "fbs": {"true": 1, "false": 0},
    "exang": {"true": 1, "false": 0},
    "cp": {"typical angina": 1, "atypical angina": 2, "non-anginal": 3, "asymptomatic": 4},
    "restecg": {"normal": 0, "st-t abnormality": 1, "lv hypertrophy": 2},
    "slope": {"upsloping": 1, "flat": 2, "downsloping": 3},
    "thal": {"normal": 3, "fixed defect": 6, "reversable defect": 7, "reversible defect": 7},
}


# --------------------------------------------------------------------------- data
def _read_any(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, na_values=["?", ""])
    cols = {str(c).strip().lower() for c in df.columns}
    if not {"age", "sex"} <= cols:  # headerless UCI file
        df = pd.read_csv(path, header=None, names=RAW_COLUMNS, na_values=["?", ""])
    return df


def _download_uci() -> pd.DataFrame:
    raw = urllib.request.urlopen(UCI_URL, timeout=30).read().decode("utf-8")
    return pd.read_csv(io.StringIO(raw), header=None, names=RAW_COLUMNS, na_values="?")


def load_raw(path: str | None = None) -> pd.DataFrame:
    if path:
        return _read_any(Path(path))
    for name in ("heart_disease_uci.csv", "heart.csv", "processed.cleveland.data"):
        p = ROOT / "data" / name
        if p.exists():
            return _read_any(p)
    try:
        return _download_uci()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "Could not find or download the dataset.\n"
            "Download it from Kaggle (redwankarimsony/heart-disease-data) or UCI and put the file\n"
            f"in {ROOT / 'data'}/, or pass --data path/to/file.csv\n({exc})"
        )


def normalize(df: pd.DataFrame, cleveland_only: bool = False) -> tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"thalch": "thalach"})
    if cleveland_only and "dataset" in df.columns:
        df = df[df["dataset"].astype(str).str.lower() == "cleveland"]

    for col, mapping in _TEXT_MAPS.items():
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].map(
                lambda v, m=mapping: m.get(str(v).strip().lower(), np.nan) if pd.notna(v) else np.nan
            )

    missing = [c for c in FEATURES + ["num"] if c not in df.columns]
    if missing:
        raise SystemExit(f"Dataset is missing expected columns: {missing}")

    X = df[FEATURES].apply(pd.to_numeric, errors="coerce").astype(float)
    y = (pd.to_numeric(df["num"], errors="coerce") > 0).astype(int)
    keep = pd.to_numeric(df["num"], errors="coerce").notna()
    return X[keep].reset_index(drop=True), y[keep].reset_index(drop=True)


# ------------------------------------------------------------------------- models
def make_preprocessor() -> ColumnTransformer:
    num = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    cat = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("oh", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([("num", num, NUMERIC), ("cat", cat, CATEGORICAL)])


def build_models(seed: int = 42) -> dict[str, Pipeline]:
    clfs = {
        "Logistic Regression": LogisticRegression(max_iter=3000, C=0.7),
        "Random Forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, random_state=seed, n_jobs=-1
        ),
    }
    try:
        from xgboost import XGBClassifier

        clfs["XGBoost"] = XGBClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, eval_metric="logloss", random_state=seed,
        )
    except Exception:  # xgboost not installed -> sklearn's equivalent
        clfs["Gradient Boosting"] = HistGradientBoostingClassifier(
            learning_rate=0.05, max_depth=3, max_iter=250, random_state=seed
        )
    return {n: Pipeline([("prep", make_preprocessor()), ("clf", c)]) for n, c in clfs.items()}


# --------------------------------------------------------------------- inference
def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)[FEATURES].astype(float)


def predict_proba(pipe: Pipeline, patient: dict) -> float:
    return float(pipe.predict_proba(_frame([patient]))[0, 1])


def explain(pipe: Pipeline, patient: dict, baseline: dict) -> tuple[float, list[tuple[str, float]]]:
    """Occlusion explanation: how much does risk change if each feature is set to the
    typical (median / most common) training value? Positive = this value raises risk."""
    rows = [dict(patient)]
    for f in FEATURES:
        alt = dict(patient)
        alt[f] = baseline[f]
        rows.append(alt)
    probs = pipe.predict_proba(_frame(rows))[:, 1]
    p = float(probs[0])
    deltas = [(f, p - float(probs[i + 1])) for i, f in enumerate(FEATURES)]
    deltas.sort(key=lambda t: abs(t[1]), reverse=True)
    return p, deltas


def risk_band(p: float) -> tuple[str, str]:
    if p < 0.33:
        return "Low risk", "Few patterns associated with heart disease show up in this profile."
    if p < 0.66:
        return "Moderate risk", "Some indicators point towards heart disease; worth a closer look."
    return "High risk", "Several strong indicators line up with patients who had heart disease."
