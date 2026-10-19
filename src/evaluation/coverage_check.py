#!/usr/bin/env python3
"""
Coverage audit: are all 280 series (56 districts x 5 sectors, 4 states, 16 tiers) present in the panel, the three split files, the training rows of each model,
the scored test rows and the saved predictions?  Writes reports/evaluation/coverage_audit.json and prints a summary.   Run: python src/evaluation/coverage_check.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training", "evaluation"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
import opt_lib as ol  # noqa: E402


def main():
    dim = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str})
    R = {"dim_series": {"series": int(dim.Series_ID.nunique()), "districts": int(dim.District_LGD_Code.nunique()), "states": int(dim.State_Name.nunique()), "tiers": int(dim.Econ_Tier.nunique()),
                        "sectors": int(dim.Sector_Name.nunique()), "series_per_district": sorted(dim.groupby("District_LGD_Code").size().unique().tolist()),
                        "states_list": sorted(dim.State_Name.unique()), "districts_per_state": dim.groupby("State_Name").District_LGD_Code.nunique().to_dict()}}
    allser = set(dim.Series_ID)
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date"])
    R["panel"] = {"series": int(panel.Series_ID.nunique()), "months_per_series": sorted(panel.groupby("Series_ID", observed=True).size().unique().tolist()), "missing_series": sorted(allser - set(panel.Series_ID.astype(str)))}
    splits = {}
    for n in sp.NAMES:
        d = sp.load_split(n, unlock_test=True, verify=True, columns=["Series_ID", "horizon", "target_idx"])
        g = d.groupby("Series_ID").size()
        splits[n] = {"series": int(g.size), "missing": sorted(allser - set(g.index)), "rows_per_series_min": int(g.min()), "rows_per_series_max": int(g.max()), "horizons": sorted(d.horizon.unique().tolist())}
    R["splits"] = splits
    train_rows = {}
    for k in "EVS":
        cols = ol.columns(k)
        tr = pd.concat([sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols)])
        used = ld.train_rows(tr, k)
        g = used.groupby("Series_ID").size()
        train_rows[k] = {"series_with_training_rows": int(g.size), "missing": sorted(allser - set(g.index)), "min_rows": int(g.min()), "max_rows": int(g.max()), "rows_removed_by_shock_policy": int(len(tr) - len(used))}
    R["training_rows_after_policy"] = train_rows
    pred = pd.read_parquet(ROOT / "data" / "interim" / "phase8_test_predictions.parquet")
    ev = {}
    for k in "EVS":
        p = pred[pred.target == k]
        s = p[~p.shock]
        mods = ["primary", "cv_blend", "v1_refit", "hgb", "last_plus_seasonal_shift"]
        ev[k] = {"series_with_predictions": int(p.Series_ID.nunique()), "series_scored": int(s.Series_ID.nunique()), "scored_rows": int(len(s)), "rows_not_scored": int(len(p) - len(s)),
                 "series_with_unscored_rows": int(p[p.shock].Series_ID.nunique()), "nan_or_inf_predictions": int((~np.isfinite(p[mods].to_numpy())).sum()),
                 "horizons_per_series_min": int(s.groupby("Series_ID").horizon.nunique().min()), "districts_scored": int(s.merge(dim[["Series_ID", "District_LGD_Code"]], on="Series_ID").District_LGD_Code.nunique()),
                 "tiers_scored": int(s.Econ_Tier.nunique()), "sectors_scored": int(s.sector.nunique()), "states_scored": int(s.state.nunique())}
    R["test_evaluation"] = ev
    R["forecast_file"] = {"exists": any((ROOT / "outputs").rglob("forecast*.parquet")) or any((ROOT / "outputs").glob("forecast*.csv")),
                          "note": "no forecast beyond the data (after 2026-12) and no flag file has been produced yet; the evaluation forecasts are in-sample-period test forecasts"}
    json.dump(R, open(ROOT / "reports" / "evaluation" / "coverage_audit.json", "w"), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
