"""
Feature engineering for FreightWise AI.

This mirrors the training notebook (freightwise.py, sections 5.1-5.3) exactly.
The model was trained on 49 features (see MODEL_FEATURES). Their names and order
are read from the loaded model itself (model.feature_names_in_) so the model stays
the single source of truth.
"""
import pandas as pd

TARGET = "bdry_close"
HORIZON = 14

EXTERNAL_COLUMNS = [
    "COL.HRD.IMP.COK.DOC", "COL.HRD.IMP.STM.DOC", "COL.HRD.IMP.TOT.DOC",
    "COL.HRD.IMP.CIS", "COL.HRD.PRD.GrandTotal.MCL", "IDY.PRD.OEA.COL",
    "IDY.PRD.OEA.STL", "CEM.PRD", "ELY.DEM.POS.TOT.India",
]


def load_dataset(csv_path):
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def build_features(df):
    """Return a copy of df with every engineered column the model was trained on."""
    d = df.copy()
    c = d[TARGET]
    for lag in [1, 2, 3, 5, 7, 14, 21, 30]:
        d[f"close_lag_{lag}"] = c.shift(lag)
    # rolling stats are shifted by 1 so today's close is never used (no leakage)
    d["roll_7_mean"] = c.shift(1).rolling(7).mean()
    d["roll_14_mean"] = c.shift(1).rolling(14).mean()
    d["roll_30_mean"] = c.shift(1).rolling(30).mean()
    d["roll_7_std"] = c.shift(1).rolling(7).std()
    d["roll_30_std"] = c.shift(1).rolling(30).std()
    d["return_1"] = c.shift(1) / c.shift(2) - 1
    d["return_7"] = c.shift(1) / c.shift(8) - 1
    d["day_of_week"] = d["date"].dt.dayofweek
    d["month"] = d["date"].dt.month
    d["quarter"] = d["date"].dt.quarter
    d["year"] = d["date"].dt.year
    d["range_lag_1"] = d["bdry_daily_range"].shift(1)
    d["volume_lag_1"] = d["bdry_volume"].shift(1)
    d["high_lag_1"] = d["bdry_high"].shift(1)
    d["low_lag_1"] = d["bdry_low"].shift(1)
    for col in EXTERNAL_COLUMNS:
        d[col + "_lag1"] = d[col].shift(1)
    return d


def latest_feature_row(df, model_features):
    """Feature row for the most recent date, in the model's exact column order."""
    feats = build_features(df)
    missing = [f for f in model_features if f not in feats.columns]
    if missing:
        raise ValueError(f"Missing model features: {missing}")
    row = feats[["date"] + list(model_features)].dropna().tail(1)
    if row.empty:
        raise ValueError("Not enough history to build features.")
    return row