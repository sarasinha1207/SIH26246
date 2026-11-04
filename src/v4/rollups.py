#!/usr/bin/env python3
"""
v4 phase 6 - forecasts and 90% ranges for the aggregates (district-sector, state-sector, state, sector, trade, India).

Point forecasts add up: an aggregate is the sum of its (reconciled) trade forecasts, so the five trades of a district-sector equal the district-sector exactly and the
district-sectors equal the state-sector, sector and India totals.  Ranges do not add up (errors of neighbouring series partly cancel), so each aggregation level has
its own calibration: the log error of the aggregate forecast over earlier out-of-sample windows, pooled over the groups of the level, by horizon (the same split-conformal
recipe as phase 5).  Coverage is checked as in phase 5: calibrate on earlier windows, check on the next (forward), and calibrate on the two other windows (leave-one-window-out).
Errors of neighbouring series share the same shocks, so the errors of an aggregate are dominated by common drift and its range calibrated on calm years is too narrow; the wide range
(which includes the stress window) is the one shown for aggregates.

Run: python src/v4/rollups.py check|deploy       (check writes reports/v4/evaluation/aggregate_interval_coverage.csv, deploy writes data/v4/aggregate_interval_calibration.csv)
     the roll-up table itself is built by rollup_forecast(), called from exports.py
"""
import sys

import numpy as np
import pandas as pd

import config as C
import intervals as IV

OUT = C.REPORTS / "evaluation"
LEVELS = {"district_sector": ["District_LGD_Code", "Sector_Name"], "state_sector": ["State_Name", "Sector_Name"], "state": ["State_Name"],
          "sector": ["Sector_Name"], "trade": ["Trade_Code"], "india": []}
KEYS = ["State_Name", "District_LGD_Code", "Sector_Name", "Trade_Code"]
MIN_POOL, MIN_ORIGINS = 100, 8


def group_ids(dim, cols):
    if not cols:
        return np.zeros(len(dim), np.int64)
    return pd.factorize(dim[cols].astype(str).agg("|".join, axis=1))[0].astype(np.int64)


def aggregate_scores(pred, dim, level, k):
    """Frame (origin_idx, horizon, group, pred_k, act_k): log change of the aggregate forecast and of the aggregate actual, per group, origin and horizon."""
    gid = group_ids(dim, LEVELS[level])[pred.series_row.to_numpy()]
    b = pred[f"base_{k}"].to_numpy(np.float64)
    d = pd.DataFrame({"o": pred.origin_idx.to_numpy(), "h": pred.horizon.to_numpy(), "g": gid, "B": np.exp(b), "P": np.exp(b + pred[f"pred_{k}"].to_numpy(np.float64)),
                      "A": np.exp(b + pred[f"act_{k}"].to_numpy(np.float64))})
    s = d.groupby(["o", "h", "g"], sort=False).sum().reset_index()
    return pd.DataFrame({"origin_idx": s.o, "horizon": s.h, "group": s.g, f"pred_{k}": np.log(s.P / s.B), f"act_{k}": np.log(s.A / s.B)})


def calibrate_level(frames, level, k):
    """Quantile table (horizon, lo, hi, n, radius) for one level and target from the aggregate scores of several windows."""
    df = pd.concat([aggregate_scores(f, DIM, level, k) for f in frames], ignore_index=True)
    return IV.calibrate(df, k, "h", min_pool=MIN_POOL, min_origins=MIN_ORIGINS).drop(columns="group")


def run_check():
    wins = {w: IV.load(w) for w in ("validation", "test", "stress")}
    rows = []
    plans = [("forward", "test", ["validation"]), ("forward", "stress", ["validation", "test"]),
             ("leave_one_window_out", "validation", ["test", "stress"]), ("leave_one_window_out", "test", ["validation", "stress"])]
    for kind, target_w, cal_w in plans:
        for level in LEVELS:
            for k in "EVS":
                t = calibrate_level([wins[w] for w in cal_w], level, k).set_index("horizon")
                chk = aggregate_scores(wins[target_w], DIM, level, k)
                lo, hi = t.lo.reindex(chk.horizon).to_numpy(), t.hi.reindex(chk.horizon).to_numpy()
                p, a = chk[f"pred_{k}"].to_numpy(), chk[f"act_{k}"].to_numpy()
                inside = (a >= p + lo) & (a <= p + hi)
                rows.append({"calibration": kind, "window": target_w, "level": level, "target": k, "groups": int(chk.group.nunique()), "scores": len(chk), "coverage": inside.mean(),
                             "mean_width_pct": (np.exp(hi - lo) - 1).mean() * 100, "wape_pct": float(np.mean(np.abs(np.exp(p) - np.exp(a)) / np.exp(a)) * 100)})
    pd.DataFrame(rows).round(4).to_csv(OUT / "aggregate_interval_coverage.csv", index=False)


def run_deploy():
    wins = {w: IV.load(w) for w in ("validation", "test", "stress")}
    usual, wide = [wins["validation"], wins["test"]], list(wins.values())
    tabs = []
    for level in LEVELS:
        for k in "EVS":
            u, w = calibrate_level(usual, level, k), calibrate_level(wide, level, k)
            t = u.merge(w, on="horizon", suffixes=("", "_wide"))
            t.insert(0, "target", k)
            t.insert(0, "level", level)
            tabs.append(t)
    pd.concat(tabs).round(5).to_csv(C.DATA / "aggregate_interval_calibration.csv", index=False)
    print("rows", sum(len(t) for t in tabs))


def rollup_forecast(fc, dim, calib):
    """Long table of the aggregates: level, keys, month, E/V/S and their usual and wide 90% ranges (whole persons)."""
    rows = []
    f = fc.merge(dim[["Series_ID"] + [c for c in KEYS if c in dim]], on="Series_ID", how="left")
    for level, cols in LEVELS.items():
        g = f.groupby(cols + ["horizon", "month"], sort=False)[["E", "V", "S"]].sum().reset_index() if cols else f.groupby(["horizon", "month"])[["E", "V", "S"]].sum().reset_index()
        for k in "EVS":
            t = calib[(calib.level == level) & (calib.target == k)].set_index("horizon")
            for nm in ("lo", "hi", "lo_wide", "hi_wide"):
                off = t[nm].reindex(g.horizon).to_numpy()
                off = np.minimum(off, 0) if nm.startswith("lo") else np.maximum(off, 0)          # a range always contains its own point forecast
                g[f"{k}_{nm}"] = np.rint(g[k] * np.exp(off)).astype(np.int64)
        g.insert(0, "level", level)
        for c in KEYS:
            if c not in g:
                g[c] = None
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    return out[["level"] + KEYS + ["horizon", "month", "E", "E_lo", "E_hi", "E_lo_wide", "E_hi_wide", "V", "V_lo", "V_hi", "V_lo_wide", "V_hi_wide", "S", "S_lo", "S_hi", "S_lo_wide", "S_hi_wide"]]


DIM = pd.read_csv(C.DATA / "dim_series.csv")

if __name__ == "__main__":
    {"check": run_check, "deploy": run_deploy}[sys.argv[1]]()
