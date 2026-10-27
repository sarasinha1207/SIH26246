#!/usr/bin/env python3
"""
v4 phase 6 - compact exports of the 2026-2030 forecast, rankings, alerts and a manifest with checksums.

Reads (data/v4/exports/): forecast_series.parquet (forecast.py), demand_index.parquet (demand_index.py), capacity_*.parquet (capacity.py); data/v4/aggregate_interval_calibration.csv.
Writes
    forecast_rollups.csv.gz        district-sector, state-sector, state, sector, trade and India forecasts with 90% ranges and the Demand Index   (tracked)
    capacity_gap_<level>.csv       capacity-gap measures by year for state, sector, trade, state-sector, state-trade and India               (tracked)
    flag_alerts.csv                every shortage or oversupply ALERT at 12, 36 and 60 months, with confidence labels                          (tracked)
    rankings.csv                   rankings of trades, districts and state-trade pairs                                                          (tracked)
    capacity_gap_series.csv.gz     the capacity-gap measures of the 7,925 series by year                                                       (tracked)
    shards/<state>.json, shards/index.json   per-state forecast shards for the dashboard (monthly point forecast, usual range, Demand Index, flag)  (git-ignored; copied by the dashboard build)
    ../FORECAST_MANIFEST.json      row counts, sizes and SHA-256 of everything above and of the inputs (models, tuned settings, data manifest)    (tracked)
The series-level table forecast_series.parquet and the series-level Demand Index stay git-ignored (re-created by the forecast pipeline).

Run: python src/v4/exports.py [--dir DIR]       (DIR defaults to data/v4/exports)
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import rollups as RU

FLAG_NAMES = {0: "Shortage alert", 1: "Shortage watch", 2: "None", 3: "Oversupply watch", 4: "Oversupply alert"}
ALERT_HORIZONS = (12, 36, 60)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def demand_index_rollups(di, fc, dim, rolls):
    """Employed-weighted Demand Index of each aggregate and forecast month, appended to the roll-up table as DI."""
    d = di[di.forecast].merge(fc[["series_row", "month", "E"]], on=["series_row", "month"])
    d = d.merge(dim[["State_Name", "District_LGD_Code", "Sector_Name", "Trade_Code"]].reset_index().rename(columns={"index": "series_row"}), on="series_row")
    d["w"] = d.E * d.DI
    out = []
    for level, cols in RU.LEVELS.items():
        keys = cols + ["month"]
        g = d.groupby(keys) if cols else d.groupby("month")
        t = (g.w.sum() / g.E.sum()).rename("DI").round(1).reset_index()
        t.insert(0, "level", level)
        out.append(t)
    di_roll = pd.concat(out, ignore_index=True)
    keys = ["level", "month"] + RU.KEYS
    for c in RU.KEYS:
        if c not in di_roll:
            di_roll[c] = None
    return rolls.merge(di_roll[keys + ["DI"]], on=keys, how="left")


def alerts_table(fc, dim):
    f = fc[fc.horizon.isin(ALERT_HORIZONS) & fc.flag_code.isin([0, 4])].merge(
        dim[["Series_ID", "State_Name", "District_LGD_Code", "District_Name", "Sector_Name", "Trade_Code", "Trade_Name"]], on="Series_ID")
    f["flag"] = f.flag_code.map(FLAG_NAMES)
    cols = ["flag", "horizon", "month", "State_Name", "District_LGD_Code", "District_Name", "Sector_Name", "Trade_Code", "Trade_Name", "Series_ID", "coverage_pct", "V", "S", "V_confidence", "S_confidence"]
    return f[cols].sort_values(["horizon", "flag", "Trade_Code", "coverage_pct"], ascending=[True, True, True, False]).round({"coverage_pct": 1})


def rankings_table(fc, rolls, cap, di, dim):
    rows = []

    def add(kind, df, key_cols, value, ascending, n=10, extra=()):
        for rank, (_, r) in enumerate(df.sort_values(value, ascending=ascending).head(n).iterrows(), 1):
            rows.append({"ranking": kind, "rank": rank, "key": " | ".join(str(r[c]) for c in key_cols), "value": round(float(r[value]), 3), "detail": "; ".join(f"{c}={float(r[c]):.2f}" for c in extra)})

    t = rolls[(rolls.level == "trade")]
    first, last = t[t.month == "2026-12"].set_index("Trade_Code"), t[t.month == "2030-12"].set_index("Trade_Code")
    g = pd.DataFrame({"employed_growth_pct_2026_2030": (last.E / first.E - 1) * 100, "vacancy_growth_pct_2026_2030": (last.V / first.V - 1) * 100}).reset_index()
    add("Trades with the fastest vacancy growth, Dec 2026 to Dec 2030 (%)", g, ["Trade_Code"], "vacancy_growth_pct_2026_2030", False, 10, ["employed_growth_pct_2026_2030"])
    add("Trades with the slowest vacancy growth, Dec 2026 to Dec 2030 (%)", g, ["Trade_Code"], "vacancy_growth_pct_2026_2030", True, 10, ["employed_growth_pct_2026_2030"])
    ct = cap["trade"][cap["trade"].year == 2030]
    add("Trades where trained supply is most stretched in 2030 (certified per opening)", ct, ["Trade_Code"], "supply_per_opening", True, 10, ["openings_per_seat"])
    cs = cap["state_trade"][cap["state_trade"].year == 2030]
    add("State-trade pairs where trained supply is most stretched in 2030 (certified per opening)", cs, ["State_Name", "Trade_Code"], "supply_per_opening", True, 15, ["openings_per_seat"])
    add("State-trade pairs with the most surplus training capacity in 2030 (certified per opening)", cs, ["State_Name", "Trade_Code"], "supply_per_opening", False, 15, ["openings_per_seat"])
    s30 = di[di.month.str[:4] == "2030"].groupby("series_row").DI.mean().rename("DI_2030").reset_index().merge(dim.reset_index().rename(columns={"index": "series_row"}), on="series_row")
    for sec, sub in s30.groupby("Sector_Name"):
        d = sub.groupby(["State_Name", "District_Name"]).apply(lambda x: pd.Series({"DI_2030": x.DI_2030.mean()}), include_groups=False).reset_index()
        add(f"Districts with the highest Demand Index in 2030: {sec}", d, ["District_Name", "State_Name"], "DI_2030", False, 10)
    return pd.DataFrame(rows)


def shards(fc, di, dim, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    months = list(C.FORECAST_MONTHS.astype(str))
    f = fc.merge(di[di.forecast][["series_row", "month", "DI"]], on=["series_row", "month"]).sort_values(["series_row", "horizon"])
    info = {}
    for st, sdim in dim.groupby("State_Name"):
        rows = sdim.index.to_numpy()
        sub = f[f.series_row.isin(rows)]
        series = []
        for sid, g in sub.groupby("series_row", sort=True):
            r = dim.loc[sid]
            series.append({"id": r.Series_ID, "d": int(r.District_LGD_Code), "t": r.Trade_Code, "E": g.E.tolist(), "E_lo": g.E_lo.tolist(), "E_hi": g.E_hi.tolist(), "V": g.V.tolist(), "V_lo": g.V_lo.tolist(),
                           "V_hi": g.V_hi.tolist(), "S": g.S.tolist(), "S_lo": g.S_lo.tolist(), "S_hi": g.S_hi.tolist(), "DI": g.DI.round(1).tolist(), "flag": g.flag_code.tolist(),
                           "conf": [g.E_confidence.iloc[11][0], g.V_confidence.iloc[11][0], g.S_confidence.iloc[11][0]]})
        doc = {"state": st, "months": months, "flag_names": FLAG_NAMES, "districts": {int(c): n for c, n in sdim.drop_duplicates("District_LGD_Code")[["District_LGD_Code", "District_Name"]].itertuples(index=False)},
               "conf_note": "first letters of the E, V, S confidence labels at 12 months (H, M, L)", "series": series}
        p = out_dir / f"{slug(st)}.json"
        p.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        info[st] = {"file": p.name, "series": len(series), "bytes": p.stat().st_size}
    (out_dir / "index.json").write_text(json.dumps({"months": months, "states": info}, indent=1), encoding="utf-8")
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(C.DATA / "exports"))
    ap.add_argument("--manifest", default=str(C.DATA / "FORECAST_MANIFEST.json"))
    a = ap.parse_args()
    d = Path(a.dir)
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    fc = pd.read_parquet(d / "forecast_series.parquet")
    di = pd.read_parquet(d / "demand_index.parquet")
    calib = pd.read_csv(C.DATA / "aggregate_interval_calibration.csv")
    rolls = demand_index_rollups(di, fc, dim, RU.rollup_forecast(fc, dim, calib))
    cap = {p.stem.replace("capacity_", ""): pd.read_parquet(p) for p in d.glob("capacity_*.parquet")}
    written = {}

    def save(name, df, **kw):
        p = d / name
        df.to_csv(p, index=False, **kw)
        written[name] = {"rows": len(df)}

    save("forecast_rollups.csv.gz", rolls)
    for level, t in cap.items():
        if level == "series":
            save("capacity_gap_series.csv.gz", t.drop(columns=["Trade_Name"], errors="ignore"))
        else:
            save(f"capacity_gap_{level}.csv", t)
    save("flag_alerts.csv", alerts_table(fc, dim))
    save("rankings.csv", rankings_table(fc, rolls, cap, di, dim))
    info = shards(fc, di, dim, d / "shards")
    man = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "forecast_origin": C.ORIGIN, "forecast_months": [str(C.FORECAST_MONTHS[0]), str(C.FORECAST_MONTHS[-1])],
           "series": int(fc.Series_ID.nunique()), "rows_per_series": 60, "data_simulated": True, "files": {}, "shards": info, "inputs": {}}
    for name, v in written.items():
        man["files"][name] = {**v, "bytes": (d / name).stat().st_size, "sha256": sha(d / name)}
    for name in ("forecast_series.parquet", "demand_index.parquet"):
        man["files"][name] = {"rows": int(len(fc) if name.startswith("forecast") else len(di)), "bytes": (d / name).stat().st_size, "sha256": sha(d / name), "tracked": False}
    ev = C.REPORTS / "evaluation"
    man["inputs"] = {"panel_content_sha256": json.loads((C.DATA / "DATA_MANIFEST.json").read_text(encoding="utf-8")).get("content_sha256"), "best_params_sha256": sha(ev / "best_params.json"),
                     "interval_calibration_sha256": sha(C.DATA / "interval_calibration.csv"), "aggregate_interval_calibration_sha256": sha(C.DATA / "aggregate_interval_calibration.csv"),
                     "confidence_cells_sha256": sha(C.DATA / "confidence_cells.csv")}
    fit = C.REPORTS / "forecast" / "deploy_fit.json"
    if fit.exists():
        man["inputs"]["deploy_fit"] = json.loads(fit.read_text(encoding="utf-8")) | {"inputs": "see deploy_fit.json"}
        man["inputs"]["deploy_models_sha256"] = {f.name: sha(f) for f in sorted((C.MODELS / "deploy").glob("*.json"))}
    Path(a.manifest).write_text(json.dumps(man, indent=2), encoding="utf-8")
    print("written", {k: v["rows"] for k, v in written.items()}, "shards MB", round(sum(s["bytes"] for s in info.values()) / 1e6, 1))


if __name__ == "__main__":
    main()
