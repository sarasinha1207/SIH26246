#!/usr/bin/env python3
"""
Dashboard - build app/dashboard/data/dash_data.js (history, forecasts and flags for all 280 series) and app/dashboard/index.html (the page shell).

Everything the dashboard shows comes from this file: the monthly panel up to the forecast origin, the Phase 9 forecast file and the Phase 9 flag file.
The dashboard sums series in the browser, so any combination of sector, state and district can be shown without another file.

Run: python src/app/build_dashboard.py          (the shell alone is rebuilt by serve.py when the dashboard files change)
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
OUT = ROOT / "app" / "dashboard"
ORIGIN = "2026-10"
FC = ROOT / "outputs" / "forecasts" / f"origin_{ORIGIN}"
TARGETS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
HIST = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers", "W": "Avg_Monthly_Wage_INR", "U": "Unemployment_Rate_Pct",
        "T": "Training_Seats_Sanctioned", "C": "Trainees_Certified_Monthly"}
STATUS = ["Tightest decile", "Tight", "Typical", "Loose", "Loosest decile"]
CONTEXT = ["openings exceed seekers", "moderate", "oversupplied", "deep surplus"]
CHANGE = ["no change", "entering tightest decile", "leaving tightest decile", "entering loosest decile", "leaving loosest decile"]


def ym(ts):
    return ts.strftime("%Y-%m")


def build_data():
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str}).sort_values("Series_ID").reset_index(drop=True)
    sid = dims.Series_ID.tolist()
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date", *HIST.values(), "Is_Covid_Window", "Is_Eshram_Ramp"])
    panel = panel[panel.Date <= pd.Timestamp(ORIGIN + "-01")].sort_values(["Series_ID", "Date"])
    months = sorted(panel.Date.unique())
    assert all(len(g) == len(months) for _, g in panel.groupby("Series_ID", observed=True)) and len(sid) == 280
    hist = {}
    for k, col in HIST.items():
        piv = panel.pivot(index="Series_ID", columns="Date", values=col).loc[sid]
        assert not piv.isna().any().any(), col
        hist[k] = (piv * 10).round().astype(int).values.tolist() if k == "U" else piv.round().astype(int).values.tolist()

    L = pd.read_csv(FC / "forecast_long.csv", dtype={"district_lgd_code": str})
    fc = {}
    for k, tv in TARGETS.items():
        g = L[L.target_variable == tv]
        out = {}
        for col, name in (("forecast", "f"), ("lo90", "lo"), ("hi90", "hi")):
            piv = g.pivot(index="Series_ID", columns="horizon", values=col).loc[sid]
            assert piv.shape[1] == 12 and not piv.isna().any().any()
            out[name] = piv.round(1).values.tolist()
        out["conf"] = g.groupby("Series_ID").confidence.first().loc[sid].tolist()
        fc[k] = out
    fmonths = sorted(L.target_month.unique())
    assert len(fmonths) == 12

    W = pd.read_csv(FC / "flags.csv", dtype={"district_lgd_code": str}).sort_values(["Series_ID", "horizon"])
    fl = []
    for s_id in sid:
        g = W[W.Series_ID == s_id]
        assert len(g) == 12
        fl.append([[round(float(r.forecast_percentile), 1), STATUS.index(r.forecast_status), CONTEXT.index(r.absolute_context), STATUS.index(r.current_status), CHANGE.index(r.change),
                    -1 if pd.isna(r.historical_precision) else round(float(r.historical_precision), 2), round(float(r.forecast_coverage_ratio), 4)] for r in g.itertuples()])

    series = [{"id": r.Series_ID, "code": r.District_LGD_Code, "district": r.District_Name, "state": r.State_Name, "sector": r.Sector_Name, "tier": r.Econ_Tier, "low": bool(r.Low_Volume)} for r in dims.itertuples()]
    cur = W[W.horizon == 1].set_index("Series_ID").loc[sid]
    covid = panel[panel.Is_Covid_Window == True].Date  # noqa: E712
    ramp = panel[panel.Is_Eshram_Ramp == True].Date    # noqa: E712
    data = {"meta": {"origin": ORIGIN, "origin_label": pd.Timestamp(ORIGIN + "-01").strftime("%B %Y"), "months": [ym(pd.Timestamp(m)) for m in months], "fmonths": fmonths,
                     "model": "xgboost_v3 refitted on data to " + ORIGIN, "covid": [ym(covid.min()), ym(covid.max())], "eshram": {"launch": "2021-08", "ramp": [ym(ramp.min()), ym(ramp.max())]},
                     "forecast_rows": int(len(L)), "flag_rows": int(len(W)), "states": sorted(dims.State_Name.unique()), "sectors": sorted(dims.Sector_Name.unique()),
                     "tiers": int(dims.Econ_Tier.nunique()), "layout": {"hist": "hist[k][series][month]; U is tenths of a percent", "fc": "fc[k].f|lo|hi[series][horizon-1]",
                                                                     "fl": "fl[series][horizon-1] = [percentile, status, context, current_status, change, precision(-1 none), forecast ratio]"},
                     "status": STATUS, "context": CONTEXT, "change": CHANGE, "thresholds": {"exceed": 1.0, "moderate": 0.2, "oversupplied": 0.1}},
            "series": series, "hist": hist, "fc": fc, "fl": fl, "current_ratio": [round(float(v), 4) for v in cur.current_coverage_ratio]}
    return data


def shell():
    """The page shell, with the stylesheet and scripts versioned by content so a changed file is never served stale."""
    def ver(p):
        return hashlib.sha1(p.read_bytes()).hexdigest()[:8]
    html = (SRC / "dashboard" / "shell.html").read_text(encoding="utf-8")
    for token, path in (("{CSS}", OUT / "dashboard.css"), ("{JS}", OUT / "dashboard.js"), ("{DATA}", OUT / "data" / "dash_data.js"), ("{MAP}", ROOT / "app" / "data" / "map_data.js")):
        html = html.replace(token, ver(path))
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main():
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    data = build_data()
    (OUT / "data" / "dash_data.js").write_text("window.DASH = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    shell()
    size = (OUT / "data" / "dash_data.js").stat().st_size
    print(f"wrote app/dashboard/data/dash_data.js ({size / 1e6:.2f} MB): 280 series x {len(data['meta']['months'])} months of history, 12 forecast months")


if __name__ == "__main__":
    main()
