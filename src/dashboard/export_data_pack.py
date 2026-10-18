#!/usr/bin/env python3
"""
Dashboard data pack: tidy CSV files a dashboard (or an AI building one) can load directly.

Uses only the train + validation period (2011-01 .. 2024-12) through load_panel, so the locked test period (2025-26) and the simulated
Nov-Dec 2026 months are not included.  Adds the Phase 5 relative flags (computed from data up to each month only).

Outputs (data/dashboard/): dim_district.csv, dim_sector.csv, monthly_metrics_2011_2024.csv, data_pack_manifest.json
Run: python src/dashboard/export_data_pack.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(ROOT / "src" / "features"))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402
import flags as fl  # noqa: E402

OUT = ROOT / "data" / "dashboard"
SECTOR_COLOR = {"Manufacturing": "#2a78d6", "Construction": "#eb6834", "IT-ITeS": "#1baf7a", "Healthcare": "#eda100", "Textiles and Apparel": "#e87ba4"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_panel("monthly")
    D = en.PanelData(panel)
    R = fl.relative_flags(D)
    labels = fl.status_labels(R["status_code"])
    cov_month = D.X["V"] / D.X["S"]
    n, T = len(D.sid), D.T
    rows = pd.DataFrame({"Series_ID": np.repeat(D.sid, T), "Date": np.tile(D.dates, n)})
    for name, arr in (("coverage_monthly", cov_month), ("coverage_3m", np.exp(R["coverage_3m_log"])), ("coverage_percentile_in_sector", R["cov_pct"]),
                      ("seat_mismatch_log", R["seat_mismatch"])):
        rows[name] = arr.ravel()
    rows["relative_status"] = labels.ravel()
    rows["absolute_context"] = np.where(np.isnan(rows.coverage_3m), "", fl.absolute_context(rows.coverage_3m.fillna(0)))
    rows.loc[rows.relative_status == "", "relative_status"] = ""
    p = panel.copy()
    p["Series_ID"] = p.Series_ID.astype(str)
    keep = {"Series_ID": "Series_ID", "Date": "Date", "State_Name": "state", "District_Name": "district", "District_LGD_Code": "district_lgd_code",
            "Econ_Tier": "district_tier", "Sector_Name": "sector", "Total_Employed_Workers": "employed", "Active_Job_Vacancies": "vacancies",
            "eShram_Registered_Seekers": "registered_seekers", "Avg_Monthly_Wage_INR": "avg_monthly_wage_inr", "Unemployment_Rate_Pct": "unemployment_rate_pct",
            "Training_Seats_Sanctioned": "training_seats_annual", "Trainees_Certified_Monthly": "trainees_certified", "Female_Share_Pct": "female_share_pct",
            "Edu_Graduate_and_Above_Pct": "graduate_share_pct", "Age_15_24_Pct": "youth_15_24_share_pct", "District_Total_Population_Est": "district_population",
            "Is_Covid_Window": "is_covid_window", "Is_Eshram_Ramp": "is_eshram_ramp"}
    out = p[list(keep)].rename(columns=keep).merge(rows, on=["Series_ID", "Date"], how="left", validate="1:1")
    ds = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv")
    out = out.merge(ds[["Series_ID", "Low_Volume"]].rename(columns={"Low_Volume": "is_low_volume_series"}), on="Series_ID", how="left")
    out["net_gap_persons"] = out.vacancies - out.registered_seekers
    for c in ("state", "district", "district_tier", "sector"):
        out[c] = out[c].astype(str)
    out["Date"] = pd.to_datetime(out.Date).dt.strftime("%Y-%m-%d")
    out = out.sort_values(["Date", "state", "district", "sector"]).reset_index(drop=True)
    assert out.Date.max() == "2024-12-01" and len(out) == 47040
    out.round({"coverage_monthly": 4, "coverage_3m": 4, "coverage_percentile_in_sector": 1, "seat_mismatch_log": 3}).to_csv(OUT / "monthly_metrics_2011_2024.csv", index=False)

    cat = pd.read_csv(ROOT / "data" / "processed" / "dim_district.csv", dtype={"District_LGD_Code": str, "State_LGD_Code": str})
    cat = cat.rename(columns={"District_LGD_Code": "district_lgd_code", "District_Name": "district", "State_Name": "state", "State_LGD_Code": "state_lgd_code",
                              "Econ_Tier": "district_tier", "Pop_2011": "population_2011", "Pop_Growth_Annual": "population_growth_per_year"})
    cat[["state", "state_lgd_code", "district", "district_lgd_code", "district_tier", "population_2011", "population_growth_per_year"]].to_csv(OUT / "dim_district.csv", index=False)
    sec = pd.read_csv(ROOT / "data" / "processed" / "dim_sector.csv", dtype={"NCO_Anchor_Code": str, "NCO_Families": str})
    sec = sec.rename(columns={"Sector_Name": "sector", "Sector_Code": "sector_code", "NIC_Code": "nic_divisions", "NCO_Anchor_Code": "nco_anchor_code",
                              "NCO_Families": "nco_families", "NSQF_Level": "nsqf_levels"})
    sec["chart_color"] = sec.sector.map(SECTOR_COLOR)
    sec.to_csv(OUT / "dim_sector.csv", index=False)
    manifest = {"period": ["2011-01", "2024-12"], "rows": int(len(out)), "series": int(out.Series_ID.nunique()), "districts": int(out.district.nunique()),
                "states": sorted(out.state.unique()), "sectors": sorted(out.sector.unique()),
                "excluded": "2025-01 onward (locked test period) and the simulated months Nov-Dec 2026", "data_is_synthetic": True,
                "relative_status_values": fl.STATUSES, "columns": list(out.columns),
                "map_boundaries": "district_boundaries.geojson (build with src/dashboard/build_boundaries.py; see district_boundaries_provenance.json)"}
    json.dump(manifest, open(OUT / "data_pack_manifest.json", "w"), indent=2)
    print(f"data pack: {len(out):,} rows x {out.shape[1]} columns -> {OUT}")


if __name__ == "__main__":
    main()
