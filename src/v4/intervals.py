#!/usr/bin/env python3
"""
v4 phase 5 - calibrated 90% prediction intervals for the 60-month forecasts.

Method: split-conformal on the log change.  The nonconformity score of a past forecast is its signed error e = actual - predicted (log scale), optionally divided by a
scale s (the series' own 12-month volatility, known at the origin).  For a new forecast with horizon h the interval is  predicted + s * [q05, q95]  where the quantiles are
taken over the scores of earlier out-of-sample forecasts of the same target, the same group and horizons h-2 .. h+2 (smoothing over neighbouring horizons).
The pool only holds forecasts of windows the model had not seen, so the intervals do not shrink with the in-sample fit.

Schemes compared (run 1, on the validation window only, calibrated on targets 2010-2012 and checked on 2013-2014; the lowest mean interval score wins):
    h            quantiles by horizon only
    h_sector     by horizon and sector
    h_volume     by horizon and volume class (low / normal median vacancies)
    h_scaled     scores divided by the series' 12-month volatility, by horizon
    h_scaled_sector, h_scaled_volume
Run 2 (the scheme chosen in run 1 is fixed):  calibrate on validation, check once on test;  calibrate on validation + test, check once on stress  ("forward"); and
    leave-one-window-out: calibrate on the two other windows, check on the third (how the pooled calibration of run 3 behaves, shock years included).
Run 3 (deploy): two ranges for the 2026-2030 forecasts (data/v4/interval_calibration.csv): the usual range, calibrated on validation + test, and the wide range, which also
    includes the stress window.

Run: python src/v4/intervals.py select|check|deploy
"""
import json
import sys

import numpy as np
import pandas as pd

import config as C
import model_lib as M

OUT = C.REPORTS / "evaluation"
ALPHA = 0.10
SMOOTH = 2                                   # horizons h-2 .. h+2 share a pool
SCHEMES = ("h", "h_sector", "h_volume", "h_scaled", "h_scaled_sector", "h_scaled_volume")
VOL_FLOOR = 0.005                             # lower bound of the volatility scale (monthly log-change sd)
MIN_POOL = 400                                # fewer scores than this: fall back to the pool of all groups at that horizon
MIN_ORIGINS = 8                               # a pool needs scores from at least this many different origins (scores of one origin share the same shocks)
SELECT_MAX_H = 24                             # the scheme is chosen on horizons the validation calibration split can cover (targets 2010-2012 allow up to 36 from a few origins)
SELECTED_FILE = OUT / "interval_scheme.json"


def load(window):
    df = pd.read_parquet(C.DATA / "interim" / f"predictions_{window}.parquet")
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    stats = pd.read_csv(C.DATA / "dim_series_stats.csv")
    s = df.series_row.to_numpy()
    df["sector"] = pd.Categorical(dim.Sector_Name.to_numpy()[s], categories=sorted(dim.Sector_Name.unique()))
    df["volume"] = np.where(stats.Low_Volume_Train.to_numpy()[s], "low", "normal")
    df["target_idx"] = df.origin_idx + df.horizon
    df["window"] = window
    return df


def parse(scheme):
    """(scores divided by the volatility scale?, grouping column or '') of a scheme name."""
    scaled = scheme.startswith("h_scaled")
    return scaled, scheme.removeprefix("h_scaled" if scaled else "h").strip("_")


def group_key(df, by):
    if by == "sector":
        return df.sector.astype(str).to_numpy()
    if by == "volume":
        return df.volume.to_numpy()
    return np.full(len(df), "all")


def score(df, k, scaled):
    e = (df[f"act_{k}"] - df[f"pred_{k}"]).to_numpy().astype(np.float64)
    if scaled:
        e = e / np.maximum(df[f"vol_{k}"].to_numpy().astype(np.float64), VOL_FLOOR)
    return e


def _pool(by_h, origins_by_h, hh):
    """Scores of horizons hh-r .. hh+r with r grown from SMOOTH until the pool has MIN_POOL scores from MIN_ORIGINS different origins (long horizons have few origins)."""
    for r in range(SMOOTH, 60):
        hs = range(max(1, hh - r), min(60, hh + r) + 1)
        n = sum(len(by_h[x]) for x in hs)
        if n >= MIN_POOL and len(set().union(*[origins_by_h[x] for x in hs])) >= MIN_ORIGINS:
            break
    return np.concatenate([by_h[x] for x in hs]), r


def calibrate(df, k, scheme, alpha=ALPHA):
    """Table of quantiles of the scores by (group, horizon): columns group, horizon, lo, hi, n, radius (horizons pooled on each side)."""
    scaled, by = parse(scheme)
    e, g, h, o = score(df, k, scaled), group_key(df, by), df.horizon.to_numpy(), df.origin_idx.to_numpy()
    ok = np.isfinite(e)
    e, g, h, o = e[ok], g[ok], h[ok], o[ok]
    hs = range(1, 61)
    everyone = ({x: e[h == x] for x in hs}, {x: set(np.unique(o[h == x]).tolist()) for x in hs})
    rows = []
    for grp in np.unique(g):
        m = g == grp
        eg, hg, og = e[m], h[m], o[m]
        by_h, origins_by_h = {x: eg[hg == x] for x in hs}, {x: set(np.unique(og[hg == x]).tolist()) for x in hs}
        for hh in hs:
            pool, r = _pool(by_h, origins_by_h, hh)
            if len(pool) < MIN_POOL:                                    # a small group: use every group at these horizons
                pool, r = _pool(*everyone, hh)
            rows.append((grp, hh, float(np.quantile(pool, alpha / 2)), float(np.quantile(pool, 1 - alpha / 2)), len(pool), r))
    return pd.DataFrame(rows, columns=["group", "horizon", "lo", "hi", "n", "radius"])


def apply(df, k, scheme, table):
    """Interval ends on the log-change scale (lo, hi), aligned with df."""
    scaled, by = parse(scheme)
    key = pd.MultiIndex.from_arrays([group_key(df, by), df.horizon.to_numpy()])
    t = table.set_index(["group", "horizon"])
    lo, hi = t.lo.reindex(key).to_numpy(), t.hi.reindex(key).to_numpy()
    if scaled:
        s = np.maximum(df[f"vol_{k}"].to_numpy().astype(np.float64), VOL_FLOOR)
        lo, hi = lo * s, hi * s
    p = df[f"pred_{k}"].to_numpy().astype(np.float64)
    return p + lo, p + hi


def evaluate(df, k, lo, hi, alpha=ALPHA):
    """Coverage, width and interval score (log scale) by slice; one row per (slice, value)."""
    y = df[f"act_{k}"].to_numpy().astype(np.float64)
    ok = np.isfinite(y)
    shock = df.shock_S.to_numpy() if k == "S" else df.shock_EV.to_numpy()
    inside = (y >= lo) & (y <= hi)
    width = hi - lo
    iscore = width + (2 / alpha) * np.maximum(lo - y, 0) + (2 / alpha) * np.maximum(y - hi, 0)
    d = pd.DataFrame({"inside": inside, "width": width, "iscore": iscore, "band": M.band_of(df.horizon.to_numpy()), "sector": df.sector.astype(str).to_numpy(),
                      "volume": df.volume.to_numpy(), "shock": np.where(shock, "touches a shock", "calm window")})[ok]
    rows = []
    for name, col in (("all", None), ("band", "band"), ("sector", "sector"), ("volume", "volume"), ("shock_window", "shock")):
        grp = [("all", d)] if col is None else list(d.groupby(col))
        for val, sub in grp:
            rows.append({"target": k, "slice": name, "value": val, "rows": len(sub), "coverage": sub.inside.mean(), "mean_width_log": sub.width.mean(),
                         "mean_width_pct": (np.exp(sub.width) - 1).mean() * 100, "interval_score": sub.iscore.mean()})
    return pd.DataFrame(rows)


def by_origin_coverage(df, k, lo, hi):
    """Coverage per forecast origin (rows of one origin share the same shocks, so this shows how much coverage moves from one origin to the next)."""
    y = df[f"act_{k}"].to_numpy().astype(np.float64)
    inside = (y >= lo) & (y <= hi)
    return pd.Series(inside).groupby([df.origin_idx.to_numpy(), df.horizon.to_numpy()]).mean()


def run_select():
    v = load("validation")
    cal = v[v.target_idx <= 155].reset_index(drop=True)
    chk = v[(v.target_idx >= 156) & (v.horizon <= SELECT_MAX_H)].reset_index(drop=True)
    print(f"validation split: calibrate {len(cal):,} rows (targets to 2012-12), check {len(chk):,} rows (2013-2014, horizons to 24)", flush=True)
    rows = []
    for k in "EVS":
        for sc in SCHEMES:
            lo, hi = apply(chk, k, sc, calibrate(cal, k, sc))
            r = evaluate(chk, k, lo, hi)
            a = r[r.slice == "all"].iloc[0]
            rows.append({"target": k, "scheme": sc, "coverage": a.coverage, "mean_width_pct": a.mean_width_pct, "interval_score": a.interval_score})
            print(k, sc, round(a.coverage, 4), round(a.mean_width_pct, 1), round(a.interval_score, 4), flush=True)
    t = pd.DataFrame(rows)
    t.round(4).to_csv(OUT / "interval_scheme_selection.csv", index=False)
    chosen = {k: t[t.target == k].sort_values("interval_score").iloc[0].scheme for k in "EVS"}
    SELECTED_FILE.write_text(json.dumps({"rule": "lowest mean interval score on validation targets 2013-2014 (calibrated on 2010-2012)", "scheme": chosen}, indent=2), encoding="utf-8")
    print("chosen", chosen)


def chosen():
    return json.loads(SELECTED_FILE.read_text(encoding="utf-8"))["scheme"]


def run_check():
    sch = chosen()
    wins = {w: load(w) for w in ("validation", "test", "stress")}
    forward = [("test", ["validation"]), ("stress", ["validation", "test"])]                       # calibrated only on earlier windows: what a user could have done
    pooled = [("validation", ["test", "stress"]), ("test", ["validation", "stress"]), ("stress", ["validation", "test"])]    # leave-one-window-out: how pooled calibration behaves
    res, orig = [], []
    for kind, target_w, cal_w in [("forward", *p) for p in forward] + [("leave_one_window_out", *p) for p in pooled]:
        cal, chk = pd.concat([wins[w] for w in cal_w], ignore_index=True), wins[target_w]
        for k in "EVS":
            table = calibrate(cal, k, sch[k])
            lo, hi = apply(chk, k, sch[k], table)
            r = evaluate(chk, k, lo, hi)
            r.insert(0, "window", target_w)
            r.insert(1, "calibration", kind)
            r.insert(2, "calibrated_on", "+".join(cal_w))
            r.insert(3, "scheme", sch[k])
            res.append(r)
            oc = by_origin_coverage(chk, k, lo, hi).groupby(level=1).agg(["min", "median", "max"])
            oc.insert(0, "target", k)
            oc.insert(0, "calibration", kind)
            oc.insert(0, "window", target_w)
            orig.append(oc.reset_index().rename(columns={"level_0": "horizon", "min": "cov_min_origin", "median": "cov_median_origin", "max": "cov_max_origin"}))
            a = r[(r.slice == "all")].iloc[0]
            print(kind, target_w, k, sch[k], "coverage", round(a.coverage, 4), "width %", round(a.mean_width_pct, 1), flush=True)
    pd.concat(res).round(4).to_csv(OUT / "interval_coverage.csv", index=False)
    pd.concat(orig).round(4).to_csv(OUT / "interval_coverage_by_origin.csv", index=False)


def run_deploy():
    """Two ranges per forecast: the usual 90% range (calibrated on the validation and test windows, the calm years) and the wide range (also the stress window, so it covers
    errors like those of 2020-2025).  One table: lo/hi are the usual range, lo_wide/hi_wide the wide range (log-change offsets from the point forecast, or in units of the
    series' volatility for a scaled scheme)."""
    sch = chosen()
    wins = {w: load(w) for w in ("validation", "test", "stress")}
    usual = pd.concat([wins["validation"], wins["test"]], ignore_index=True)
    wide = pd.concat(list(wins.values()), ignore_index=True)
    tabs = []
    for k in "EVS":
        u, w = calibrate(usual, k, sch[k]), calibrate(wide, k, sch[k])
        t = u.merge(w, on=["group", "horizon"], suffixes=("", "_wide"))
        t.insert(0, "scheme", sch[k])
        t.insert(0, "target", k)
        tabs.append(t)
    out = pd.concat(tabs)
    out.round(5).to_csv(C.DATA / "interval_calibration.csv", index=False)
    print("calibration rows", len(out))


if __name__ == "__main__":
    {"select": run_select, "check": run_check, "deploy": run_deploy}[sys.argv[1] if len(sys.argv) > 1 else "select"]()
