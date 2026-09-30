"""
FreightWise AI - Flask backend.

Loads the trained Extra Trees model and the historical dataset ONCE at start-up,
then serves JSON to the frontend. No prediction here is hard-coded: every forecast
comes from model.predict() on features built by utils/preprocessing.py.
"""
import logging
import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
import pandas as pd
from flask import Flask, jsonify, request

from utils.preprocessing import EXTERNAL_COLUMNS, HORIZON, TARGET, build_features, load_dataset

BASE = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE / "model" / "extra_trees_t14_model.pkl"))
DATA_PATH = Path(os.getenv("DATA_PATH", BASE / "data" / "master_training_dataset_clean.csv"))
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
STABLE_BAND_PCT = 1.0        # |change| below this is called "stable" (shown to the user)
DB_PATH = Path(os.getenv("DB_PATH", BASE / "data" / "forecast_history.db"))
DATA_SOURCE = "Backend dataset (master_training_dataset_clean.csv)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("freightwise")
app = Flask(__name__)


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, as_of_date TEXT NOT NULL,
        horizon TEXT NOT NULL, input_close REAL NOT NULL, predicted REAL NOT NULL, model TEXT NOT NULL)""")
    return con


# ----------------------------------------------------------------- helpers
def num(x):
    """JSON-safe float (NaN/inf -> None)."""
    try:
        x = float(x)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def pct(new, old):
    return None if old in (0, None) or new is None else (new / old - 1) * 100


def smape(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    return float(np.mean(2 * np.abs(a - p) / (np.abs(a) + np.abs(p))) * 100)


def trend_of(change_pct):
    if change_pct is None:
        return "unknown"
    return "stable" if abs(change_pct) < STABLE_BAND_PCT else ("up" if change_pct > 0 else "down")


def approx_target_date(date):
    """t+14 = 14 trading observations ahead; business days are an APPROXIMATION."""
    return str((pd.Timestamp(date) + pd.offsets.BDay(HORIZON)).date())


FEATURE_GROUPS = [
    ("Current-day market", ["bdry_open", "bdry_high", "bdry_low", "bdry_volume", "bdry_daily_range"]),
    ("Freight lags", ["bdry_lag", "close_lag_"]),
    ("Rolling statistics", ["roll_"]),
    ("Momentum", ["return_"]),
    ("Calendar", ["day_of_week", "month", "quarter", "year"]),
    ("Previous-day market", ["range_lag_1", "volume_lag_1", "high_lag_1", "low_lag_1"]),
    ("Lagged indicators", ["_lag1"]),
    ("Commodity / industry indicators", ["COL.", "IDY.", "CEM.", "ELY."]),
]


def group_of(name):
    for group, keys in FEATURE_GROUPS:
        if any(name.startswith(k) or (k.startswith("_") and name.endswith(k)) for k in keys):
            return group
    return "Other"


# ----------------------------------------------------------------- start-up (runs once)
def load_everything():
    S = {"model": None, "features": None, "df": None, "feats": None, "backtest": None, "error": None}
    try:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"model file not found at {MODEL_PATH}")
        if MODEL_PATH.stat().st_size < 1024:
            raise ValueError("model file is empty or corrupt")
        model = joblib.load(MODEL_PATH)
        if not hasattr(model, "feature_names_in_"):
            raise ValueError("model has no feature_names_in_; cannot verify feature order")
        S["model"], S["features"] = model, list(model.feature_names_in_)
        S["df"] = load_dataset(DATA_PATH)
        S["feats"] = build_features(S["df"])

        # Out-of-sample test period, rebuilt exactly as in the training notebook (70/15/15 chronological)
        d = S["df"].copy()
        d["target"] = d[TARGET].shift(-HORIZON)
        d = build_features(d.dropna(subset=["target"])).dropna().reset_index(drop=True)
        n = len(d)
        i_tr, i_va = int(n * 0.70), int(n * 0.85)
        test = d.iloc[i_va:].copy()
        test["predicted"] = model.predict(test[S["features"]])
        S["backtest"] = test[["date", TARGET, "target", "predicted"]].rename(
            columns={TARGET: "baseline_close", "target": "actual"})
        S["split"] = {"train": (d["date"].iloc[0], d["date"].iloc[i_tr - 1]),
                      "validation": (d["date"].iloc[i_tr], d["date"].iloc[i_va - 1]),
                      "test": (d["date"].iloc[i_va], d["date"].iloc[-1])}
        log.info("Loaded %s | %d features | %d rows", type(model).__name__, len(S["features"]), len(S["df"]))
    except Exception as e:                      # keep the server alive; report via /api/health
        S["error"] = f"{type(e).__name__}: {e}"
        log.error("Startup failure: %s", S["error"])
    return S


S = load_everything()


# ----------------------------------------------------------------- plumbing
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def fail(message, code=400):
    return jsonify(success=False, error=message), code


@app.errorhandler(404)
def _404(_):
    return fail("Endpoint not found.", 404)


@app.errorhandler(405)
def _405(_):
    return fail("Method not allowed.", 405)


@app.errorhandler(Exception)
def _500(e):
    log.exception("Unhandled error")           # traceback stays in the terminal, never sent to the browser
    return fail("Something went wrong on the server. Please try again.", 500)


def model_ready():
    return S["model"] is not None and S["error"] is None


def feature_row(as_of=None):
    """The model's input row for the latest date (or a chosen past date), in exact training order."""
    rows = S["feats"][["date"] + S["features"]].dropna()
    if as_of:
        rows = rows[rows["date"] == pd.Timestamp(as_of)]
        if rows.empty:
            return None
    return rows.tail(1)


def tree_spread(X):
    """Spread of the 300 individual trees. NOT a calibrated prediction interval."""
    per_tree = np.array([t.predict(X.to_numpy()) for t in S["model"].estimators_])[:, 0]
    return {"std": num(per_tree.std()), "p10": num(np.percentile(per_tree, 10)),
            "p90": num(np.percentile(per_tree, 90)),
            "note": "Spread across the model's individual trees; not a calibrated confidence interval."}


def model_meta():
    m = S["model"]
    return {"name": "Extra Trees", "type": type(m).__name__, "n_estimators": int(m.n_estimators),
            "n_features": len(S["features"]), "horizon": f"t+{HORIZON}", "target": TARGET,
            "runtime_sklearn": sklearn.__version__}


def downsample(df, max_points=800):
    if len(df) <= max_points:
        return df
    idx = np.unique(np.append(np.linspace(0, len(df) - 1, max_points).astype(int), len(df) - 1))
    return df.iloc[idx]


RANGES = {"7d": 7, "30d": 30, "90d": 90, "6m": 126, "1y": 252, "all": None}


# ----------------------------------------------------------------- routes
@app.get("/")
def index():
    return jsonify(app="FreightWise AI API", status="running", endpoints=sorted(
        r.rule for r in app.url_map.iter_rules() if r.rule.startswith("/api")))


@app.get("/api/health")
def health():
    df = S["df"]
    return jsonify(status="ok" if model_ready() else "degraded", model_loaded=S["model"] is not None,
                   data_loaded=df is not None, rows=None if df is None else len(df),
                   first_date=None if df is None else str(df["date"].min().date()),
                   last_date=None if df is None else str(df["date"].max().date()), detail=S["error"])


@app.get("/api/latest")
def latest():
    if S["df"] is None:
        return fail("Freight data is not available.", 503)
    df = S["df"]
    close = df[TARGET]
    last, prev = df.iloc[-1], df.iloc[-2]
    coal = "COL.HRD.IMP.TOT.DOC"
    coal_prev = df[coal][df[coal] != last[coal]].iloc[-1] if (df[coal] != last[coal]).any() else None
    out = {"success": True, "source": DATA_SOURCE, "date": str(last["date"].date()),
           "close": num(last[TARGET]), "previous_close": num(prev[TARGET]),
           "day_change_percent": num(pct(last[TARGET], prev[TARGET])),
           "avg_7d": num(close.tail(7).mean()), "avg_30d": num(close.tail(30).mean()),
           "coal_import": {"column": coal, "value": num(last[coal]), "previous_value": num(coal_prev),
                           "change_percent": num(pct(last[coal], coal_prev)), "unit": None,
                           "note": "Indicator updates about monthly and is carried forward daily; unit not documented in the dataset."}}
    if model_ready():
        row = feature_row()
        f = float(S["model"].predict(row[S["features"]])[0])
        out["forecast"] = {"value": f, "horizon": f"t+{HORIZON}", "as_of_date": str(row["date"].iloc[0].date()),
                           "change_percent": num(pct(f, last[TARGET])), "trend": trend_of(pct(f, last[TARGET]))}
    return jsonify(out)


@app.get("/api/history")
def history():
    if S["df"] is None:
        return fail("Freight data is not available.", 503)
    rng = request.args.get("range", "1y").lower()
    if rng not in RANGES:
        return fail(f"range must be one of {list(RANGES)}")
    d = S["df"][["date", TARGET]].copy()
    d["avg_7d"] = d[TARGET].rolling(7).mean()
    d["avg_30d"] = d[TARGET].rolling(30).mean()
    if RANGES[rng]:
        d = d.tail(RANGES[rng])
    d = downsample(d)
    return jsonify(success=True, range=rng, source=DATA_SOURCE, count=len(d),
                   dates=[str(x.date()) for x in d["date"]], close=[num(v) for v in d[TARGET]],
                   avg_7d=[num(v) for v in d["avg_7d"]], avg_30d=[num(v) for v in d["avg_30d"]])


@app.get("/api/market")
def market():
    if S["df"] is None:
        return fail("Freight data is not available.", 503)
    rng = request.args.get("range", "1y").lower()
    if rng not in RANGES:
        return fail(f"range must be one of {list(RANGES)}")
    d = S["df"]
    view = d.tail(RANGES[rng]) if RANGES[rng] else d
    view = downsample(view)
    indicators = []
    for col in EXTERNAL_COLUMNS:
        changed = d[col][d[col] != d[col].iloc[-1]]
        prev = changed.iloc[-1] if len(changed) else None
        indicators.append({"column": col, "latest": num(d[col].iloc[-1]), "previous": num(prev),
                           "change_percent": num(pct(d[col].iloc[-1], prev)), "unit": None,
                           "source": DATA_SOURCE, "dates": [str(x.date()) for x in view["date"]],
                           "series": [num(v) for v in view[col]]})
    return jsonify(success=True, range=rng, indicators=indicators,
                   update_note="These indicators change roughly monthly and are carried forward between updates.")


@app.get("/api/context-status")
def context_status():
    """Honest status of maritime-context sources. Nothing here is fabricated."""
    off = {"connected": False, "message": "Data source not connected"}
    return jsonify(success=True, port_activity=off, port_congestion=off, vessel_activity=off,
                   vessel_availability=off, weather={"connected": False, "message": "Live weather connection not configured"})


@app.get("/api/features")
def features():
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    row = feature_row()
    imp = dict(zip(S["features"], S["model"].feature_importances_))
    return jsonify(success=True, as_of_date=str(row["date"].iloc[0].date()), features=[
        {"name": f, "group": group_of(f), "value": num(row[f].iloc[0]), "importance": num(imp[f])}
        for f in S["features"]])


@app.get("/api/model-info")
def model_info():
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    imp = sorted(zip(S["features"], S["model"].feature_importances_), key=lambda x: -x[1])
    sp = S["split"]
    return jsonify(success=True, model=model_meta(),
                   training_period={k: [str(a.date()), str(b.date())] for k, (a, b) in sp.items()},
                   feature_importance=[{"feature": f, "importance": num(v), "group": group_of(f)} for f, v in imp],
                   excluded_from_final_model=["bdry_close", "bdry_roll7_mean", "bdry_roll30_mean"],
                   note="Importance = mean decrease in impurity (feature_importances_).")


@app.get("/api/metrics")
def metrics():
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    bt = S["backtest"]
    a, p, naive = bt["actual"].to_numpy(), bt["predicted"].to_numpy(), bt["baseline_close"].to_numpy()

    def block(pred):
        return {"mae": num(np.mean(np.abs(a - pred))), "rmse": num(np.sqrt(np.mean((a - pred) ** 2))),
                "smape_percent": num(smape(a, pred))}

    reported = {}
    for name in ("final_model_summary", "model_comparison_t14"):
        f = BASE / "data" / f"{name}.csv"
        if f.exists():
            reported[name] = pd.read_csv(f).to_dict(orient="records")
    return jsonify(success=True, test_period=[str(bt["date"].iloc[0].date()), str(bt["date"].iloc[-1].date())],
                   n_test=len(bt), model_recomputed=block(p), naive_persistence_recomputed=block(naive),
                   reported_in_notebook_files=reported,
                   note="Naive persistence = predict that the value 14 steps ahead equals today's close.")


@app.get("/api/backtest")
def backtest():
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    limit = min(int(request.args.get("limit", 300)), 1000)
    bt = S["backtest"].tail(limit)
    rows = [{"date": str(r.date.date()), "approx_target_date": approx_target_date(r.date),
             "input_freight": num(r.baseline_close), "actual": num(r.actual), "predicted": num(r.predicted), "error": num(r.predicted - r.actual),
             "percent_error": num(pct(r.predicted, r.actual)), "horizon": f"t+{HORIZON}", "model": "Extra Trees"}
            for r in bt.itertuples()]
    return jsonify(success=True, count=len(rows), period="out-of-sample test split", rows=rows)


@app.post("/api/forecast")
def forecast():
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    body = {}
    if request.get_data().strip():                       # a body is optional, but if sent it must be a JSON object
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return fail("Request body must be a JSON object.")
    as_of = body.get("as_of_date")
    if as_of is not None:
        try:
            pd.Timestamp(as_of)
        except (ValueError, TypeError):
            return fail("as_of_date must look like YYYY-MM-DD.")
    row = feature_row(as_of)
    if row is None:
        return fail("No model features exist for that date. Use a trading date within the dataset.")
    X = row[S["features"]]
    value = float(S["model"].predict(X)[0])
    date = row["date"].iloc[0]
    base = float(S["df"].loc[S["df"]["date"] == date, TARGET].iloc[0])
    ch = pct(value, base)
    saved = False
    if body.get("save") is True:                          # only the Forecast Center asks to save
        con = db()
        already = con.execute("SELECT 1 FROM forecasts WHERE as_of_date=? AND horizon=? AND ABS(predicted-?)<1e-9",
                              (str(date.date()), f"t+{HORIZON}", value)).fetchone()
        if not already:                                   # re-running the same forecast doesn't add duplicate rows
            with con:
                con.execute("INSERT INTO forecasts (created_at, as_of_date, horizon, input_close, predicted, model) VALUES (?,?,?,?,?,?)",
                            (datetime.now(timezone.utc).isoformat(timespec="seconds"), str(date.date()), f"t+{HORIZON}", base, value, "Extra Trees"))
        con.close()
        saved = True
    return jsonify(success=True, forecast={
        "value": value, "horizon": f"t+{HORIZON}", "horizon_note": f"{HORIZON} trading observations ahead",
        "as_of_date": str(date.date()), "approx_target_date": approx_target_date(date),
        "baseline_close": base, "absolute_change": value - base, "change_percent": num(ch),
        "trend": trend_of(ch), "stable_band_percent": STABLE_BAND_PCT, "tree_spread": tree_spread(X)},
        model=model_meta(), saved=saved)


@app.get("/api/forecast-history")
def forecast_history():
    """Forecasts saved from the Forecast Center. Actual = the real close 14 observations later, once it exists."""
    con = db()
    rows = con.execute("SELECT * FROM forecasts ORDER BY id DESC LIMIT 500").fetchall()
    con.close()
    dates = S["df"]["date"].dt.strftime("%Y-%m-%d").tolist() if S["df"] is not None else []
    pos, closes = {d: i for i, d in enumerate(dates)}, S["df"][TARGET].tolist() if dates else []
    out = []
    for r in rows:
        i = pos.get(r["as_of_date"])
        actual = closes[i + HORIZON] if i is not None and i + HORIZON < len(closes) else None
        out.append({"id": r["id"], "created_at": r["created_at"], "as_of_date": r["as_of_date"], "horizon": r["horizon"],
                    "input_freight": r["input_close"], "predicted": r["predicted"], "model": r["model"], "actual": num(actual),
                    "difference": None if actual is None else r["predicted"] - actual,
                    "percent_error": None if actual is None else num(pct(r["predicted"], actual)),
                    "status": "Pending" if actual is None else "Actual available"})
    return jsonify(success=True, count=len(out), rows=out)


@app.post("/api/scenario")
def scenario():
    """What-if: override model inputs on the latest row. Derived features are NOT recomputed."""
    if not model_ready():
        return fail("Forecast model is not available.", 503)
    overrides = (request.get_json(silent=True) or {}).get("overrides")
    if not isinstance(overrides, dict) or not overrides or len(overrides) > 20:
        return fail("Provide 1-20 feature overrides.")
    unknown = [k for k in overrides if k not in S["features"]]
    if unknown:
        return fail(f"Unknown model feature(s): {unknown}")
    clean = {}
    for k, v in overrides.items():
        v = num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        if v is None:
            return fail(f"Value for '{k}' must be a finite number.")
        clean[k] = v
    row = feature_row()
    X_base = row[S["features"]].copy()
    X_new = X_base.copy()
    for k, v in clean.items():
        X_new[k] = v
    base, new = float(S["model"].predict(X_base)[0]), float(S["model"].predict(X_new)[0])
    return jsonify(success=True, label="Scenario analysis - not a guaranteed outcome", as_of_date=str(row["date"].iloc[0].date()),
                   base_prediction=base, scenario_prediction=new, difference=new - base,
                   difference_percent=num(pct(new, base)), overrides=clean,
                   caveat="Only the listed inputs were changed; related lag/rolling features were left as-is.")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=False)
