#!/usr/bin/env python3
"""
v4 phase 6 - capacity gap: forecast demand for trained workers against training seats, per district-trade and year (2026-2030).

Inputs per series
    avg_vacancies        mean of the 12 monthly vacancy forecasts of the calendar year (openings to be filled)
    seats                the annual seats sanctioned in the financial year 2025-26 (December 2025 stock), HELD FLAT: an assumption, since no seat plans are forecast
    expected_certified   seats * certification rate, the rate being the median over 2023-2025 of (trainees certified in the calendar year / seats), capped at 1.2
Measures
    openings_per_seat    avg_vacancies / seats                       (absolute: how many forecast openings each seat has to serve in a year; a stock against a flow, so read it as a ranking)
    supply_per_opening   expected_certified / avg_vacancies          (below 1: fewer trainees certified in a year than openings)
    mismatch             log[(seat share of the district in its trade) / (vacancy share of the district in its trade)]  across the 317 districts (relative; as in v3)
    status               mismatch < -0.5  "Seats fall short of demand"      mismatch > +0.5  "Seats exceed demand"      otherwise "Balanced"
The relative measure says where capacity is placed badly compared with where the openings are; the absolute ones say how stretched the capacity is.  Aggregates (state, sector, trade,
state-sector, state-trade) add seats, expected certified and vacancies and recompute the ratios.

Run: python src/v4/capacity.py [--forecast PATH] [--out DIR]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import config as C

SHORT, SURPLUS = -0.5, 0.5
YEARS = list(range(2026, 2031))
AGG = {"series": ["Series_ID"], "state_sector": ["State_Name", "Sector_Name"], "state_trade": ["State_Name", "Trade_Code"], "state": ["State_Name"], "sector": ["Sector_Name"], "trade": ["Trade_Code"], "india": []}


def status_of(mismatch):
    return np.where(mismatch < SHORT, "Seats fall short of demand", np.where(mismatch > SURPLUS, "Seats exceed demand", "Balanced"))


def series_capacity(fc, dim):
    """One row per series and year with the measures above."""
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Series_ID", "Date", "Training_Seats_Sanctioned", "Trainees_Certified_Monthly"])
    seats = raw[raw.Date == "2025-12-01"].set_index("Series_ID").Training_Seats_Sanctioned
    r = raw[raw.Date.dt.year.isin([2023, 2024, 2025])]
    cert = r.groupby(["Series_ID", r.Date.dt.year]).Trainees_Certified_Monthly.sum().unstack()
    st = r.groupby(["Series_ID", r.Date.dt.year]).Training_Seats_Sanctioned.last().unstack()
    rate = (cert / st).median(axis=1).clip(0, 1.2)
    f = fc.assign(year=fc.month.str[:4].astype(int)).groupby(["Series_ID", "year"]).V.mean().rename("avg_vacancies").reset_index()
    f["seats"] = seats.reindex(f.Series_ID).to_numpy()
    f["expected_certified"] = f.seats * rate.reindex(f.Series_ID).to_numpy()
    return f.merge(dim[["Series_ID", "State_Name", "District_LGD_Code", "District_Name", "Sector_Name", "Trade_Code", "Trade_Name"]], on="Series_ID")


def with_measures(f):
    f = f.copy()
    f["openings_per_seat"] = f.avg_vacancies / f.seats
    f["supply_per_opening"] = f.expected_certified / f.avg_vacancies
    return f


def capacity_tables(fc, dim):
    s = series_capacity(fc, dim)
    s["seat_share"] = s.seats / s.groupby(["Trade_Code", "year"]).seats.transform("sum")
    s["vacancy_share"] = s.avg_vacancies / s.groupby(["Trade_Code", "year"]).avg_vacancies.transform("sum")
    s["mismatch"] = np.log(s.seat_share / s.vacancy_share)
    s["status"] = status_of(s.mismatch)
    s = with_measures(s)
    tabs = {"series": s}
    for level, cols in AGG.items():
        if level == "series":
            continue
        g = s.groupby(cols + ["year"])[["avg_vacancies", "seats", "expected_certified"]].sum().reset_index() if cols else s.groupby("year")[["avg_vacancies", "seats", "expected_certified"]].sum().reset_index()
        tabs[level] = with_measures(g)
    return tabs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forecast", default=str(C.DATA / "exports" / "forecast_series.parquet"))
    ap.add_argument("--out", default=str(C.DATA / "exports"))
    a = ap.parse_args()
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    fc = pd.read_parquet(a.forecast, columns=["Series_ID", "month", "V"])
    tabs = capacity_tables(fc, dim)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    for level, t in tabs.items():
        t.round(4).to_parquet(Path(a.out) / f"capacity_{level}.parquet", index=False)
    s = tabs["series"]
    print({y: s[s.year == y].status.value_counts(normalize=True).round(3).to_dict() for y in (2026, 2030)})


if __name__ == "__main__":
    main()
