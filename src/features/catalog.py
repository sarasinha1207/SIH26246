#!/usr/bin/env python3
"""Writes data/processed/features/feature_catalog.csv: every candidate feature, what it is, and where it was selected."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402

NAME = {"E": "employed workers", "V": "job vacancies", "S": "registered seekers"}


def describe(f):
    if f[:2] in ("E_", "V_", "S_"):
        k, kind = f[0], f[2:]
        n = NAME[k]
        d = {"dev0_3": f"log {n} minus its 3-month mean (a noise proxy)", "dev0_12": f"log {n} minus its 12-month mean",
             "dev3_12": f"3-month mean minus 12-month mean of log {n}", "dev6_12": f"6-month mean minus 12-month mean of log {n}",
             "vol12": f"std of month-on-month log change of {n} over 12 months", "sf_origin": f"seasonal factor of the origin month for {n} (expanding, shock-free)",
             "sf_shift": f"seasonal factor of the target month minus the origin month for {n}",
             "ya_h": f"log {n} in the same month last year (t+h-12) minus now", "yadrift_h": f"log {n} change from t-12 to t+h-12 (last year's growth over the same span)"}
        if kind in d:
            return d[kind]
        if kind.startswith("mom"):
            return f"log change of {n} over the last {kind[3:]} month(s)"
    if f.startswith("sec_"):
        _, k, kind = f.split("_")
        return {"mom3": "3-month", "mom12": "12-month", "dev12": "deviation from 12-month mean of"}[kind] + f" log change of sector-wide {NAME[k]} (all districts)" \
            if kind != "dev12" else f"log sector-wide {NAME[k]} minus its 12-month mean"
    simple = {"vac_rate": "log(vacancies / employed)", "seek_rate": "log(seekers / employed)", "coverage": "log(vacancies / seekers)",
              "ur": "unemployment rate (%)", "ur_chg3": "change in unemployment rate over 3 months", "ur_chg12": "change in unemployment rate over 12 months",
              "log_pop": "log district population (EXCLUDED: calendar-time proxy)", "rel_size_E": "log employed workers minus the sector mean across districts",
              "wage_log": "log average monthly wage (EXCLUDED: calendar-time proxy)", "wage_rel": "log wage minus the sector mean across districts",
              "seats_per_kpop": "log sanctioned training seats per 1,000 residents (EXCLUDED: calendar-time proxy)", "seats_rel": "seats per 1,000 residents (log) minus the sector mean across districts",
              "female_rel": "female share of employment minus the sector mean across districts (pp)", "cert_to_vac": "log(1 + certified trainees, last 12 months) minus log vacancies",
              "female_pct": "female share of employment (%) (EXCLUDED: calendar-time proxy)", "grad_pct": "graduate share of employment (%)", "youth_pct": "share aged 15-24 (%)",
              "post_covid": "1 from 2022-03 onwards (EXCLUDED: calendar regime flag)", "eshram_progress": "0 before 2021-08, rising linearly to 1 by 2023-02 (EXCLUDED: calendar regime flag)",
              "horizon": "forecast horizon in months", "origin_month": "calendar month of the forecast origin", "target_month": "calendar month being forecast",
              "target_month_sin": "sine of the target calendar month", "target_month_cos": "cosine of the target calendar month",
              "cat_sector": "sector", "cat_tier": "district economic tier", "cat_state": "state", "cat_district": "district"}
    simple["seek_rate"] += " (EXCLUDED level: trends with the e-Shram registry)"
    simple["coverage"] += " (EXCLUDED level: trends with the e-Shram registry)"
    for base in ("vac_rate", "seek_rate", "coverage"):
        if f == base + "_dev12":
            return f"{simple[base]} minus its 12-month mean"
        if f == base + "_mom12":
            return f"12-month change in {simple[base]}"
    return simple[f]


def main():
    D = en.PanelData(load_panel("monthly"))
    OF, SF = en.origin_features(D)
    ex = en.build_examples(D, OF, SF, horizons=(1,))
    feats = en.feature_names(ex, include_time_proxies=True)
    sel_path = ROOT / "data" / "processed" / "features" / "feature_sets.json"
    sel = json.load(open(sel_path))["targets"] if sel_path.exists() else {}
    rows = []
    for f in feats:
        fam = en.group_of(f, "E")
        fam = fam.replace("own_", "").replace("other_", "")
        series = f[0] if f[:2] in ("E_", "V_", "S_") else (f.split("_")[1] if f.startswith("sec_") else "")
        rows.append(dict(feature=f, family=fam, series=series, description=describe(f),
                         excluded_time_proxy=f in en.TIME_PROXY_FEATURES,
                         known_at_origin="yes (target month is calendar-only)" if f in ("target_month", "target_month_sin", "target_month_cos") else "yes",
                         horizon_specific=f in ("horizon",) or f.endswith(("_ya_h", "_yadrift_h", "_sf_shift")) or f.startswith("target_month"),
                         **{f"selected_{k}": (f in sel[k]["features"]) if sel else None for k in "EVS"}))
    out = ROOT / "data" / "processed" / "features" / "feature_catalog.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"catalog: {len(rows)} features -> {out}")


if __name__ == "__main__":
    main()
