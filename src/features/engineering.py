"""
Phase 5 - leak-safe feature engineering for the LMIS forecasting problem.

One training example = one (series, forecast origin t, horizon h).  Every feature is computed from data at or before
month t only: trailing windows, expanding statistics and cross-sections at t; no centred windows, no future values.
The only things taken from after t are the target (log level at t+h) and the calendar month of t+h (known in advance).

Panels are loaded by the caller through src/common/data_access.load_panel, so the locked test period cannot enter by accident.
"""
import warnings

import numpy as np
import pandas as pd

HORIZONS = list(range(1, 13))
MIN_ORIGIN = 36                        # origins need 36 months of history (mom36, seasonal profile)
TARGET_KEYS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
COVID_FIRST, COVID_LAST = pd.Timestamp("2020-03-01"), pd.Timestamp("2022-02-01")
POLICY_SPANS = [(pd.Timestamp("2016-11-01"), pd.Timestamp("2017-01-01")), (pd.Timestamp("2017-07-01"), pd.Timestamp("2017-10-01"))]
ESHRAM_FIRST, ESHRAM_LAST = pd.Timestamp("2021-08-01"), pd.Timestamp("2023-02-01")
# Features that are (near) monotone functions of calendar time.  Trees cannot extrapolate them, and they let a model memorise
# "what year it is" instead of learning economics, so they are excluded from the candidate pool (audit: reports/features/time_proxy_audit.csv).
# Detrended replacements are provided: wage_rel, rel_size_E, seats_rel, female_rel and the dev12 / mom12 versions of the rates.
TIME_PROXY_FEATURES = {"log_pop", "wage_log", "seats_per_kpop", "female_pct", "seek_rate", "coverage", "post_covid", "eshram_progress"}
CAT_COLS = {"cat_sector": "Sector_Name", "cat_tier": "Econ_Tier", "cat_state": "State_Name", "cat_district": "District_Name"}


class PanelData:
    """Series x month arrays built from a processed-panel DataFrame (output of load_panel)."""

    def __init__(self, df):
        df = df.copy()
        for c in ("Series_ID", "Sector_Name", "Econ_Tier", "State_Name", "District_Name"):
            df[c] = df[c].astype(str)
        self.sid = sorted(df.Series_ID.unique())
        self.dates = pd.DatetimeIndex(sorted(df.Date.unique()))
        self.T = len(self.dates)
        piv = lambda col: df.pivot(index="Series_ID", columns="Date", values=col).loc[self.sid].to_numpy(float)
        self.X = {k: piv(v) for k, v in TARGET_KEYS.items()}
        self.L = {k: np.log(v) for k, v in self.X.items()}
        self.aux = {c: piv(c) for c in ["Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "District_Total_Population_Est", "Training_Seats_Sanctioned",
                                        "Trainees_Certified_Monthly", "Female_Share_Pct", "Edu_Graduate_and_Above_Pct", "Age_15_24_Pct"]}
        self.meta = df.drop_duplicates("Series_ID").set_index("Series_ID").loc[self.sid][["Sector_Name", "Econ_Tier", "State_Name", "District_Name"]]
        self.sector = self.meta.Sector_Name.to_numpy()
        d = self.dates
        self.covid = (d >= COVID_FIRST) & (d <= COVID_LAST)
        self.policy = np.zeros(self.T, bool)
        for lo, hi in POLICY_SPANS:
            self.policy |= (d >= lo) & (d <= hi)
        self.ramp = (d >= ESHRAM_FIRST) & (d <= ESHRAM_LAST)
        self.months0 = ((d.year - 2011) * 12 + d.month - 1).to_numpy()
        assert (self.months0 == np.arange(self.T) + self.months0[0]).all()
        self.t_offset = int(self.months0[0])             # calendar months since 2011-01 of column 0 (0 for the full panel)


def roll_mean(a, w):
    return pd.DataFrame(a.T).rolling(w, min_periods=w).mean().to_numpy().T


def roll_std(a, w):
    return pd.DataFrame(a.T).rolling(w, min_periods=w).std().to_numpy().T


def lagdiff(a, k):
    out = np.full_like(a, np.nan)
    out[:, k:] = a[:, k:] - a[:, :-k]
    return out


def seasonal_profile(D, k):
    """(series, origin t, calendar month) seasonal factors using only observations up to t.

    r_s = log x_s - mean(log x over s-12..s-1) (a trailing quantity); months whose 13-month window touches a shock are dropped;
    the profile for month m at origin t is the mean of r_s over s <= t with month m (at least 2 observations), centred over months."""
    L = D.L[k]
    prev12 = roll_mean(np.concatenate([np.full((L.shape[0], 1), np.nan), L[:, :-1]], axis=1), 12)
    r = L - prev12
    shock = D.covid | D.policy | (D.ramp if k == "S" else np.zeros(D.T, bool))
    touched = pd.Series(shock.astype(int)).rolling(13, min_periods=1).sum().to_numpy() > 0
    r[:, touched] = np.nan
    mon = D.dates.month.to_numpy() - 1
    prof = np.full((L.shape[0], D.T, 12), np.nan)
    for m in range(12):
        sel = mon == m
        v = np.where(sel[None, :] & ~np.isnan(r), r, 0.0)
        n = np.cumsum(sel[None, :] & ~np.isnan(r), axis=1)
        prof[:, :, m] = np.where(n >= 2, np.cumsum(v, axis=1) / np.maximum(n, 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)               # all-NaN early origins
        prof -= np.nanmean(prof, axis=2, keepdims=True)
    prof[np.isnan(prof).any(axis=2)] = np.nan
    return prof


def origin_features(D):
    """Features that depend on the origin only.  Returns {name: (series, T) array}."""
    F = {}
    for k in "EVS":
        L = D.L[k]
        m3, m6, m12 = roll_mean(L, 3), roll_mean(L, 6), roll_mean(L, 12)
        F[f"{k}_dev0_3"], F[f"{k}_dev0_12"] = L - m3, L - m12
        F[f"{k}_dev3_12"], F[f"{k}_dev6_12"] = m3 - m12, m6 - m12
        for lag in (1, 3, 6, 12, 36):
            F[f"{k}_mom{lag}"] = lagdiff(L, lag)
        F[f"{k}_vol12"] = roll_std(lagdiff(L, 1), 12)
    rates = {"vac_rate": D.L["V"] - D.L["E"], "seek_rate": D.L["S"] - D.L["E"], "coverage": D.L["V"] - D.L["S"]}
    for name, a in rates.items():
        F[name], F[f"{name}_dev12"], F[f"{name}_mom12"] = a, a - roll_mean(a, 12), lagdiff(a, 12)
    ur = D.aux["Unemployment_Rate_Pct"]
    F["ur"], F["ur_chg3"], F["ur_chg12"] = ur, lagdiff(ur, 3), lagdiff(ur, 12)
    # sector-wide aggregates (sums over all districts in the sector at each month)
    for k in "EVS":
        agg = np.zeros_like(D.L[k])
        for s in np.unique(D.sector):
            m = D.sector == s
            tot = np.log(D.X[k][m].sum(axis=0))
            row = np.vstack([lagdiff(tot[None, :], 3), lagdiff(tot[None, :], 12), (tot - roll_mean(tot[None, :], 12)[0])[None, :]])
            for name, r_ in zip(("mom3", "mom12", "dev12"), row):
                F.setdefault(f"sec_{k}_{name}", np.full_like(D.L[k], np.nan))[m] = r_
    pop = D.aux["District_Total_Population_Est"]
    F["log_pop"] = np.log(pop)
    wl = np.log(D.aux["Avg_Monthly_Wage_INR"])
    secmean = np.zeros_like(wl)
    secmean_E = np.zeros_like(wl)
    for s in np.unique(D.sector):
        m = D.sector == s
        secmean[m], secmean_E[m] = wl[m].mean(axis=0), D.L["E"][m].mean(axis=0)
    F["wage_log"], F["wage_rel"], F["rel_size_E"] = wl, wl - secmean, D.L["E"] - secmean_E
    F["seats_per_kpop"] = np.log(D.aux["Training_Seats_Sanctioned"] / pop * 1000)
    seat_sec = np.zeros_like(wl)
    fem_sec = np.zeros_like(wl)
    for s in np.unique(D.sector):
        m = D.sector == s
        seat_sec[m] = F["seats_per_kpop"][m].mean(axis=0)
        fem_sec[m] = D.aux["Female_Share_Pct"][m].mean(axis=0)
    F["seats_rel"] = F["seats_per_kpop"] - seat_sec
    F["female_rel"] = D.aux["Female_Share_Pct"] - fem_sec
    cert12 = pd.DataFrame(D.aux["Trainees_Certified_Monthly"].T).rolling(12, min_periods=12).sum().to_numpy().T
    F["cert_to_vac"] = np.log1p(cert12) - D.L["V"]
    F["female_pct"], F["grad_pct"], F["youth_pct"] = D.aux["Female_Share_Pct"], D.aux["Edu_Graduate_and_Above_Pct"], D.aux["Age_15_24_Pct"]
    post = (D.dates >= pd.Timestamp("2022-03-01")).astype(float)
    span = (ESHRAM_LAST.year - ESHRAM_FIRST.year) * 12 + ESHRAM_LAST.month - ESHRAM_FIRST.month + 1      # months in the ramp
    since = (D.dates.year - ESHRAM_FIRST.year) * 12 + D.dates.month - ESHRAM_FIRST.month + 1
    prog = np.clip(since / span, 0, 1)
    F["post_covid"] = np.tile(post, (len(D.sid), 1))
    F["eshram_progress"] = np.tile(prog, (len(D.sid), 1))
    SF = {k: seasonal_profile(D, k) for k in "EVS"}
    mon = D.dates.month.to_numpy() - 1
    for k in "EVS":
        F[f"{k}_sf_origin"] = np.take_along_axis(SF[k], np.tile(mon, (len(D.sid), 1))[:, :, None], axis=2)[:, :, 0]
    return F, SF


def build_examples(D, OF, SF, horizons=(1, 3, 6, 12), origin_min=MIN_ORIGIN, origin_max=None, need_target=True):
    """Stack one row per (series, origin, horizon).  Origins up to origin_max (default: last month with a target)."""
    nS = len(D.sid)
    frames = []
    cal_month = lambda idx: (idx + D.t_offset) % 12
    shock_E = D.covid | D.policy
    shock_S = shock_E | D.ramp
    cs_E, cs_S = np.cumsum(shock_E.astype(int)), np.cumsum(shock_S.astype(int))
    inwin = lambda cs, lo, hi: cs[hi] - (cs[lo - 1] if lo > 0 else 0) > 0
    for h in horizons:
        hi_o = (D.T - 1 - h) if need_target else (D.T - 1)
        if origin_max is not None:
            hi_o = min(hi_o, origin_max)
        t = np.arange(origin_min, hi_o + 1)
        if len(t) == 0:
            continue
        d = {name: arr[:, t].ravel() for name, arr in OF.items()}
        mO, mT = cal_month(t), cal_month(t + h)
        for k in "EVS":
            L = D.L[k]
            d[f"{k}_ya_h"] = (L[:, t + h - 12] - L[:, t]).ravel()
            d[f"{k}_yadrift_h"] = (L[:, t + h - 12] - L[:, t - 12]).ravel()
            d[f"{k}_sf_shift"] = (SF[k][:, t, :][np.arange(nS)[:, None], np.arange(len(t))[None, :], mT[None, :]] -
                                  SF[k][:, t, :][np.arange(nS)[:, None], np.arange(len(t))[None, :], mO[None, :]]).ravel()
            d[f"last_{k}"] = L[:, t].ravel()
            d[f"sm3_{k}"] = roll_mean(L, 3)[:, t].ravel()
            d[f"sm6_{k}"] = roll_mean(L, 6)[:, t].ravel()
            d[f"target_{k}"] = (L[:, t + h].ravel() if need_target else np.full(nS * len(t), np.nan))
        d["horizon"] = np.full(nS * len(t), h)
        d["origin_month"] = np.tile(mO + 1, nS)
        d["target_month"] = np.tile(mT + 1, nS)
        d["target_month_sin"], d["target_month_cos"] = np.sin(2 * np.pi * d["target_month"] / 12), np.cos(2 * np.pi * d["target_month"] / 12)
        d["origin_idx"] = np.tile(t, nS)
        d["target_idx"] = d["origin_idx"] + h
        d["series_row"] = np.repeat(np.arange(nS), len(t))
        d["shock_EV"] = np.array([inwin(cs_E, max(ti - 12, 0), min(ti + h, D.T - 1)) for ti in t])[np.tile(np.arange(len(t)), nS)]
        d["shock_S"] = np.array([inwin(cs_S, max(ti - 12, 0), min(ti + h, D.T - 1)) for ti in t])[np.tile(np.arange(len(t)), nS)]
        for cname, mcol in CAT_COLS.items():
            d[cname] = np.repeat(D.meta[mcol].to_numpy(), len(t))
        d["Series_ID"] = np.repeat(np.array(D.sid), len(t))
        frames.append(pd.DataFrame(d))
    return pd.concat(frames, ignore_index=True)


def make_categorical(df, D):
    for cname, mcol in CAT_COLS.items():
        df[cname] = pd.Categorical(df[cname], categories=sorted(D.meta[mcol].unique()))
    return df


def feature_names(df, include_time_proxies=False):
    skip = set() if include_time_proxies else set(TIME_PROXY_FEATURES)
    skip |= {"origin_idx", "target_idx", "series_row", "shock_EV", "shock_S", "Series_ID"}
    skip |= {c for c in df.columns if c.startswith(("last_", "sm3_", "sm6_", "target_")) and c not in ("target_month", "target_month_sin", "target_month_cos")}
    return [c for c in df.columns if c not in skip]


def group_of(name, target):
    """Feature group (used for ablation and documentation); 'own' = features of the series being forecast."""
    if name == "horizon":
        return "core_horizon"
    if name.startswith("sec_"):
        return "sector_aggregates"
    if name[:2] in ("E_", "V_", "S_"):
        k, kind = name[0], name[2:]
        own = "own_" if k == target else "other_"
        g = ("level_dev" if kind.startswith("dev") else "momentum" if kind.startswith("mom") else "volatility" if kind == "vol12"
             else "seasonal_anchor" if kind.startswith("ya") else "seasonal_profile")
        return own + g
    if name.startswith(("vac_rate", "seek_rate", "coverage")):
        return "cross_rates"
    if name.startswith("ur"):
        return "unemployment"
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
    if name in ("seats_per_kpop", "seats_rel", "cert_to_vac"):
        return "training"
    if name in ("post_covid", "eshram_progress"):
        return "regime"
    raise KeyError(name)
