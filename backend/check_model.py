"""
Run this FIRST, from the backend folder:   python check_model.py
It checks that your model file loads, that its features match the dataset,
and prints the forecast for the latest date. Nothing is changed or saved.
"""
import sys
import warnings
from pathlib import Path

import joblib
import sklearn

from utils.preprocessing import latest_feature_row, load_dataset

BASE = Path(__file__).resolve().parent
MODEL = BASE / "model" / "extra_trees_t14_model.pkl"
DATA = BASE / "data" / "master_training_dataset_clean.csv"

print("Python:", sys.version.split()[0], "| scikit-learn:", sklearn.__version__)
for p in (MODEL, DATA):
    if not p.exists():
        sys.exit(f"MISSING FILE: {p}\nPut the file in that exact folder and run again.")
    print(f"{p.name}: {p.stat().st_size / 1_048_576:.2f} MB")
if MODEL.stat().st_size < 1024:
    sys.exit("The model file is empty. Download it again from Colab.")

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    model = joblib.load(MODEL)
for w in caught:
    print("WARNING:", str(w.message).split(". This might")[0])
if caught:
    print("-> Your scikit-learn version differs from the one used for training. Install the pinned version:")
    print("   pip install scikit-learn==1.6.1")

print("\nModel type:", type(model).__name__, "| trees:", model.n_estimators)
print("Features the model expects:", model.n_features_in_)
df = load_dataset(DATA)
print(f"Dataset: {len(df)} rows, {df['date'].min().date()} to {df['date'].max().date()}")

row = latest_feature_row(df, model.feature_names_in_)
pred = float(model.predict(row[list(model.feature_names_in_)])[0])
close = float(df["bdry_close"].iloc[-1])
print(f"\nLatest date: {row['date'].iloc[0].date()} | latest BDRY close: {close:.4f}")
print(f"t+14 forecast: {pred:.4f}  ({(pred / close - 1) * 100:+.2f}% vs latest close)")
print("\nOK - the model, dataset and feature builder work together.")
