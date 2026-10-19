#!/usr/bin/env python3
"""
Phase 9 - generate the forecast and early-warning flag files for one forecast origin.

    python src/deployment/forecast.py --origin 2026-10

Reads   data/processed/panel_monthly.parquet (cut off at the origin), models/deployed/origin_<origin>/ (written by refit.py).
Writes  outputs/forecasts/origin_<origin>/forecast_long.csv   one row per series x target x horizon (280 x 3 x 12 = 10,080): forecast, 90% interval, baseline, confidence label
        outputs/forecasts/origin_<origin>/flags.csv           one row per series x horizon (3,360): relative early-warning status from the forecast, today's status, change, reliability
        outputs/forecasts/origin_<origin>/manifest.json       counts, checksums, model and data fingerprints
        reports/deployment/synthetic_check_<origin>.json      forecast vs the simulated months after today, when the panel has them (synthetic, a sanity check only)

Interval policy (models/xgboost_v3/final_interval_policy.json): employed = static fold-based; vacancies = recalibrated static; seekers = adaptive conformal, whose error stream is the
declared v3 model's out-of-sample forecasts for 2022-12 onward (the deployed refit has no out-of-sample history yet).
Flags: Phase 5 relative classes applied to the forecast single-month coverage ratio (vacancies / seekers) among the 56 districts of a sector in the target month.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training", "evaluation", "deployment"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import features as df_  # noqa: E402
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from conformal import adaptive_intervals  # noqa: E402
from predict import Forecaster  # noqa: E402

V3 = ROOT / "models" / "xgboost_v3"
VARS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
HORIZON_GRID = [1, 3, 6, 12]


def status_of(p):
    return np.select([p >= 90, p >= 70, p > 30, p > 10], ["Tightest decile", "Tight", "Typical", "Loose"], "Loosest decile")


def context_of(c):
    return np.select([c >= 1.0, c >= 0.2, c >= 0.1], ["openings exceed seekers", "moderate", "oversupplied"], "deep surplus")


def seekers_adaptive(fc3, origin_idx, new_rows, cfg):
    """Adaptive conformal offsets for the new seekers forecasts, from the v3 model's already-known out-of-sample errors on the spent test split."""
    test = sp.load_split("test", unlock_test=True, verify=True)
    test = test[(test.origin_idx <= origin_idx) & (test.target_idx <= origin_idx)].reset_index(drop=True)
    p = fc3.predict(test, targets=("S",))
    R = pd.DataFrame({"sector": test.sector.to_numpy(), "horizon": test.horizon.to_numpy(), "origin_idx": test.origin_idx.to_numpy(), "target_idx": test.target_idx.to_numpy(),
                      "y": test["target_S"].to_numpy(), "pred": p["pred_log_S"].to_numpy(), "excl": test["target_in_shock_S"].to_numpy()})
    static = fc3.intervals["S"]
    R["static_lo"] = [static[str(int(h))][0] for h in R.horizon]
    R["static_hi"] = [static[str(int(h))][1] for h in R.horizon]
    N = pd.DataFrame({"sector": new_rows.sector.to_numpy(), "horizon": new_rows.horizon.to_numpy(), "origin_idx": new_rows.origin_idx.to_numpy(),
                      "target_idx": new_rows.origin_idx.to_numpy() + new_rows.horizon.to_numpy(), "y": np.nan, "pred": new_rows["pred_log_S"].to_numpy(), "excl": True})
    N["static_lo"] = [static[str(int(h))][0] for h in N.horizon]
    N["static_hi"] = [static[str(int(h))][1] for h in N.horizon]
    allr = pd.concat([R, N], ignore_index=True)
    empty = pd.DataFrame({"sector": [], "horizon": [], "target_idx": [], "resid": [], "excl": []})
    lo, hi, used, _ = adaptive_intervals(allr, empty, window=cfg["window"], gamma=cfg["gamma"], alpha=cfg["alpha"], n_min=cfg["n_min"], alpha_range=tuple(cfg["alpha_range"]))
    return lo[len(R):], hi[len(R):], used[len(R):]


def main(origin):
    t0 = time.time()
    mdir = ROOT / "models" / "deployed" / f"origin_{origin}"
    mman = json.load(open(mdir / "manifest.json"))
    for name, digest in mman["files_sha256"].items():
        assert sp.sha256(mdir / name) == digest, f"{name} changed since the refit"
    panel = df_.load_history(origin)
    rows, D = df_.forecast_rows(panel)
    O = int(rows.origin_idx.iloc[0])
    fc = Forecaster.load(mdir)
    pred = fc.predict(rows)
    cfg = json.load(open(mdir / "conformal.json"))
    fc3 = Forecaster.load(V3 / "primary")
    vrec = json.load(open(mdir / "vacancy_intervals_recalibrated.json"))["by_horizon"]
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str})[["Series_ID", "District_LGD_Code", "Econ_Tier", "Low_Volume"]]
    by_h = pd.read_csv(ROOT / "reports" / "evaluation" / "v3" / "original" / "by_horizon.csv")
    pred["horizon"] = rows.horizon.to_numpy()
    pred["sector"] = rows.sector.to_numpy()
    pred["origin_idx"] = rows.origin_idx.to_numpy()
    h = rows.horizon.to_numpy()
    offsets, method = {}, {}
    offsets["E"] = (np.array([fc.intervals["E"][str(int(x))][0] for x in h]), np.array([fc.intervals["E"][str(int(x))][1] for x in h]))
    method["E"] = np.full(len(h), "static (fold-based)", dtype=object)
    offsets["V"] = (np.array([vrec[str(int(x))][0] for x in h]), np.array([vrec[str(int(x))][1] for x in h]))
    method["V"] = np.full(len(h), "static (recalibrated)", dtype=object)
    slo, shi, used = seekers_adaptive(fc3, O, pred, cfg)
    offsets["S"] = (slo, shi)
    method["S"] = np.where(used, "adaptive conformal", "static (fold-based, fallback)")
    long_rows = []
    for k in "EVS":
        lvl = pred[f"pred_log_{k}"].to_numpy()
        base_name = "seasonal_naive_drift" if k == "E" else "last_plus_seasonal_shift"
        base = ld.baseline_log(rows, k, base_name)
        lo, hi = offsets[k]
        d = pd.DataFrame({"Series_ID": rows.Series_ID.to_numpy(), "target_variable": VARS[k], "horizon": h, "origin_month": rows.origin_date.dt.strftime("%Y-%m").to_numpy(),
                          "target_month": rows.target_date.dt.strftime("%Y-%m").to_numpy(), "forecast": np.exp(lvl), "lo90": np.exp(lvl + lo), "hi90": np.exp(lvl + hi),
                          "baseline_forecast": np.exp(base), "baseline_name": base_name.replace("_", " "), "interval_method": method[k], "last_observed": np.exp(rows[f"last_{k}"].to_numpy()),
                          "sector": rows.sector.to_numpy(), "state": rows.state.to_numpy(), "district": rows.district.to_numpy(), "_k": k})
        long_rows.append(d)
    L = pd.concat(long_rows, ignore_index=True).merge(dims, on="Series_ID", how="left")
    # confidence label and the typical test error for that target and horizon
    L["confidence"] = [("low" if (k == "V" or (s == "IT-ITeS" and k != "E")) else ("high" if k == "E" else "medium")) for k, s in zip(L._k, L.sector)]
    tw = by_h.set_index(["target", "horizon"])["v3"] if "v3" in by_h.columns else None
    L["typical_test_error_pct"] = [round(float(tw.loc[(k, int(x))]), 2) if tw is not None and (k, int(x)) in tw.index else np.nan for k, x in zip(L._k, L.horizon)]
    assert L[["forecast", "lo90", "hi90"]].notna().all().all()
    assert (L.lo90 < L.forecast).all() and (L.forecast < L.hi90).all() and (L.lo90 > 0).all()
    L = L.rename(columns={"District_LGD_Code": "district_lgd_code", "Econ_Tier": "district_tier", "Low_Volume": "low_volume_series"})
    L = L.drop(columns="_k").sort_values(["target_variable", "Series_ID", "horizon"]).reset_index(drop=True)
    for c in ("forecast", "lo90", "hi90", "baseline_forecast", "last_observed"):
        L[c] = L[c].round(1)
    # ---- flags
    W = pd.DataFrame({"Series_ID": rows.Series_ID.to_numpy(), "horizon": h, "sector": rows.sector.to_numpy(), "target_month": rows.target_date.dt.strftime("%Y-%m").to_numpy(),
                      "fc_V": np.exp(pred["pred_log_V"].to_numpy()), "fc_S": np.exp(pred["pred_log_S"].to_numpy()), "now_V": np.exp(rows.last_V.to_numpy()), "now_S": np.exp(rows.last_S.to_numpy())})
    W["forecast_coverage_ratio"] = W.fc_V / W.fc_S
    W["current_coverage_ratio"] = W.now_V / W.now_S
    W["forecast_percentile"] = W.groupby(["sector", "horizon"]).forecast_coverage_ratio.rank(pct=True) * 100
    W["current_percentile"] = W.groupby(["sector", "horizon"]).current_coverage_ratio.rank(pct=True) * 100
    W["forecast_status"] = status_of(W.forecast_percentile.to_numpy())
    W["current_status"] = status_of(W.current_percentile.to_numpy())
    W["absolute_context"] = context_of(W.forecast_coverage_ratio.to_numpy())
    W["change"] = np.select([(W.forecast_status == "Tightest decile") & (W.current_status != "Tightest decile"), (W.forecast_status == "Loosest decile") & (W.current_status != "Loosest decile"),
                             (W.forecast_status != "Tightest decile") & (W.current_status == "Tightest decile"), (W.forecast_status != "Loosest decile") & (W.current_status == "Loosest decile")],
                            ["entering tightest decile", "entering loosest decile", "leaving tightest decile", "leaving loosest decile"], "no change")
    fl = pd.read_csv(ROOT / "reports" / "evaluation" / "test" / "flag_check.csv")
    prec = {ev: fl[(fl.flag_source == "model forecast (blended seekers)") & fl.event.str.startswith(ev)].set_index("horizon").precision for ev in ("tightest", "loosest")}
    interp = lambda s, hh: np.interp(hh, HORIZON_GRID, [s.loc[g] for g in HORIZON_GRID])  # noqa: E731
    W["historical_precision"] = np.where(W.forecast_status == "Tightest decile", interp(prec["tightest"], W.horizon), np.where(W.forecast_status == "Loosest decile", interp(prec["loosest"], W.horizon), np.nan))
    W["confidence"] = "low"                                    # the flag is driven by vacancy forecasts, which have low confidence
    W = W.merge(dims, on="Series_ID", how="left").rename(columns={"District_LGD_Code": "district_lgd_code", "Econ_Tier": "district_tier", "Low_Volume": "low_volume_series"})
    W = W.drop(columns=["fc_V", "fc_S", "now_V", "now_S"]).sort_values(["Series_ID", "horizon"]).reset_index(drop=True)
    for c in ("forecast_coverage_ratio", "current_coverage_ratio", "forecast_percentile", "current_percentile", "historical_precision"):
        W[c] = W[c].round(4)
    out = ROOT / "outputs" / "forecasts" / f"origin_{origin}"
    out.mkdir(parents=True, exist_ok=True)
    L.to_csv(out / "forecast_long.csv", index=False, lineterminator="\n")
    W.to_csv(out / "flags.csv", index=False, lineterminator="\n")
    # ---- coverage summary and fingerprints
    cover = {"series": int(L.Series_ID.nunique()), "districts": int(L.district_lgd_code.nunique()), "states": int(L.state.nunique()), "tiers": int(L.district_tier.nunique()), "sectors": int(L.sector.nunique()),
             "targets": sorted(L.target_variable.unique().tolist()), "horizons": sorted(L.horizon.unique().tolist()), "forecast_rows": int(len(L)), "flag_rows": int(len(W)),
             "rows_per_series_target": sorted(L.groupby(["Series_ID", "target_variable"]).size().unique().tolist())}
    syn = {}
    full = pd.read_parquet(df_.PANEL, columns=["Series_ID", "Date", *VARS.values()])
    for k in "EVS":
        for hh in (1, 2):
            tm = (pd.Period(origin, "M") + hh).to_timestamp()
            act = full[full.Date == tm].set_index("Series_ID")[VARS[k]]
            if len(act) == 280:
                f = L[(L.target_variable == VARS[k]) & (L.horizon == hh)].set_index("Series_ID").forecast
                syn[f"{k}_h{hh}"] = {"target_month": str(tm.date()), "wape_pct": round(float(100 * np.abs(act - f.loc[act.index]).sum() / act.sum()), 3)}
    json.dump({"note": "the target months are simulated months after today; a sanity check only", "checks": syn}, open(ROOT / "reports" / "deployment" / f"synthetic_check_{origin}.json", "w"), indent=1)
    man = {"origin": origin, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "coverage": cover, "files_sha256": {f.name: sp.sha256(f) for f in sorted(out.glob("*.csv"))},
           "model_manifest_sha256": sp.sha256(mdir / "manifest.json"), "panel_sha256": sp.sha256(df_.PANEL), "history_last_month": str(D.dates[-1].date()),
           "interval_policy": json.load(open(V3 / "final_interval_policy.json"))["policy"], "seekers_intervals_adaptive_share": float(np.mean(used)),
           "confidence_rules": {"employed": "high", "seekers": "medium", "vacancies": "low (small gain over the baseline in 2025-26); every IT-ITeS vacancy or seeker forecast is low"},
           "flag_rules": "forecast single-month vacancies/seekers ratio, percentile among the 56 districts of the sector in the target month; deciles at 10/90, watch classes at 30/70; absolute context kept separate",
           "seconds": round(time.time() - t0, 1)}
    json.dump(man, open(out / "manifest.json", "w"), indent=1)
    print(json.dumps(cover, indent=1)); print("synthetic check:", syn)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    main(ap.parse_args().origin)
