#!/usr/bin/env python3
"""
v4 phase 8 - build app/data/site_data.js (window.SITE_DATA) for the public pages from the project's real outputs.  Nothing on the site is typed in by hand
except prose; every figure the pages quote is checked against this file (or the tables it is read from) by tests/test_v4_site.py.

Reads   data/v4/DATA_MANIFEST.json, dim_series.csv, FORECAST_MANIFEST.json, exports/forecast_series.parquet, exports/forecast_rollups.csv.gz, exports/capacity_gap_*.csv,
        raw/trade_monthly (history of the hero example), reports/v4/evaluation/*.csv
Writes  app/data/site_data.js
Hero    one district-trade series, shown as an example: among the larger series with a medium-confidence 12-month vacancy forecast (the best label vacancy forecasts earn), the one whose 60-month vacancy forecast
        grows fastest relative to its seeker forecast.  Vacancies and seekers are drawn as an index (last observed month = 100) with the usual 90% range.

Run: python src/v4/build_site_data.py
"""
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import config as C

ROOT = C.ROOT
OUT = ROOT / "app" / "data" / "site_data.js"
EV = C.REPORTS / "evaluation"
EXP = C.DATA / "exports"
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def long_month(ym):
    y, m = ym.split("-")
    return f"{MONTHS_LONG[int(m) - 1]} {y}"


def r(x, n=2):
    return None if pd.isna(x) else round(float(x), n)


def accuracy():
    out = {}
    for name, f in (("test", "test_metrics.csv"), ("stress", "stress_metrics.csv")):
        m = pd.read_csv(EV / f)
        m = m[(m.slice == "all") & (m.band == "all horizons")].set_index("target")
        out[name] = {k: {"model": r(m.loc[k, "wape_model"]), "baseline": r(m.loc[k, "wape_best_baseline"]), "gain_pct": r(m.loc[k, "improvement_vs_best_baseline_pct"], 1), "bias_pct": r(m.loc[k, "bias_pct"], 1)} for k in "EVS"}
    t = pd.read_csv(EV / "test_metrics.csv")
    bands = t[(t.slice == "all") & (t.band != "all horizons")]
    out["test_by_band"] = {k: {b: r(g.loc[g.band == b, "improvement_vs_best_baseline_pct"].iloc[0], 1) for b in g.band} for k, g in bands.groupby("target")}
    fw = pd.read_csv(EV / "fresh_worlds.csv")
    fw = fw[fw.band == "all horizons"]
    out["fresh"] = {int(s): {k: {"model": r(g.loc[g.target == k, "wape_model"].iloc[0]), "baseline": r(g.loc[g.target == k, "wape_best_baseline"].iloc[0])} for k in "EVS"} for s, g in fw.groupby("world_seed")}
    c = pd.read_csv(EV / "interval_coverage.csv")
    c = c[(c.slice == "all") & (c.calibration == "forward")]
    out["coverage"] = {w: {k: r(g.loc[g.target == k, "coverage"].iloc[0], 3) for k in "EVS"} for w, g in c.groupby("window")}
    p = pd.read_csv(EV / "flag_precision.csv")
    p = p[(p.window == "test") & (p.source == "model") & (p.volume == "all") & (p.band == "1-12") & p.flag.isin(["Shortage alert", "Oversupply alert"])]
    out["alerts"] = {row.flag: {"precision": r(row.precision_decile, 3), "base_rate": r(row.base_rate_decile, 3), "lift": r(row.lift_decile, 1)} for row in p.itertuples()}
    return out


def headline(fc):
    rl = pd.read_csv(EXP / "forecast_rollups.csv.gz", low_memory=False)
    ind = rl[rl.level == "india"].set_index("horizon")
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Date", "Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"])
    now = raw[raw.Date == "2025-12-01"][["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"]].sum()
    out = {"now": {"E": int(now.iloc[0]), "V": int(now.iloc[1]), "S": int(now.iloc[2])}}
    for h in (12, 60):
        row = ind.loc[h]
        out[f"h{h}"] = {k: {"point": int(row[k]), "usual": [int(row[f"{k}_lo"]), int(row[f"{k}_hi"])], "wide": [int(row[f"{k}_lo_wide"]), int(row[f"{k}_hi_wide"])]} for k in "EVS"}
        out[f"h{h}"]["DI"] = float(row.DI)
    sec = pd.read_csv(EXP / "capacity_gap_sector.csv")
    out["capacity"] = {s: {int(y): {"openings_per_seat": r(g.loc[g.year == y, "openings_per_seat"].iloc[0]), "supply_per_opening": r(g.loc[g.year == y, "supply_per_opening"].iloc[0])} for y in (2026, 2030)} for s, g in sec.groupby("Sector_Name")}
    ser = pd.read_parquet(EXP / "capacity_series.parquet", columns=["year", "status"])
    out["capacity_status_2030"] = {k: r(v, 3) for k, v in ser[ser.year == 2030].status.value_counts(normalize=True).items()}
    al = pd.read_csv(EXP / "flag_alerts.csv")
    out["alerts_12m"] = {"shortage": int(((al.flag == "Shortage alert") & (al.horizon == 12)).sum()), "oversupply": int(((al.flag == "Oversupply alert") & (al.horizon == 12)).sum())}
    return out


def hero(fc, dim):
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Series_ID", "Date", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Total_Employed_Workers"])
    last = raw[raw.Date == "2025-12-01"].set_index("Series_ID")
    big = last.Total_Employed_Workers >= last.Total_Employed_Workers.median()
    f12 = fc[fc.horizon == 12].set_index("Series_ID")
    f60 = fc[fc.horizon == 60].set_index("Series_ID")
    ok = big & (f12.V_confidence.reindex(last.index) == "Medium") & (last.Active_Job_Vacancies > 0) & (last.eShram_Registered_Seekers > 0)
    score = (f60.V / last.Active_Job_Vacancies) / (f60.S / last.eShram_Registered_Seekers)
    sid = score[ok.reindex(score.index).fillna(False)].idxmax()
    meta = dim[dim.Series_ID == sid].iloc[0]
    f = fc[fc.Series_ID == sid].sort_values("horizon")
    h = raw[raw.Series_ID == sid].sort_values("Date").tail(37)
    out = {"series_id": sid, "district": meta.District_Name, "state": meta.State_Name, "sector": meta.Trade_Name, "sector_name": meta.Sector_Name, "trade_code": meta.Trade_Code, "lgd": str(meta.District_LGD_Code),
           "rule": "the larger district-trade series with a medium-confidence 12-month vacancy forecast whose 60-month vacancy forecast grows fastest relative to its seeker forecast"}
    for k, col in (("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers")):
        base = float(last.loc[sid, col])
        idx = lambda a: [round(float(v) / base * 100, 2) for v in a]
        out[k] = {"history": idx(h[col]), "history_months": [d.strftime("%Y-%m") for d in h.Date], "forecast": idx(f[k]), "lo": idx(f[f"{k}_lo"]), "hi": idx(f[f"{k}_hi"]), "forecast_months": f.month.tolist(),
                  "last_value": base, "confidence": f[f"{k}_confidence"].iloc[11].lower(), "interval_method": "usual 90% range from split-conformal calibration on 2010-2019"}
    return out


def main():
    man = json.loads((C.DATA / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
    fman = json.loads((C.DATA / "FORECAST_MANIFEST.json").read_text(encoding="utf-8"))
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    fc = pd.read_parquet(EXP / "forecast_series.parquet")
    trades = [{"c": c, "n": n, "s": s} for c, n, s in dim.drop_duplicates("Trade_Code")[["Trade_Code", "Trade_Name", "Sector_Name"]].itertuples(index=False)]
    per_state = dim.groupby("State_Name").District_LGD_Code.nunique().to_dict()
    n_cols = len(pq.read_schema(C.DATA / "raw" / "trade_monthly_2000_2025.parquet").names)
    D = {"meta": {"origin": C.ORIGIN, "origin_label": long_month(C.ORIGIN), "first_target": long_month("2026-01"), "last_target": long_month("2030-12"), "model": "xgboost_v4 direct multi-horizon, final fit on data to 2025-12",
                  "series": int(man["series"]), "districts": int(man["districts"]), "states": int(man["states"]), "sectors": int(man["sectors"]), "trades": int(man["trades"]), "horizons": 60,
                  "rows": int(man["rows"]), "months": int(man["months"]), "columns": int(n_cols), "first_month": man["first_month"], "last_month": man["last_month"],
                  "forecast_rows": int(len(fc)), "synthetic": True, "sector_list": sorted(dim.Sector_Name.unique()), "state_list": sorted(dim.State_Name.unique()), "districts_by_state": per_state,
                  "trade_list": trades, "data_sha256": man["content_sha256"], "forecast_generated": fman["generated_at_utc"]},
         "headline": headline(fc), "hero": hero(fc, dim), "accuracy": accuracy()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.SITE_DATA = " + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")
    h = D["hero"]
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.1f} KB); hero: {h['district']}, {h['sector']} ({h['state']}); V {h['V']['forecast'][-1]:.0f}, S {h['S']['forecast'][-1]:.0f} at 2030-12")


if __name__ == "__main__":
    main()
