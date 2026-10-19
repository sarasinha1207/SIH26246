"""
Phase 8 (B2) - adaptive conformal prediction intervals (Gibbs & Candes style adaptive miscoverage level, Mondrian by sector and horizon).

For a forecast made at origin o with horizon h (target month o + h) the interval is the empirical [alpha_t/2, 1 - alpha_t/2] range of the SIGNED log errors
(actual - predicted) of earlier forecasts for the same target variable, sector and horizon whose target month is within the last `window` months up to and including o,
i.e. only errors that are already known at o.  alpha_t starts at 0.10 and is updated once a month and per (sector, horizon) from the miss rate of the intervals that
were issued for target month o:   alpha <- clip(alpha + gamma * (0.10 - miss_rate), 0.02, 0.5).   Too many misses lower alpha and widen the interval; too few raise it.
When fewer than `n_min` known errors are available (the first months, long horizons) the static fallback interval is used and alpha is not updated.
Errors in shock months (seekers: the e-Shram ramp) are excluded from the pool.  Declared settings (models/xgboost_v3/conformal.json): window 12, gamma 0.05, n_min 200.
"""
import numpy as np
import pandas as pd

DECLARED = dict(window=12, gamma=0.05, alpha=0.10, n_min=200, alpha_range=(0.02, 0.5))


def adaptive_intervals(R, C0, window=12, gamma=0.05, alpha=0.10, n_min=200, alpha_range=(0.02, 0.5)):
    """R: DataFrame with sector, horizon, origin_idx, target_idx, y (actual log), pred (log), excl (bool), static_lo, static_hi (log offsets).
    C0: calibration errors known before R starts (sector, horizon, target_idx, resid, excl).  Returns (lo, hi) log offsets aligned with R's row order."""
    R = R.reset_index(drop=True)
    lo, hi = R.static_lo.to_numpy().copy(), R.static_hi.to_numpy().copy()
    used = np.zeros(len(R), bool)
    resid_R = (R.y - R.pred).to_numpy()
    pool = pd.concat([C0.loc[~C0.excl, ["sector", "horizon", "target_idx", "resid"]],
                      pd.DataFrame({"sector": R.sector, "horizon": R.horizon, "target_idx": R.target_idx, "resid": resid_R})[~R.excl.to_numpy()]], ignore_index=True)
    alphas = []
    for (sec, h), grp in R.groupby(["sector", "horizon"]):
        pg = pool[(pool.sector == sec) & (pool.horizon == h)].sort_values("target_idx")
        t, r = pg.target_idx.to_numpy(), pg.resid.to_numpy()
        a = alpha
        by_origin = {o: np.asarray(v) for o, v in grp.groupby("origin_idx").groups.items()}
        by_target = {o: np.asarray(v) for o, v in grp.groupby("target_idx").groups.items()}
        for o in sorted(by_origin):
            if o in by_target:
                rows = by_target[o]
                rows = rows[used[rows] & ~R.excl.to_numpy()[rows]]
                if len(rows):
                    miss = float(np.mean((R.y.to_numpy()[rows] < R.pred.to_numpy()[rows] + lo[rows]) | (R.y.to_numpy()[rows] > R.pred.to_numpy()[rows] + hi[rows])))
                    a = float(np.clip(a + gamma * (alpha - miss), *alpha_range))
            sel = (t > o - window) & (t <= o)
            rows_o = np.asarray(by_origin[o])
            if sel.sum() >= n_min:
                lo[rows_o], hi[rows_o] = np.quantile(r[sel], a / 2), np.quantile(r[sel], 1 - a / 2)
                used[rows_o] = True
            alphas.append((sec, h, o, a, int(sel.sum())))
    return lo, hi, used, pd.DataFrame(alphas, columns=["sector", "horizon", "origin_idx", "alpha", "pool"])


def interval_metrics(R, lo, hi, alpha=0.10):
    ok = ~R.excl.to_numpy()
    y, p = R.y.to_numpy()[ok], R.pred.to_numpy()[ok]
    l, u = p + lo[ok], p + hi[ok]
    inside = (y >= l) & (y <= u)
    score = (u - l) + (2 / alpha) * np.maximum(l - y, 0) + (2 / alpha) * np.maximum(y - u, 0)
    width = 100 * (np.exp(u - l) - 1)
    df = pd.DataFrame({"horizon": R.horizon.to_numpy()[ok], "inside": inside, "width": width, "score": score})
    by_h = df.groupby("horizon").agg(coverage=("inside", "mean"), width_pct=("width", "mean"), interval_score=("score", "mean"))
    return dict(coverage=float(inside.mean()), width_pct=float(width.mean()), interval_score=float(score.mean()), by_horizon=by_h)
