#!/usr/bin/env python3
"""
v4 phase 7 - build the dashboard's data files and page shell from the phase 6 exports.  Nothing shown on the dashboard is typed in by hand.

Writes (app/dashboard/data/)
    core.js            window.DASH4: scope lists, history and 2026-2030 forecast of India / 5 sectors / 25 trades / 10 states / 50 state-sectors, range tables, capacity-gap tables,
                       Demand Index by state-trade and district-sector, rankings, caveat figures and the hashes of the export files it was built from
    alerts.js          window.DASH4_ALERTS: every shortage and oversupply ALERT at 12, 36 and 60 months (flag_alerts.csv)
    shards/<state>.json  one file per state, loaded when a state or district is chosen: history 2021-2025 and forecast 2026-2030 of each district-trade (points only), Demand Index,
                       flags, confidence letters and the capacity-gap inputs
and app/dashboard/index.html from src/app/dashboard/shell.html (the shell is shared with the site build; the v4 shell is src/v4/dashboard_shell.html).

Ranges are not stored: the browser applies the calibration tables in core.js (the same tables, the same recipe as forecast.py and rollups.py) to the point forecast of any
series, district-sector, state-sector, state, sector, trade or India.  Other combinations (for example a state and one trade) get the point forecast without a range.

Run: python src/v4/build_dashboard.py
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import exports as EX
import rollups as RU

APP = C.ROOT / "app" / "dashboard"
OUT = APP / "data"
HIST_FROM_CORE, HIST_FROM_SHARD = 192, 252             # 2016-01 and 2021-01 (month indices)
N_HIST_CORE, N_HIST_SHARD = C.N_MONTHS - HIST_FROM_CORE, C.N_MONTHS - HIST_FROM_SHARD
YEARS = list(range(2026, 2031))
BANDS = ["1-12", "13-24", "25-36", "37-48", "49-60"]
LETTER = {"High": "H", "Medium": "M", "Low": "L"}


def wide(df, col, ids):
    return df.pivot(index="Series_ID", columns="Date", values=col).reindex(ids).to_numpy(np.float64)


def jdump(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def ints(a):
    return np.rint(a).astype(np.int64).tolist()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def history_and_forecast(dim, fc, di):
    """E, V, S (series, 2016-01..2030-12) and the Demand Index (series, 180) in series order."""
    ids = dim.Series_ID.to_numpy()
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Series_ID", "Date", "Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"])
    out = {}
    for k, col in (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers")):
        h = wide(raw, col, ids)[:, HIST_FROM_CORE:]
        f = fc.pivot(index="series_row", columns="horizon", values=k).sort_index().to_numpy(np.float64)
        out[k] = np.hstack([h, f])
    d = di.pivot(index="series_row", columns="month", values="DI").sort_index().to_numpy(np.float64)
    assert d.shape[1] == N_HIST_CORE + 60 and (fc.groupby("series_row").size() == 60).all()
    return out, d


def group_table(dim, series, d, level_cols):
    """Sum of E, V, S and employed-weighted Demand Index of each group of one level: {key: {E,V,S,DI}} with 120 history + 60 forecast months."""
    key = pd.Series("", index=dim.index) if not level_cols else dim[level_cols].astype(str).agg("|".join, axis=1)
    out = {}
    for g, rows in key.groupby(key).groups.items():
        r = np.asarray(list(rows))
        e = series["E"][r].sum(axis=0)
        w = (series["E"][r] * d[r]).sum(axis=0) / e
        out[g] = {"E": ints(e), "V": ints(series["V"][r].sum(axis=0)), "S": ints(series["S"][r].sum(axis=0)), "DI": np.round(w, 1).tolist()}
    return out


def year_di(dim, series, d, cols):
    """Employed-weighted Demand Index per calendar year 2026-2030 for each group (forecast months only)."""
    key = dim[cols].astype(str).agg("|".join, axis=1)
    f0 = N_HIST_CORE
    out = {}
    for g, rows in key.groupby(key).groups.items():
        r = np.asarray(list(rows))
        e, v = series["E"][r][:, f0:], d[r][:, f0:]
        out[g] = [round(float((e[:, 12 * y:12 * y + 12] * v[:, 12 * y:12 * y + 12]).sum() / e[:, 12 * y:12 * y + 12].sum()), 1) for y in range(5)]
    return out


def calibration():
    """Series-level and aggregate range tables as offsets on the log scale (60 horizons each)."""
    s = pd.read_csv(C.DATA / "interval_calibration.csv")
    series = {}
    for (k, grp), t in s.groupby(["target", "group"]):
        t = t.sort_values("horizon")
        assert list(t.horizon) == list(range(1, 61)), (k, grp)
        series.setdefault(k, {})[grp] = {n: t[n].round(5).tolist() for n in ("lo", "hi", "lo_wide", "hi_wide")}
    a = pd.read_csv(C.DATA / "aggregate_interval_calibration.csv")
    levels = {}
    for (lv, k), t in a.groupby(["level", "target"]):
        t = t.sort_values("horizon")
        assert list(t.horizon) == list(range(1, 61)), (lv, k)
        levels.setdefault(lv, {})[k] = {n: t[n].round(5).tolist() for n in ("lo", "hi", "lo_wide", "hi_wide")}
    return series, levels


def coverage_figures():
    """The coverage numbers quoted on the notes page, read from the evaluation tables."""
    ev = C.REPORTS / "evaluation"
    s = pd.read_csv(ev / "interval_coverage.csv")
    s = s[(s.slice == "all") & (s.calibration == "forward")]
    series = {f"{r.window}|{r.target}|{r.calibrated_on}": round(float(r.coverage), 3) for r in s.itertuples()}
    a = pd.read_csv(ev / "aggregate_interval_coverage.csv")
    agg = {f"{r.calibration}|{r.window}|{r.level}|{r.target}": round(float(r.coverage), 3) for r in a.itertuples()}
    p = pd.read_csv(ev / "flag_precision.csv")
    p = p[(p.window == "test") & (p.source == "model") & (p.volume == "all") & (p.flag.isin(["Shortage alert", "Oversupply alert"]))]
    prec = {f"{r.band}|{r.flag}": [round(float(r.precision_decile), 3), round(float(r.lift_decile), 1)] for r in p.itertuples()}
    return {"series": series, "aggregate": agg, "alert_precision_test": prec}


def shard_docs(dim, fc, di, series, d, cap, conf):
    OUT.joinpath("shards").mkdir(parents=True, exist_ok=True)
    flag = fc.pivot(index="series_row", columns="horizon", values="flag_code").sort_index().to_numpy(np.int8)
    cov = fc.pivot(index="series_row", columns="horizon", values="coverage_pct").sort_index().to_numpy(np.float64)
    hist0 = HIST_FROM_SHARD - HIST_FROM_CORE
    sub_d = d[:, hist0:]
    capy = cap.pivot(index="Series_ID", columns="year", values="avg_vacancies").reindex(dim.Series_ID)
    mm = cap.pivot(index="Series_ID", columns="year", values="mismatch").reindex(dim.Series_ID)
    seats = cap.groupby("Series_ID").seats.first().reindex(dim.Series_ID)
    cert = cap.groupby("Series_ID").expected_certified.first().reindex(dim.Series_ID)
    trades = list(dict.fromkeys(dim.Trade_Code))
    info = {}
    for st, sdim in dim.groupby("State_Name"):
        r = sdim.index.to_numpy()
        doc = {"state": st, "ids": sdim.Series_ID.tolist(), "d": sdim.District_LGD_Code.astype(int).tolist(), "t": [trades.index(t) for t in sdim.Trade_Code],
               "hist": {k: ints(series[k][r][:, hist0:N_HIST_CORE]) for k in "EVS"}, "fc": {k: ints(series[k][r][:, N_HIST_CORE:]) for k in "EVS"},
               "DI": np.round(sub_d[r], 1).tolist(), "flag": flag[r].tolist(), "cov": np.round(cov[r], 1).tolist(),
               "conf": {k: [conf[k][i] for i in r] for k in "EVS"},
               "cap": {"seats": ints(seats.to_numpy()[r]), "cert": np.round(cert.to_numpy()[r], 1).tolist(), "vac": np.round(capy.to_numpy()[r], 1).tolist(), "mm": np.round(mm.to_numpy()[r], 3).tolist()}}
        p = OUT / "shards" / f"{EX.slug(st)}.json"
        p.write_text(jdump(doc), encoding="utf-8")
        info[st] = {"file": f"shards/{p.name}", "series": len(r), "bytes": p.stat().st_size}
    return info


def confidence_letters(fc, dim):
    """For each target, one string of five letters (H, M, L) per series: the confidence label of each 12-month band."""
    out = {}
    for k in "EVS":
        t = fc[fc.horizon.isin([6, 18, 30, 42, 54])].pivot(index="series_row", columns="horizon", values=f"{k}_confidence").sort_index()
        out[k] = ["".join(LETTER[v] for v in row) for row in t.to_numpy()]
    return out


def main():
    ex = C.DATA / "exports"
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    fc = pd.read_parquet(ex / "forecast_series.parquet")
    di = pd.read_parquet(ex / "demand_index.parquet")
    di = di[di.month >= "2016-01"]
    series, d = history_and_forecast(dim, fc, di)
    cap = pd.read_parquet(ex / "capacity_series.parquet")
    man = json.loads((C.DATA / "FORECAST_MANIFEST.json").read_text(encoding="utf-8"))

    levels = {"india": [], "sector": ["Sector_Name"], "trade": ["Trade_Code"], "state": ["State_Name"], "state_sector": ["State_Name", "Sector_Name"]}
    groups = {lv: group_table(dim, series, d, cols) for lv, cols in levels.items()}
    series_cal, level_cal = calibration()
    trades = [{"c": c, "n": n, "s": s} for c, n, s in dim.drop_duplicates("Trade_Code")[["Trade_Code", "Trade_Name", "Sector_Name"]].itertuples(index=False)]
    districts = [[int(c), n, list(C.STATES).index(s)] for c, n, s in dim.drop_duplicates("District_LGD_Code")[["District_LGD_Code", "District_Name", "State_Name"]].itertuples(index=False)]
    capacity = {p.stem.replace("capacity_gap_", ""): pd.read_csv(p).round(4).to_dict("records") for p in sorted(ex.glob("capacity_gap_*.csv"))}
    dsec = dim.assign(k=dim.District_LGD_Code.astype(str))
    core = {
        "meta": {"origin": C.ORIGIN, "hist_core": [str(C.MONTHS[HIST_FROM_CORE]), str(C.MONTHS[-1]), N_HIST_CORE], "hist_shard": [str(C.MONTHS[HIST_FROM_SHARD]), str(C.MONTHS[-1]), N_HIST_SHARD],
                 "fc": [str(C.FORECAST_MONTHS[0]), str(C.FORECAST_MONTHS[-1]), 60], "states": list(C.STATES), "sectors": list(C.SECTORS), "trades": trades, "districts": districts, "years": YEARS,
                 "bands": BANDS, "flag_names": EX.FLAG_NAMES, "simulated": True, "series": int(len(dim)), "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "files": {n: v["sha256"][:16] for n, v in man["files"].items() if "sha256" in v},
                 "manifest": {"forecast_origin": man["forecast_origin"], "generated_at_utc": man["generated_at_utc"], "deploy_fit": {k: man["inputs"]["deploy_fit"].get(k) for k in ("fit_targets_to", "left_out", "pairs_before", "pairs_after")}}},
        "groups": groups, "cal_series": series_cal, "cal_levels": level_cal, "capacity": capacity,
        "di_state_trade": year_di(dim, series, d, ["State_Name", "Trade_Code"]), "di_district_sector": year_di(dim, series, d, ["District_LGD_Code", "Sector_Name"]),
        "rankings": pd.read_csv(ex / "rankings.csv").to_dict("records"), "coverage": coverage_figures(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "core.js").write_text("window.DASH4=" + jdump(core) + ";\n", encoding="utf-8")

    al = pd.read_csv(ex / "flag_alerts.csv")
    st_ix, tr_ix = {s: i for i, s in enumerate(C.STATES)}, {t["c"]: i for i, t in enumerate(trades)}
    hz = {12: 0, 36: 1, 60: 2}
    rows = [[0 if r.flag == "Shortage alert" else 1, hz[int(r.horizon)], st_ix[r.State_Name], int(r.District_LGD_Code), tr_ix[r.Trade_Code], float(r.coverage_pct), int(r.V), int(r.S),
             LETTER[r.V_confidence], LETTER[r.S_confidence]] for r in al.itertuples()]
    (OUT / "alerts.js").write_text("window.DASH4_ALERTS=" + jdump({"columns": ["type(0 shortage,1 oversupply)", "horizon(0=12,1=36,2=60)", "state", "district_lgd", "trade", "coverage_pct", "V", "S", "V_conf", "S_conf"], "rows": rows}) + ";\n", encoding="utf-8")

    info = shard_docs(dim, fc, di, series, d, cap, confidence_letters(fc, dim))
    (OUT / "shards" / "index.json").write_text(json.dumps({"states": info}, indent=1), encoding="utf-8")
    shell()
    print({"core_kb": round((OUT / "core.js").stat().st_size / 1e3), "alerts_kb": round((OUT / "alerts.js").stat().st_size / 1e3), "alerts": len(rows), "shards_mb": round(sum(v["bytes"] for v in info.values()) / 1e6, 1)})


def shell():
    """The page shell, with the stylesheet and scripts versioned by content so a changed file is never served stale."""
    import sys
    sys.path.insert(0, str(C.ROOT / "src" / "app"))
    import logo

    def ver(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:10]
    html = (Path(__file__).resolve().parent / "dashboard_shell.html").read_text(encoding="utf-8").replace("{LOGO}", logo.inline())
    for token, path in (("{CSS}", APP / "dashboard.css"), ("{JS}", APP / "dashboard.js"), ("{CORE}", OUT / "core.js"), ("{ALERTS}", OUT / "alerts.js"),
                        ("{CHATCSS}", C.ROOT / "app" / "assets" / "chat.css"), ("{CHATJS}", C.ROOT / "app" / "assets" / "chat.js")):
        html = html.replace(token, ver(path))
    (APP / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
