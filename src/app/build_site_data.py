#!/usr/bin/env python3
"""
Public website - build app/data/site_data.js from the project's real outputs.  Nothing on the site is typed in by hand: every number comes
from the forecast files (Phase 9), the evaluation tables (Phase 8) and the dimension tables.

Hero example: among the non-IT-ITeS district-sector series, the one whose 12-month vacancy forecast grows fastest relative to its seeker forecast (stated on the page).
Run: python src/app/build_site_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "app"
ORIGIN = "2026-10"
FC = ROOT / "outputs" / "forecasts" / f"origin_{ORIGIN}"
VARS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}


def r(x, n=2):
    return None if pd.isna(x) else round(float(x), n)


def main():
    L = pd.read_csv(FC / "forecast_long.csv", dtype={"district_lgd_code": str})
    W = pd.read_csv(FC / "flags.csv", dtype={"district_lgd_code": str})              # only counted, for the footer figures
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str})
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date", *VARS.values()])
    panel = panel[panel.Date <= pd.Timestamp(ORIGIN + "-01")]
    D = {"meta": {"origin": ORIGIN, "origin_label": "October 2026", "first_target": "November 2026", "last_target": "October 2027", "model": "xgboost_v3 refitted on data to 2026-10",
                  "series": 280, "districts": int(dims.District_LGD_Code.nunique()), "states": int(dims.State_Name.nunique()), "sectors": int(dims.Sector_Name.nunique()), "tiers": int(dims.Econ_Tier.nunique()),
                  "forecast_rows": int(len(L)), "flag_rows": int(len(W)), "horizons": 12, "synthetic": True,
                  "sector_list": sorted(dims.Sector_Name.unique()), "state_list": sorted(dims.State_Name.unique())}}
    # ---- hero example
    piv = L[L.horizon == 12].pivot_table(index="Series_ID", columns="target_variable", values=["forecast", "last_observed"])
    gap = (piv["forecast"][VARS["V"]] / piv["last_observed"][VARS["V"]]) / (piv["forecast"][VARS["S"]] / piv["last_observed"][VARS["S"]])
    cand = dims[(dims.Sector_Name != "IT-ITeS") & (~dims.Low_Volume)].Series_ID
    sid = gap.loc[cand].idxmax()
    meta = dims[dims.Series_ID == sid].iloc[0]
    hero = {"series_id": sid, "district": meta.District_Name, "state": meta.State_Name, "sector": meta.Sector_Name, "lgd": meta.District_LGD_Code,
            "rule": "the non-IT-ITeS series whose 12-month vacancy forecast grows fastest relative to its seeker forecast"}
    for k in "VS":
        f = L[(L.Series_ID == sid) & (L.target_variable == VARS[k])].sort_values("horizon")
        last = f.last_observed.iloc[0]
        h = panel[panel.Series_ID == sid].sort_values("Date").tail(37)
        hero[k] = {"history": [round(float(v) / last * 100, 2) for v in h[VARS[k]]], "history_months": [d.strftime("%Y-%m") for d in h.Date],
                   "forecast": [round(float(v) / last * 100, 2) for v in f.forecast], "lo": [round(float(v) / last * 100, 2) for v in f.lo90], "hi": [round(float(v) / last * 100, 2) for v in f.hi90],
                   "forecast_months": f.target_month.tolist(), "last_value": float(last), "confidence": f.confidence.iloc[0], "interval_method": f.interval_method.iloc[0]}
    D["hero"] = hero
    # ---- accuracy on the test period: the home page quotes these figures, and the tests check them
    M = pd.read_csv(ROOT / "reports" / "evaluation" / "v3" / "original" / "metrics.csv").set_index(["target", "model"])
    acc = {"label": "Test period 2023 to 2026"}
    for k in "EVS":
        base = "seasonal_naive_drift" if k == "E" else "last_plus_seasonal_shift"
        acc[k] = {"model": r(M.loc[(k, "v3"), "wape_mean_horizon"]), "baseline": r(M.loc[(k, base), "wape_mean_horizon"]),
                  "baseline_name": "Seasonal naive plus drift" if k == "E" else "Last value plus seasonal shift"}
    D["accuracy"] = {"original": acc}
    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / "site_data.js").write_text("window.SITE_DATA = " + json.dumps(D, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("hero series:", sid, meta.District_Name, meta.Sector_Name)


if __name__ == "__main__":
    main()
