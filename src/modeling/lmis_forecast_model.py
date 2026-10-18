#!/usr/bin/env python3
"""
LMIS Demand-Supply Forecasting Model (SIH26246 / MSDE)
======================================================
Trains a global, direct multi-horizon LightGBM forecaster on the 2011-2026 district x sector monthly panel
(`lmis_district_monthly_2011_2026.csv`) and turns the forecasts into a ranked demand-supply gap table with
early-warning flags.

Inputs  : data/raw/lmis_district_monthly_2011_2026.csv  (the ONLY dataset used; nothing under Archived/ is read)
Outputs : outputs/quarantine/ and models/quarantine/  (metrics, forecasts, gap ranking, saved models)
Status  : QUARANTINED. This prototype scores the locked 2025-2026 test period and bypasses load_panel; do not run it or use its results.
          The Phase 6-8 pipeline replaces it.

Targets (each forecast 1..12 months ahead, per district x sector):
    Total_Employed_Workers      -> employment / demand outlook
    Active_Job_Vacancies        -> demand signal
    eShram_Registered_Seekers   -> supply proxy (the dataset has no training-seat capacity column)

Pipeline
    A. early-stopping fold   train targets <= 2023-12, validate 2024-01..2024-12
    B. honest test fold      refit on targets <= 2024-12, test origins 2024-12..2026-11 (targets <= 2026-12)
    C. final model           refit on everything, forecast 2027-01..2027-12 from origin 2026-12
Run:  python src/modeling/lmis_forecast_model.py
"""
import json
import os
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "raw" / "lmis_district_monthly_2011_2026.csv"
OUT = ROOT / "outputs" / "quarantine" / "provisional_prototype"
MODEL_DIR = ROOT / "models" / "quarantine" / "provisional_prototype"

HORIZONS = list(range(1, 13))
TARGETS = {
    "employed": "Total_Employed_Workers",
    "vacancies": "Active_Job_Vacancies",
    "seekers": "eShram_Registered_Seekers",
}
START = pd.Timestamp("2011-01-01")
IDX_VAL_ORIGIN = 155      # 2023-12: last origin whose targets may be used in fold A training
IDX_TEST_ORIGIN = 167     # 2024-12: last month of fold-B training targets / first test origin
# e-Shram launched Aug-2021 and its uptake ramps over 2021-22 (a registry roll-out, not a labour-market move).
# Training windows touching the ramp are dropped for the seekers target only.
ESHRAM_RAMP = (119, 132)  # 2020-12 .. 2022-01
COVID_WINDOW = (110, 133)  # 2020-03 .. 2022-02; exogenous shock the model cannot anticipate
RESIDUAL_ON_DRIFT = os.environ.get("LMIS_RESID", "1") == "1"   # model the error of the seasonal+drift baseline instead of the raw log-change
EXCLUDE_COVID_WINDOWS = os.environ.get("LMIS_EXCL_COVID", "1") == "1"
# Early-warning thresholds on forecast coverage = openings per registered seeker. Placeholders to be recalibrated
# with real seat-allocation / placement data.
COVERAGE_ACUTE_SHORTAGE = 1.00
COVERAGE_OVERSUPPLY_WATCH = 0.20
COVERAGE_SATURATION = 0.10
TREND_ALERT = 0.08        # +/-8% forecast change in coverage vs. trailing 12 months

LGB_PARAMS = dict(
    objective="regression", learning_rate=0.05, num_leaves=63, min_child_samples=200,
    feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
    n_estimators=3000, verbose=-1, n_jobs=-1, random_state=42,
)


# ----------------------------------------------------------------------------------------------------------------
# Data -> arrays
# ----------------------------------------------------------------------------------------------------------------
def load_panel():
    assert "Archived" not in str(DATA), "Archived data must not be used"
    df = pd.read_csv(DATA, dtype={"State_LGD_Code": str, "District_LGD_Code": str})
    df = df.sort_values(["District_Name", "Sector_Name", "Timestamp"]).reset_index(drop=True)
    keys = ["District_Name", "Sector_Name"]

    def wide(col):
        return df.pivot(index=keys, columns="Timestamp", values=col)

    ref = wide("Total_Employed_Workers")
    assert not ref.isna().any().any(), "panel must be complete"
    meta = ref.index.to_frame(index=False)
    meta = meta.merge(df[["District_Name", "State_Name"]].drop_duplicates(), on="District_Name")
    cols = list(ref.columns)
    arrays = {c: wide(c).loc[ref.index].to_numpy(float) for c in df.columns
              if df[c].dtype != object and c not in ("Year", "Month", "NCO_Code")}
    return df, meta, cols, arrays


def lagdiff(a, k):
    out = np.full_like(a, np.nan)
    out[:, k:] = a[:, k:] - a[:, :-k]
    return out


def roll(a, k, fn):
    return getattr(pd.DataFrame(a.T).rolling(k), fn)().to_numpy().T


def base_features(ly, arrays, meta):
    """(n_series x n_months) feature planes using only information up to each origin month."""
    E, V, S = (np.log(arrays[c]) for c in TARGETS.values())
    f = {
        "d1": lagdiff(ly, 1), "d3": lagdiff(ly, 3), "d6": lagdiff(ly, 6), "d12": lagdiff(ly, 12),
        "rel_mean12": ly - roll(ly, 12, "mean"),
        "vol12": roll(lagdiff(ly, 1), 12, "std"),
        "level": ly,
        "log_wage": np.log(arrays["Avg_Monthly_Wage_INR"]),
        "wage_d12": lagdiff(np.log(arrays["Avg_Monthly_Wage_INR"]), 12),
        "unemp": arrays["Unemployment_Rate_Pct"],
        "vac_rate": V - E, "seek_rate": S - E, "vac_rate_d12": lagdiff(V - E, 12),
        "female_pct": arrays["Female_Share_Pct"], "grad_pct": arrays["Edu_Graduate_and_Above_Pct"],
        "youth_pct": arrays["Age_15_24_Pct"], "log_pop": np.log(arrays["District_Total_Population_Est"]),
    }
    # sector-wide momentum (captures macro shocks such as COVID); sums over all districts at each month
    sec = meta["Sector_Name"].to_numpy()
    for name in ("d1", "d3", "d12"):
        k = {"d1": 1, "d3": 3, "d12": 12}[name]
        plane = np.zeros_like(ly)
        for s in np.unique(sec):
            tot = np.log(np.exp(ly[sec == s]).sum(axis=0))
            d = np.full_like(tot, np.nan)
            d[k:] = tot[k:] - tot[:-k]
            plane[sec == s] = d
        f[f"sector_{name}"] = plane
    return f


def build_rows(name, arrays, meta, origins_by_h=None, T=192):
    """Stack one row per (series, origin, horizon). Target = log(y[t+h]) - log(y[t])."""
    ly = np.log(arrays[TARGETS[name]])
    base = base_features(ly, arrays, meta)
    n = ly.shape[0]
    frames = []
    for h in HORIZONS:
        t = np.arange(12, T - h) if origins_by_h is None else np.asarray(origins_by_h[h])
        if len(t) == 0:
            continue
        d = {k: v[:, t].ravel() for k, v in base.items()}
        d["seas_anchor"] = (ly[:, t + h - 12] - ly[:, t]).ravel()          # same month last year vs now
        d["seas_drift"] = (ly[:, t + h - 12] - ly[:, t - 12]).ravel()      # prior-year growth over same span
        d["horizon"] = h
        d["origin_idx"] = np.tile(t, n)
        d["target_idx"] = d["origin_idx"] + h
        d["origin_month"] = d["origin_idx"] % 12 + 1
        d["target_month"] = d["target_idx"] % 12 + 1
        d["district"] = np.repeat(meta["District_Name"].to_numpy(), len(t))
        d["sector"] = np.repeat(meta["Sector_Name"].to_numpy(), len(t))
        d["series_row"] = np.repeat(np.arange(n), len(t))
        ok = (t + h) < ly.shape[1]
        y_t = ly[:, t].ravel()
        tgt = np.full((n, len(t)), np.nan)
        tgt[:, ok] = ly[:, (t + h)[ok]] - ly[:, t[ok]]
        d["y"] = tgt.ravel()
        d["log_y_t"] = y_t
        frames.append(pd.DataFrame(d))
    df = pd.concat(frames, ignore_index=True)
    for c in ("district", "sector"):
        df[c] = pd.Categorical(df[c], categories=sorted(meta["District_Name" if c == "district" else "Sector_Name"].unique()))
    return df


def feature_cols(df):
    drop = {"y", "log_y_t", "origin_idx", "target_idx", "series_row"}
    return [c for c in df.columns if c not in drop]


def window_mask(df, span):
    """True for rows whose [origin-12, target] window does NOT touch `span`."""
    lo, hi = span
    return ~((df["target_idx"] >= lo) & (df["origin_idx"] - 12 <= hi))


def anchor(df):
    return df["seas_drift"].to_numpy() if RESIDUAL_ON_DRIFT else np.zeros(len(df))


def predict(model, df, feats, num_iteration=None):
    """Log-change forecast = baseline anchor + learned correction."""
    return anchor(df) + model.predict(df[feats], num_iteration=num_iteration)


# ----------------------------------------------------------------------------------------------------------------
# Training / evaluation helpers
# ----------------------------------------------------------------------------------------------------------------
def fit(train, feats, val=None, n_estimators=None):
    params = dict(LGB_PARAMS)
    if n_estimators:
        params["n_estimators"] = n_estimators
    m = lgb.LGBMRegressor(**params)
    kw = {}
    if val is not None:
        kw = dict(eval_set=[(val[feats], val["y"] - anchor(val))], eval_metric="l1",
                  callbacks=[lgb.early_stopping(100, verbose=False)])
    m.fit(train[feats], train["y"] - anchor(train), **kw)
    return m


def to_level(df, log_ratio):
    return np.exp(df["log_y_t"].to_numpy() + log_ratio)


def metrics(actual, pred):
    err = pred - actual
    return dict(
        WAPE_pct=100 * np.abs(err).sum() / actual.sum(),
        sMAPE_pct=100 * np.mean(2 * np.abs(err) / (np.abs(actual) + np.abs(pred))),
        MedAPE_pct=100 * np.median(np.abs(err) / actual),
        Bias_pct=100 * err.sum() / actual.sum(),
    )


def score_table(test, preds, target):
    rows = []
    actual = np.exp(test["log_y_t"] + test["y"]).to_numpy()
    for model_name, lr in preds.items():
        lvl = to_level(test, lr)
        for label, mask in [("all", np.ones(len(test), bool))] + \
                [(f"h={h}", test["horizon"].to_numpy() == h) for h in (1, 3, 6, 9, 12)] + \
                [(f"sector={s}", (test["sector"] == s).to_numpy()) for s in sorted(test["sector"].unique())]:
            if mask.sum():
                rows.append(dict(target=target, model=model_name, slice=label, n=int(mask.sum()),
                                 **metrics(actual[mask], lvl[mask])))
    return rows


# ----------------------------------------------------------------------------------------------------------------
# Gap analysis
# ----------------------------------------------------------------------------------------------------------------
def classify(cov, change):
    if cov >= COVERAGE_ACUTE_SHORTAGE:
        status = "Acute Shortage"
    elif cov < COVERAGE_SATURATION:
        status = "Saturation Risk"
    elif cov < COVERAGE_OVERSUPPLY_WATCH:
        status = "Oversupply Watch"
    else:
        status = "Balanced"
    trend = "Worsening supply glut" if change <= -TREND_ALERT else \
        "Tightening" if change >= TREND_ALERT else "Stable"
    return status, trend


def build_gap_tables(fc, hist):
    """fc: monthly forecast frame; hist: last-12-month actuals per series."""
    g = fc.groupby(["State_Name", "District_Name", "Sector_Name"], as_index=False).agg(
        Employed_Fcst=("employed", "mean"), Vacancies_Fcst=("vacancies", "mean"), Seekers_Fcst=("seekers", "mean"))
    g = g.merge(hist, on=["State_Name", "District_Name", "Sector_Name"])
    g["Employment_Growth_Pct"] = 100 * (g["Employed_Fcst"] / g["Employed_Last12M"] - 1)
    g["Net_Gap_Persons"] = g["Vacancies_Fcst"] - g["Seekers_Fcst"]          # >0: openings exceed seekers
    g["Coverage_Fcst"] = g["Vacancies_Fcst"] / g["Seekers_Fcst"]
    g["Coverage_Last12M"] = g["Vacancies_Last12M"] / g["Seekers_Last12M"]
    g["Coverage_Change_Pct"] = 100 * (g["Coverage_Fcst"] / g["Coverage_Last12M"] - 1)
    flags = [classify(c, ch / 100) for c, ch in zip(g["Coverage_Fcst"], g["Coverage_Change_Pct"])]
    g["Status_Flag"], g["Trend_Flag"] = zip(*flags)
    g["Surplus_Rank_Overall"] = g["Net_Gap_Persons"].rank(method="first").astype(int)         # 1 = largest glut
    g["Shortage_Rank_Overall"] = g["Net_Gap_Persons"].rank(ascending=False, method="first").astype(int)
    g["Surplus_Rank_In_Sector"] = g.groupby("Sector_Name")["Net_Gap_Persons"].rank(method="first").astype(int)
    g["Shortage_Rank_In_Sector"] = g.groupby("Sector_Name")["Net_Gap_Persons"].rank(
        ascending=False, method="first").astype(int)
    num = g.select_dtypes("number").columns
    g[num] = g[num].round(3)
    return g.sort_values("Surplus_Rank_Overall")


# ----------------------------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------------------------
def main():
    OUT.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    df, meta, cols, arrays = load_panel()
    T = len(cols)
    assert T == 192
    all_metrics, importances, resid_val, resid_test, best_iters = [], [], [], [], {}
    final_models, test_cov = {}, []
    fc_frames = {}

    for name, col in TARGETS.items():
        print(f"\n=== {name} ({col}) ===", flush=True)
        rows = build_rows(name, arrays, meta, T=T)
        feats = feature_cols(rows)
        if name == "seekers":
            rows = rows[window_mask(rows, ESHRAM_RAMP)]
        if EXCLUDE_COVID_WINDOWS:
            rows = rows[window_mask(rows, COVID_WINDOW)]
        rows = rows.reset_index(drop=True)

        # --- A: early stopping fold -----------------------------------------------------------------------------
        trainA = rows[rows["target_idx"] <= IDX_VAL_ORIGIN]
        valA = rows[(rows["origin_idx"] >= IDX_VAL_ORIGIN) & (rows["target_idx"] <= IDX_TEST_ORIGIN)]
        mA = fit(trainA, feats, valA)
        best = int(mA.best_iteration_ or LGB_PARAMS["n_estimators"])
        best_iters[name] = best
        print(f"fold A: best_iteration={best}, rows train={len(trainA):,} val={len(valA):,}", flush=True)
        print(f"fold A val L1(log) ={mA.best_score_['valid_0']['l1']:.5f}", flush=True)
        predA = predict(mA, valA, feats, best)
        resid_val.append(valA[["horizon", "sector"]].assign(target=name, err=valA["y"].to_numpy() - predA))

        # --- B: honest test fold --------------------------------------------------------------------------------
        trainB = rows[rows["target_idx"] <= IDX_TEST_ORIGIN]
        test = rows[(rows["origin_idx"] >= IDX_TEST_ORIGIN)].reset_index(drop=True)
        mB = fit(trainB, feats, n_estimators=best)
        pred = {
            "LightGBM": predict(mB, test, feats),
            "Seasonal naive": test["seas_anchor"].to_numpy(),
            "Seasonal naive + drift": test["seas_drift"].to_numpy(),
            "Last value": np.zeros(len(test)),
        }
        all_metrics += score_table(test, pred, name)
        resid_test.append(test[["horizon", "sector"]].assign(target=name, err=test["y"].to_numpy() - pred["LightGBM"]))
        # interval coverage: quantiles learned on fold A residuals, checked on fold B
        ev = resid_val[-1]
        q = ev.groupby("horizon")["err"].quantile([0.05, 0.95]).unstack()
        lo = pred["LightGBM"] + test["horizon"].map(q[0.05]).to_numpy()
        hi = pred["LightGBM"] + test["horizon"].map(q[0.95]).to_numpy()
        test_cov.append(dict(target=name, nominal=0.90,
                             empirical=float(((test["y"] >= lo) & (test["y"] <= hi)).mean())))
        importances.append(pd.DataFrame({"target": name, "feature": feats,
                                         "gain": mB.booster_.feature_importance("gain")}))
        lgb_wape = [m for m in all_metrics if m["target"] == name and m["model"] == "LightGBM" and m["slice"] == "all"][0]
        print(f"fold B (test 2025-01..2026-12): LightGBM WAPE={lgb_wape['WAPE_pct']:.2f}%", flush=True)

        # --- C: final model + 2027 forecast ---------------------------------------------------------------------
        mC = fit(rows, feats, n_estimators=int(best * 1.1))
        mC.booster_.save_model(str(MODEL_DIR / f"lgbm_{name}.txt"))
        origin = {h: np.array([T - 1]) for h in HORIZONS}
        fut = build_rows(name, arrays, meta, origins_by_h=origin, T=T)
        lr = predict(mC, fut, feats)
        rv = pd.concat(resid_val[-1:] + resid_test[-1:])
        qf = rv.groupby("horizon")["err"].quantile([0.05, 0.95]).unstack()
        fut["Timestamp"] = [(START + pd.DateOffset(months=int(i))).strftime("%Y-%m") for i in fut["target_idx"]]
        fut["District_Name"] = fut["district"].astype(str)
        fut["Sector_Name"] = fut["sector"].astype(str)
        fut[name] = to_level(fut, lr)
        fut[f"{name}_p05"] = to_level(fut, lr + fut["horizon"].map(qf[0.05]).to_numpy())
        fut[f"{name}_p95"] = to_level(fut, lr + fut["horizon"].map(qf[0.95]).to_numpy())
        fc_frames[name] = fut[["District_Name", "Sector_Name", "Timestamp", "horizon", name,
                               f"{name}_p05", f"{name}_p95"]]
        final_models[name] = best

    # ---- write evaluation artefacts --------------------------------------------------------------------------
    met = pd.DataFrame(all_metrics).round(3)
    met.to_csv(OUT / "backtest_metrics.csv", index=False)
    pd.concat(importances).groupby(["target", "feature"], as_index=False)["gain"].sum() \
        .assign(gain_share_pct=lambda d: (100 * d["gain"] / d.groupby("target")["gain"].transform("sum")).round(2)) \
        .sort_values(["target", "gain"], ascending=[True, False]).to_csv(OUT / "feature_importance.csv", index=False)
    pd.DataFrame(test_cov).round(3).to_csv(OUT / "interval_coverage.csv", index=False)

    # ---- forecasts + gap analysis ----------------------------------------------------------------------------
    fc = fc_frames["employed"]
    for name in ("vacancies", "seekers"):
        fc = fc.merge(fc_frames[name].drop(columns="horizon"), on=["District_Name", "Sector_Name", "Timestamp"])
    fc = fc.merge(meta[["District_Name", "State_Name"]].drop_duplicates(), on="District_Name")
    fc["net_gap"] = fc["vacancies"] - fc["seekers"]
    fc["coverage"] = fc["vacancies"] / fc["seekers"]
    fc = fc.rename(columns={
        "employed": "Employed_Fcst", "employed_p05": "Employed_P05", "employed_p95": "Employed_P95",
        "vacancies": "Vacancies_Fcst", "vacancies_p05": "Vacancies_P05", "vacancies_p95": "Vacancies_P95",
        "seekers": "Seekers_Fcst", "seekers_p05": "Seekers_P05", "seekers_p95": "Seekers_P95",
        "net_gap": "Net_Gap_Persons", "coverage": "Coverage_Fcst", "horizon": "Horizon_Months"})
    out_cols = ["State_Name", "District_Name", "Sector_Name", "Timestamp", "Horizon_Months"] + \
        [c for c in fc.columns if c.endswith(("_Fcst", "_P05", "_P95")) or c == "Net_Gap_Persons"]
    fc = fc[out_cols].sort_values(["State_Name", "District_Name", "Sector_Name", "Timestamp"])
    fc.round(3).to_csv(OUT / "forecast_2027_monthly.csv", index=False)

    last12 = df[df["Timestamp"] > cols[-13]]
    hist = last12.groupby(["State_Name", "District_Name", "Sector_Name"], as_index=False).agg(
        Employed_Last12M=("Total_Employed_Workers", "mean"), Vacancies_Last12M=("Active_Job_Vacancies", "mean"),
        Seekers_Last12M=("eShram_Registered_Seekers", "mean"))
    fcm = fc.rename(columns={"Employed_Fcst": "employed", "Vacancies_Fcst": "vacancies", "Seekers_Fcst": "seekers"})
    gap = build_gap_tables(fcm, hist)
    gap.to_csv(OUT / "gap_ranking_2027.csv", index=False)
    fcm["Quarter"] = pd.PeriodIndex(fcm["Timestamp"], freq="M").asfreq("Q").astype(str)
    q = fcm.groupby(["State_Name", "District_Name", "Sector_Name", "Quarter"], as_index=False)[
        ["employed", "vacancies", "seekers"]].mean()
    q["Net_Gap_Persons"] = q["vacancies"] - q["seekers"]
    q["Coverage_Fcst"] = q["vacancies"] / q["seekers"]
    q.round(3).to_csv(OUT / "forecast_2027_quarterly.csv", index=False)

    json.dump({"data": DATA.name, "best_iterations": final_models, "horizons": HORIZONS,
               "train_cutoffs": {"fold_A_last_target": "2023-12", "fold_B_last_target": "2024-12",
                                 "final_last_target": "2026-12"},
               "thresholds": {"acute_shortage": COVERAGE_ACUTE_SHORTAGE, "oversupply_watch": COVERAGE_OVERSUPPLY_WATCH,
                              "saturation": COVERAGE_SATURATION, "trend_alert": TREND_ALERT},
               "lightgbm_params": {k: v for k, v in LGB_PARAMS.items() if k != "n_jobs"}},
              open(OUT / "model_metadata.json", "w"), indent=2)

    pd.set_option("display.width", 200)
    print("\nBACKTEST (test fold, all horizons)")
    print(met[met["slice"] == "all"][["target", "model", "WAPE_pct", "sMAPE_pct", "Bias_pct"]].to_string(index=False))
    print("\nInterval coverage on test fold:\n", pd.DataFrame(test_cov).round(3).to_string(index=False))
    print("\nStatus flags:\n", gap.groupby(["Sector_Name", "Status_Flag"]).size().to_string())


if __name__ == "__main__":
    main()
