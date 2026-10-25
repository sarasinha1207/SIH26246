"""
v4 phase 3 - leak-safe features for forecasting up to 60 months ahead.

One training example is (series, forecast origin t, horizon h).  Every feature is computed from data at or before month t: trailing windows, expanding
statistics and cross-sections at t, never a centred window or a future value.  What comes from after t is only the target (log level at t + h) and the
calendar month of t + h, which is known in advance.

Differences from v3 (src/features/engineering.py, 12 months, 280 series)
  * horizons 1..60.  The year-ago anchor of horizon h is the latest observation in the same calendar month as the target that is not after t
    (index t + h - 12*ceil(h/12), always in (t-12, t]); v3's t + h - 12 would read the future for h > 12.
  * 25 trades, 10 states: group aggregates for the sector, the trade (all districts) and the state-sector cell; relative-size features against the trade.
  * four source channels (portal postings, quarterly hiring survey, NCS vacancies, labour-force survey) enter as growth and deviation features; a channel
    that has not started yet is missing (NaN), which XGBoost handles natively.
  * shocks: COVID-19, the 2016-17 demonetisation / GST months, the 2008-09 slowdown (and the e-Shram ramp for seekers) are excluded from the seasonal profile and
    flag the rows whose window touches them (evaluation only; the flags are not model inputs).
  * the features that are (near) monotone in calendar time are kept out of the model inputs, as in v3 (TIME_PROXY_FEATURES).
"""
import warnings

import numpy as np
import pandas as pd

import config as C

T = C.N_MONTHS
KEYS = ("E", "V", "S")
TARGET_COLS = C.TARGETS
IDX = lambda y, m: (y - 2000) * 12 + m - 1                                  # month index (2000-01 = 0)
SHOCK_SPANS = {                                                              # inclusive month-index spans
    "covid": (IDX(2020, 3), IDX(2022, 2)),
    "policy": [(IDX(2016, 11), IDX(2017, 1)), (IDX(2017, 7), IDX(2017, 10))],
    "slowdown": (IDX(2008, 10), IDX(2009, 11)),
    "eshram": (IDX(2021, 8), IDX(2023, 2)),
}
# Features that are (near) monotone functions of calendar time: trees cannot extrapolate them and they let a model memorise the year.
TIME_PROXY_FEATURES = {"log_pop", "wage_log", "seats_per_kpop", "female_pct", "seek_rate", "coverage", "post_covid", "eshram_progress"}
CAT_COLS = {"cat_sector": "Sector_Name", "cat_trade": "Trade_Code", "cat_tier": "Econ_Tier", "cat_state": "State_Name", "cat_district": "District_Name"}
EVAL_ONLY = {"origin_idx", "target_idx", "series_row", "shock_EV", "shock_S"}


def span_mask(spans):
    m = np.zeros(T, bool)
    for lo, hi in (spans if isinstance(spans, list) else [spans]):
        m[lo:hi + 1] = True
    return m


class PanelData:
    """Series x month arrays from the trade panel (sorted by Series_ID and Date) and its dimension table."""

    def __init__(self, df, dim):
        self.sid = dim.Series_ID.tolist()
        nS = len(self.sid)
        assert len(df) == nS * T and (df.Series_ID.to_numpy()[::T] == np.array(self.sid)).all(), "the panel must be complete and sorted like dim_series"
        arr = lambda col: df[col].to_numpy().reshape(nS, T)
        self.nS = nS
        self.X = {k: arr(c).astype(np.float64) for k, c in TARGET_COLS.items()}
        self.L = {k: np.log(v).astype(np.float32) for k, v in self.X.items()}
        self.aux = {c: arr(c).astype(np.float32) for c in ["Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "District_Total_Population_Est", "Training_Seats_Sanctioned",
                                                           "Trainees_Certified_Monthly", "Female_Share_Pct", "Edu_Graduate_and_Above_Pct", "Age_15_24_Pct"]}
        self.sig = {c: arr(c).astype(np.float64) for c in ["Sig_Portal_Postings", "Sig_Hiring_Survey_Index", "Sig_NCS_Vacancies", "Sig_Labour_Survey_Employment"]}
        self.meta = dim.set_index("Series_ID").loc[self.sid]
        self.shock_E = span_mask([SHOCK_SPANS["covid"], *SHOCK_SPANS["policy"], SHOCK_SPANS["slowdown"]])
        self.shock_S = self.shock_E | span_mask(SHOCK_SPANS["eshram"])
        self.cat_codes, self.cat_levels = {}, {}
        for cname, mcol in CAT_COLS.items():
            col = self.meta[mcol] if mcol in self.meta else self.meta.index.to_series()
            levels = sorted(col.unique())
            self.cat_levels[cname] = levels
            self.cat_codes[cname] = pd.Categorical(col, categories=levels).codes.astype(np.int32)


def roll_mean(a, w):
    return pd.DataFrame(a.T).rolling(w, min_periods=w).mean().to_numpy().T


def roll_std(a, w):
    return pd.DataFrame(a.T).rolling(w, min_periods=w).std().to_numpy().T


def lagdiff(a, k):
    out = np.full(a.shape, np.nan, dtype=np.float64)
    out[:, k:] = a[:, k:].astype(np.float64) - a[:, :-k]
    return out


def seasonal_profile(L, shock):
    """(series, origin t, calendar month) seasonal factors using only observations up to t.

    r_s = log x_s - mean(log x over s-12..s-1) is a trailing quantity; months whose 13-month window touches a shock are dropped; the profile for calendar
    month m at origin t is the mean of r_s over s <= t with month m (at least 2 observations), centred over the months."""
    L = L.astype(np.float64)
    prev12 = roll_mean(np.concatenate([np.full((L.shape[0], 1), np.nan), L[:, :-1]], axis=1), 12)
    r = L - prev12
    touched = pd.Series(shock.astype(int)).rolling(13, min_periods=1).sum().to_numpy() > 0
    r[:, touched] = np.nan
    mon = np.arange(T) % 12
    prof = np.full((L.shape[0], T, 12), np.nan)
    for m in range(12):
        sel = mon == m
        ok = sel[None, :] & ~np.isnan(r)
        n = np.cumsum(ok, axis=1)
        prof[:, :, m] = np.where(n >= 2, np.cumsum(np.where(ok, r, 0.0), axis=1) / np.maximum(n, 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)                      # all-NaN early origins
        prof -= np.nanmean(prof, axis=2, keepdims=True)
    prof[np.isnan(prof).any(axis=2)] = np.nan
    return prof.astype(np.float32)


def group_features(D, F, prefix, gid):
    """Growth and deviation of the log of the summed series of each group (sector, trade, state-sector cell), copied back to every series of the group."""
    G = int(gid.max()) + 1
    for k in KEYS:
        tot = np.zeros((G, T))
        np.add.at(tot, gid, D.X[k])
        lt = np.log(tot)
        for name, a in (("mom3", lagdiff(lt, 3)), ("mom12", lagdiff(lt, 12)), ("dev12", lt - roll_mean(lt, 12))):
            F[f"{prefix}_{k}_{name}"] = a[gid]


def group_mean(a, gid):
    G = int(gid.max()) + 1
    s, n = np.zeros((G, a.shape[1])), np.bincount(gid, minlength=G)[:, None]
    np.add.at(s, gid, a.astype(np.float64))
    return (s / n)[gid]


def origin_features(D):
    """Features that depend on the origin only: {name: float32 array (series, T)}, and the seasonal profiles."""
    F = {}
    for k in KEYS:
        L = D.L[k]
        m3, m6, m12 = roll_mean(L, 3), roll_mean(L, 6), roll_mean(L, 12)
        F[f"{k}_dev0_3"], F[f"{k}_dev0_12"] = L - m3, L - m12
        F[f"{k}_dev3_12"], F[f"{k}_dev6_12"] = m3 - m12, m6 - m12
        for lag in (1, 3, 6, 12, 36):
            F[f"{k}_mom{lag}"] = lagdiff(L, lag)
        F[f"{k}_vol12"] = roll_std(lagdiff(L, 1), 12)
        F[f"{k}_mom36_pa"] = lagdiff(L, 36) / 3.0                                # growth per year over three years (for the long horizons)
    rates = {"vac_rate": D.L["V"] - D.L["E"], "seek_rate": D.L["S"] - D.L["E"], "coverage": D.L["V"] - D.L["S"]}
    for name, a in rates.items():
        F[name], F[f"{name}_dev12"], F[f"{name}_mom12"] = a, a - roll_mean(a, 12), lagdiff(a, 12)
    ur = D.aux["Unemployment_Rate_Pct"]
    F["ur"], F["ur_chg3"], F["ur_chg12"] = ur, lagdiff(ur, 3), lagdiff(ur, 12)
    # aggregates over the sector, the trade and the state-sector cell
    sec = D.cat_codes["cat_sector"]
    trd = D.cat_codes["cat_trade"]
    ss = pd.factorize(D.meta.State_Name.astype(str) + "|" + D.meta.Sector_Name.astype(str))[0].astype(np.int32)
    group_features(D, F, "sec", sec)
    group_features(D, F, "trd", trd)
    group_features(D, F, "ss", ss)
    # context
    pop = D.aux["District_Total_Population_Est"]
    F["log_pop"] = np.log(pop)
    wl = np.log(D.aux["Avg_Monthly_Wage_INR"])
    F["wage_log"], F["wage_rel"] = wl, wl - group_mean(wl, trd)
    F["rel_size_E"] = D.L["E"] - group_mean(D.L["E"], trd)
    seats = np.log(D.aux["Training_Seats_Sanctioned"])
    spk = np.log(D.aux["Training_Seats_Sanctioned"] / pop * 1000)
    F["seats_per_kpop"], F["seats_rel"] = spk, spk - group_mean(spk, trd)
    F["seat_to_vac"] = seats - D.L["V"]
    F["seat_to_vac_dev12"] = F["seat_to_vac"] - roll_mean(F["seat_to_vac"], 12)
    F["female_pct"] = D.aux["Female_Share_Pct"]
    F["female_rel"] = D.aux["Female_Share_Pct"] - group_mean(D.aux["Female_Share_Pct"], trd)
    cert12 = pd.DataFrame(D.aux["Trainees_Certified_Monthly"].T).rolling(12, min_periods=12).sum().to_numpy().T
    F["cert_to_vac"] = np.log1p(cert12) - D.L["V"]
    F["grad_pct"], F["youth_pct"] = D.aux["Edu_Graduate_and_Above_Pct"], D.aux["Age_15_24_Pct"]
    t = np.arange(T)
    since = np.clip((t - SHOCK_SPANS["eshram"][0] + 1) / (SHOCK_SPANS["eshram"][1] - SHOCK_SPANS["eshram"][0] + 1), 0, 1)
    F["post_covid"] = np.tile((t > SHOCK_SPANS["covid"][1]).astype(np.float32), (D.nS, 1))
    F["eshram_progress"] = np.tile(since.astype(np.float32), (D.nS, 1))
    # source channels: growth and deviation, missing until the channel exists
    P = np.log1p(D.sig["Sig_Portal_Postings"])
    F["portal_mom1"], F["portal_mom3"], F["portal_dev12"] = lagdiff(P, 1), lagdiff(P, 3), P - roll_mean(P, 12)
    F["portal_vs_vac_dev12"] = F["portal_dev12"] - F["V_dev0_12"]
    Q = np.log(D.sig["Sig_Hiring_Survey_Index"])
    F["survey_mom3"], F["survey_dev12"] = lagdiff(Q, 3), Q - roll_mean(Q, 12)
    N = np.log1p(D.sig["Sig_NCS_Vacancies"])
    F["ncs_mom3"], F["ncs_dev12"] = lagdiff(N, 3), N - roll_mean(N, 12)
    LS = np.log(D.sig["Sig_Labour_Survey_Employment"])
    F["lfs_mom3"], F["lfs_gap_dev12"] = lagdiff(LS, 3), (LS - D.L["E"]) - roll_mean(LS - D.L["E"], 12)
    SF = {k: seasonal_profile(D.L[k], D.shock_S if k == "S" else D.shock_E) for k in KEYS}
    mon = np.tile(np.arange(T) % 12, (D.nS, 1))
    for k in KEYS:
        F[f"{k}_sf_origin"] = np.take_along_axis(SF[k], mon[:, :, None], axis=2)[:, :, 0]
    return {n: a.astype(np.float32) for n, a in F.items()}, SF


def _window_hit(cs, lo, hi):
    return (cs[hi] - np.where(lo > 0, cs[np.maximum(lo - 1, 0)], 0)) > 0


def assemble(D, OF, SF, t, h, series=None, names=None, include_time_proxies=False):
    """Feature matrix for the cross product of (origin, horizon) pairs and series.  Returns (X, meta); row i*len(series)+j is pair i, series j.

    X holds the model inputs (float32, plus the categorical identity columns); meta holds series_row, origin_idx, horizon, target_idx and the shock flags."""
    series = np.arange(D.nS) if series is None else np.asarray(series)
    P, nS = len(t), len(series)
    s = np.tile(series, P).astype(np.int64)
    tt = np.repeat(np.asarray(t), nS).astype(np.int64)
    hh = np.repeat(np.asarray(h), nS).astype(np.int64)
    cols = {}
    for name, arr in OF.items():
        if names is None and (include_time_proxies or name not in TIME_PROXY_FEATURES) or names is not None and name in names:
            cols[name] = arr[s, tt]
    mO, mT = tt % 12, (tt + hh) % 12
    m = (hh + 11) // 12                                                      # ceil(h/12)
    ya = tt + hh - 12 * m                                                    # latest observation in the target's calendar month that is not after t
    assert (ya <= tt).all() and (ya > tt - 12).all()
    for k in KEYS:
        L = D.L[k]
        cols[f"{k}_ya_h"] = L[s, ya] - L[s, tt]
        cols[f"{k}_yadrift_h"] = L[s, ya] - L[s, tt - 12]
        cols[f"{k}_sf_shift"] = SF[k][s, tt, mT] - SF[k][s, tt, mO]
    cols["horizon"] = hh.astype(np.float32)
    cols["origin_month"], cols["target_month"] = (mO + 1).astype(np.float32), (mT + 1).astype(np.float32)
    cols["target_month_sin"], cols["target_month_cos"] = np.sin(2 * np.pi * (mT + 1) / 12).astype(np.float32), np.cos(2 * np.pi * (mT + 1) / 12).astype(np.float32)
    if names is not None:
        cols = {n: v for n, v in cols.items() if n in names}
    X = pd.DataFrame({n: np.asarray(v, dtype=np.float32) for n, v in cols.items()})
    for cname, codes in D.cat_codes.items():
        if names is None or cname in names:
            X[cname] = pd.Categorical.from_codes(codes[s], categories=D.cat_levels[cname])
    cs_E, cs_S = np.cumsum(D.shock_E.astype(int)), np.cumsum(D.shock_S.astype(int))
    lo, hi = np.maximum(tt - 12, 0), np.minimum(tt + hh, T - 1)
    meta = pd.DataFrame({"series_row": s.astype(np.int32), "origin_idx": tt.astype(np.int32), "horizon": hh.astype(np.int16), "target_idx": (tt + hh).astype(np.int32),
                         "shock_EV": _window_hit(cs_E, lo, hi), "shock_S": _window_hit(cs_S, lo, hi)})
    return X, meta


def target_change(D, meta, k):
    """Log change from the origin to the target month for target `k` (NaN when the target month is after the data)."""
    s, t, tgt = meta.series_row.to_numpy(), meta.origin_idx.to_numpy(), meta.target_idx.to_numpy()
    ok = tgt < T
    y = np.full(len(meta), np.nan, dtype=np.float32)
    y[ok] = D.L[k][s[ok], tgt[ok]] - D.L[k][s[ok], t[ok]]
    return y


def group_of(name):
    """Feature group (for documentation and ablation)."""
    if name == "horizon":
        return "core_horizon"
    if name.startswith(("sec_", "trd_", "ss_")):
        return {"sec": "sector_aggregates", "trd": "trade_aggregates", "ss": "state_sector_aggregates"}[name.split("_")[0]]
    if name[:2] in ("E_", "V_", "S_"):
        kind = name[2:]
        return ("level_dev" if kind.startswith("dev") else "momentum" if kind.startswith("mom") else "volatility" if kind == "vol12"
                else "seasonal_anchor" if kind.startswith("ya") else "seasonal_profile")
    if name.startswith(("vac_rate", "seek_rate", "coverage")):
        return "cross_rates"
    if name.startswith("ur"):
        return "unemployment"
    if name.startswith(("portal", "survey", "ncs", "lfs")):
        return "source_channels"
    if name in ("origin_month", "target_month", "target_month_sin", "target_month_cos"):
        return "calendar"
    if name.startswith("cat_"):
        return "identity"
    if name in ("log_pop", "rel_size_E"):
        return "size_context"
    if name.startswith("wage"):
        return "wages"
    if name in ("female_pct", "female_rel", "grad_pct", "youth_pct"):
        return "demographics"
    if name in ("seats_per_kpop", "seats_rel", "seat_to_vac", "seat_to_vac_dev12", "cert_to_vac"):
        return "training"
    if name in ("post_covid", "eshram_progress"):
        return "regime"
    raise KeyError(name)


def feature_catalogue(OF, X):
    """One row per candidate feature: group, whether it is a time proxy (kept out of the model inputs), whether it depends on the horizon and its first month."""
    rows = []
    hor = {"horizon", "origin_month", "target_month", "target_month_sin", "target_month_cos"} | {f"{k}_{s}" for k in KEYS for s in ("ya_h", "yadrift_h", "sf_shift")}
    names = list(OF) + [c for c in X.columns if c not in OF]
    for n in names:
        first = ""
        if n in OF:
            nn = np.where(~np.isnan(OF[n]).all(axis=0))[0]
            first = str(C.MONTHS[int(nn[0])]) if len(nn) else ""
        rows.append({"feature": n, "group": group_of(n), "time_proxy": n in TIME_PROXY_FEATURES, "depends_on_horizon": n in hor, "first_available_month": first})
    return pd.DataFrame(rows)
