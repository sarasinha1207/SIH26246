#!/usr/bin/env python3
"""
v4 phase 6 - the Demand Index (0 to 100) of a district-trade and month.

METHOD (written down so that the number can be reproduced and challenged)
  Signals    three demand channels are measured as openings per worker, in logs:  x_c = log((signal_c + 1) / employed workers)
               V      administrative vacancies (all months),
               P      job-portal postings (all months; the portal's share of all openings rises over time, which is why the next step removes the national profile),
               N      National Career Service vacancies (from 2015-07).
             Registered seekers measure supply, not demand, and the labour-force survey estimate measures employment, so neither is in the index; the quarterly hiring survey is an
             index relative to its own series, so it cannot be compared between districts (kept in the data, used by the models as a feature).
  Step 1     position   z_c = standardised x_c among the districts of the same trade in the same month (mean 0, standard deviation 1 across districts), per channel.  This removes every
             national or trade-wide shift in a channel (coverage trends, level changes) and keeps only how the district compares with its peers.
             The composite is the mean of the available z_c, divided by its own standard deviation across districts, so it again has standard deviation 1.
  Step 2     level      L = (log(national vacancies / national employed of the trade) - its mean in the reference period 2018-2019) / (the cross-district standard deviation of log(V/E) in
             that period).  It carries the trade's national demand level in units of the district spread, so that the index rises and falls with demand over time.
  Index      DI = 100 * Phi(composite + L), Phi the standard normal distribution function.  DI = 50 is the median district of the trade at the 2018-2019 national demand level; 84 is one
             standard deviation above it, 16 one below.
  Forecast   the 2026-2030 months use the forecast vacancies and employed workers only (the other channels are measurements of the same openings, not separate forecasts).  The check
             in history: the V-only index against the three-channel index (correlation and mean absolute difference, by year) is in reports/v4/forecast/demand_index_check.json.
  Roll-ups   the index of a state, sector or trade is the employed-worker-weighted mean of the indices of its series.

Run: python src/v4/demand_index.py [--forecast PATH]       (default PATH data/v4/exports/forecast_series.parquet)
"""
import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

import config as C

REF = (216, 239)                              # 2018-01 .. 2019-12
HIST_FROM = 192                               # 2016-01: the first month kept in the export
T_ALL = C.N_MONTHS + 60


def _wide(df, col):
    return df.pivot(index="Series_ID", columns="Date", values=col).sort_index().to_numpy(np.float64)


def zscore_by_trade(x, trade):
    """Standardise x (series, months) across the series of each trade, month by month (NaN-aware)."""
    z = np.full_like(x, np.nan)
    for t in np.unique(trade):
        m = trade == t
        sub = x[m]
        mu, sd = np.nanmean(sub, axis=0), np.nanstd(sub, axis=0)
        z[m] = (sub - mu) / np.where(sd > 0, sd, np.nan)
    return z


def composite(zs, trade):
    """Mean of the available z, rescaled to unit standard deviation across the series of each trade and month."""
    stack = np.stack(zs)
    with np.errstate(all="ignore"):
        comp = np.nanmean(stack, axis=0)
    out = np.full_like(comp, np.nan)
    for t in np.unique(trade):
        m = trade == t
        sd = np.nanstd(comp[m], axis=0)
        out[m] = comp[m] / np.where(sd > 0, sd, np.nan)
    return out


def level_shift(V, E, trade):
    """L per trade and month, shape (series, months): the trade's national log(V/E) relative to the reference period, in units of the reference cross-district spread."""
    L = np.zeros_like(V)
    for t in np.unique(trade):
        m = trade == t
        nat = np.log(V[m].sum(axis=0) / E[m].sum(axis=0))
        x = np.log((V[m] + 1) / E[m])
        sd = np.nanmean(np.nanstd(x[:, REF[0]:REF[1] + 1], axis=0))
        L[m] = ((nat - nat[REF[0]:REF[1] + 1].mean()) / sd)[None, :]
    return L


def build(forecast_path):
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Series_ID", "Date", "Total_Employed_Workers", "Active_Job_Vacancies", "Sig_Portal_Postings", "Sig_NCS_Vacancies"])
    assert (raw.Series_ID.drop_duplicates().to_numpy() == dim.Series_ID.to_numpy()).all()
    E, V = _wide(raw, "Total_Employed_Workers"), _wide(raw, "Active_Job_Vacancies")
    P, N = _wide(raw, "Sig_Portal_Postings"), _wide(raw, "Sig_NCS_Vacancies")
    trade = dim.Trade_Code.to_numpy()
    fc = pd.read_parquet(forecast_path, columns=["series_row", "horizon", "E", "V"])
    Ef = fc.pivot(index="series_row", columns="horizon", values="E").sort_index().to_numpy(np.float64)
    Vf = fc.pivot(index="series_row", columns="horizon", values="V").sort_index().to_numpy(np.float64)
    E_all, V_all = np.hstack([E, Ef]), np.hstack([V, Vf])
    L = level_shift(V_all, E_all, trade)
    zV = zscore_by_trade(np.log((V_all + 1) / E_all), trade)
    nan_f = np.full((len(dim), 60), np.nan)
    zP = zscore_by_trade(np.hstack([np.log((P + 1) / E), nan_f]), trade)
    zN = zscore_by_trade(np.hstack([np.log((N + 1) / E), nan_f]), trade)
    full = composite([zV, zP, zN], trade)                       # history: three channels; forecast months: V only (the others are NaN there)
    v_only = composite([zV], trade)
    di_full, di_v = 100 * ndtr(full + L), 100 * ndtr(v_only + L)
    check = {}
    for y in range(2012, 2026):
        a, b = di_full[:, (y - 2000) * 12:(y - 2000) * 12 + 12].ravel(), di_v[:, (y - 2000) * 12:(y - 2000) * 12 + 12].ravel()
        check[y] = {"correlation": round(float(np.corrcoef(a, b)[0, 1]), 4), "mean_abs_difference": round(float(np.abs(a - b).mean()), 2), "channels_in_three_channel_index": 2 + int(y >= 2016)}
    return dim, di_full, di_v, E_all, check


def main():
    warnings.filterwarnings("ignore", message="(Mean of empty slice|Degrees of freedom)")       # forecast months have no portal or NCS values
    ap = argparse.ArgumentParser()
    ap.add_argument("--forecast", default=str(C.DATA / "exports" / "forecast_series.parquet"))
    ap.add_argument("--out", default=str(C.DATA / "exports"))
    a = ap.parse_args()
    dim, di_full, di_v, E_all, check = build(a.forecast)
    n, T = di_full.shape
    idx = np.arange(HIST_FROM, T)
    di = np.where(np.arange(T)[None, :] < C.N_MONTHS, di_full, di_v)[:, HIST_FROM:]
    months = pd.period_range("2000-01", "2030-12", freq="M")[HIST_FROM:].astype(str)
    out = pd.DataFrame({"series_row": np.repeat(np.arange(n), len(idx)).astype(np.int32), "month": np.tile(months, n), "DI": np.round(di.ravel(), 1).astype(np.float32),
                        "DI_vacancy_only": np.round(di_v[:, HIST_FROM:].ravel(), 1).astype(np.float32), "forecast": np.tile(idx >= C.N_MONTHS, n)})
    assert out.DI.notna().all()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    out.to_parquet(Path(a.out) / "demand_index.parquet", index=False)
    (C.REPORTS / "forecast").mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "forecast" / "demand_index_check.json").write_text(json.dumps({"reference_period": "2018-01 to 2019-12", "v_only_vs_three_channels_by_year": check}, indent=2), encoding="utf-8")
    print(f"{len(out):,} rows; 2025 correlation V-only vs three channels", check[2025])


if __name__ == "__main__":
    main()
