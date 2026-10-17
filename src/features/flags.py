"""
Phase 5 (decision D7): relative early-warning flags.

Phase 4 showed that absolute coverage thresholds (1.0 / 0.20 / 0.10) collapse into one status per sector after the e-Shram launch.
These flags are RELATIVE: a district is compared with the other districts of its own sector in the same month, so common shifts
(the registry break, COVID, a sector-wide hiring cycle) cancel out.  Everything uses data up to month t only.

    coverage_3m       = sum of vacancies over 3 months / sum of seekers over 3 months
    cov_pct           = percentile (0-100) of log coverage among the districts of the same sector, same month
    relative status   Tightest decile  cov_pct >= 90      Tight             70 <= cov_pct < 90
                      Typical          30 < cov_pct < 70
                      Loose            10 < cov_pct <= 30  Loosest decile    cov_pct <= 10
    absolute context  (separate field) coverage level: openings >= seekers (>= 1.0), moderate (0.2-1.0), oversupplied (0.1-0.2), deep surplus (< 0.1)

IMPORTANT: the relative status ranks districts WITHIN a sector, so by construction the classes hold about 11/20/39/20/11% of districts every
month.  "Tightest decile" in Construction can still be a deep surplus in absolute terms; always show the absolute context beside it.
    cov_trend_rel     12-month change in log coverage minus the sector median change  (DIAGNOSTIC ONLY, see below)
    seat_mismatch     log[(district share of the sector's seats) / (district share of the sector's vacancies, trailing 12-month mean)]
                      > +0.5 seats exceed the district's demand share; < -0.5 seats fall short of it.

The trailing trend is NOT used in the status: on 2011-2024 data it predicts the opposite of what an early warning needs (a district whose
coverage fell faster than its sector is more likely to recover; see reports/features/flags_summary.json).  Forward-looking ("approaching",
"entering") flags are therefore defined in Phase 8 on model FORECASTS: the same percentile rules applied to forecast coverage at 6 and 12
months, compared against the persistence benchmark computed here.  Thresholds are placeholders to be validated in Phase 8.
"""
import warnings

import numpy as np
import pandas as pd

PCT_EXTREME = 10.0          # bottom / top decile of the sector
PCT_WATCH = 30.0            # bottom / top 30% for the "watch" classes
SEAT_ALERT = 0.5            # log points of seat-share versus vacancy-share mismatch
STATUSES = ["Tightest decile", "Tight", "Typical", "Loose", "Loosest decile"]


def _roll_sum(a, w):
    return pd.DataFrame(a.T).rolling(w, min_periods=w).sum().to_numpy().T


def relative_flags(D):
    """Arrays of shape (series, months) for coverage, percentile, relative trend, status code and seat mismatch."""
    lc = np.log(_roll_sum(D.X["V"], 3) / _roll_sum(D.X["S"], 3))
    pct = np.full_like(lc, np.nan)
    trend = np.full_like(lc, np.nan)
    trend[:, 12:] = lc[:, 12:] - lc[:, :-12]
    trend_rel = np.full_like(lc, np.nan)
    seat_mis = np.full_like(lc, np.nan)
    seats = D.aux["Training_Seats_Sanctioned"]
    v12 = pd.DataFrame(D.X["V"].T).rolling(12, min_periods=12).mean().to_numpy().T
    for s in np.unique(D.sector):
        m = D.sector == s
        sub = pd.DataFrame(lc[m])
        cnt = sub.notna().sum(axis=0).to_numpy()
        pct[m] = ((sub.rank(axis=0) - 0.5) / cnt * 100).to_numpy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)               # all-NaN early months
            trend_rel[m] = trend[m] - np.nanmedian(trend[m], axis=0, keepdims=True)
        ss, vv = seats[m], v12[m]
        seat_mis[m] = np.log((ss / ss.sum(axis=0, keepdims=True)) / (vv / vv.sum(axis=0, keepdims=True)))
    code = np.full(lc.shape, 2.0)                                       # Typical
    code[(pct <= PCT_WATCH)] = 3                                        # loose
    code[(pct >= 100 - PCT_WATCH)] = 1                                  # tight
    code[pct <= PCT_EXTREME] = 4                                        # loosest decile
    code[pct >= 100 - PCT_EXTREME] = 0                                  # tightest decile
    code[np.isnan(pct)] = np.nan
    return dict(coverage_3m_log=lc, cov_pct=pct, cov_trend_rel=trend_rel, status_code=code, seat_mismatch=seat_mis)


def absolute_context(coverage):
    """Absolute reading of a coverage value (openings per registered seeker); the Phase 1 thresholds, kept as context only."""
    c = np.asarray(coverage, float)
    return np.select([c >= 1.0, c >= 0.2, c >= 0.1], ["openings exceed seekers", "moderate", "oversupplied"], default="deep surplus")


def status_labels(code):
    out = np.full(code.shape, "", dtype=object)
    ok = ~np.isnan(code)
    out[ok] = np.array(STATUSES, dtype=object)[code[ok].astype(int)]
    return out
