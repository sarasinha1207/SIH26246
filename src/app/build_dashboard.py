#!/usr/bin/env python3
"""
Dashboard - build app/dashboard/data/dash_data.js (history, forecasts and flags for all 280 series) and app/dashboard/index.html (the page shell).

Everything the dashboard shows comes from three files, and nothing is typed in by hand:
  * history        data/processed/panel_monthly.parquet (up to the forecast origin)
  * forecasts      outputs/forecasts/origin_<month>/forecast_long.csv   (forecast, lo90, hi90, confidence - copied unrounded)
  * early warnings outputs/forecasts/origin_<month>/flags.csv           (percentile, status, absolute context, change, precision, confidence - copied unrounded)
The origin month, row counts and file hashes are checked against that folder's manifest.json, and the absolute-context thresholds are derived from
(and checked against) flags.csv itself.  The dashboard sums series in the browser, so any combination of sector, state and district can be shown.

Run: python src/app/build_dashboard.py [YYYY-MM]  (newest forecast folder when no month is given; the shell alone is rebuilt by serve.py when the dashboard files change)
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
OUT = ROOT / "app" / "dashboard"


def latest_origin():
    """The newest forecast folder, unless an origin such as 2026-10 is given on the command line."""
    if len(sys.argv) > 1 and re.fullmatch(r"\d{4}-\d{2}", sys.argv[1]):
        return sys.argv[1]
    return max(d.name[len("origin_"):] for d in (ROOT / "outputs" / "forecasts").glob("origin_*") if (d / "forecast_long.csv").exists())


ORIGIN = latest_origin()
FC = ROOT / "outputs" / "forecasts" / f"origin_{ORIGIN}"
TARGETS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
HIST = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers", "W": "Avg_Monthly_Wage_INR", "U": "Unemployment_Rate_Pct",
        "T": "Training_Seats_Sanctioned", "C": "Trainees_Certified_Monthly"}
STATUS = ["Tightest decile", "Tight", "Typical", "Loose", "Loosest decile"]
CONTEXT = ["openings exceed seekers", "moderate", "oversupplied", "deep surplus"]
CHANGE = ["no change", "entering tightest decile", "leaving tightest decile", "entering loosest decile", "leaving loosest decile"]
# The project's own flag classes (manifest flag_rules: "deciles at 10/90, watch classes at 30/70"): a decile is an alert, the 30/70 class is a watch.
# This is a lookup on flags.csv forecast_status only; no other rule or threshold is applied in the browser.
FLAG_CLASS = {"Tightest decile": ["shortage", "alert"], "Tight": ["shortage", "watch"], "Typical": None, "Loose": ["oversupply", "watch"], "Loosest decile": ["oversupply", "alert"]}
RANK = {"low": 0, "medium": 1, "high": 2}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def thresholds_from(W):
    """The coverage ratios that separate the four absolute contexts, read off flags.csv.  The build stops if any ratio sits in the wrong class
    (the classes must split cleanly); the cut is then the roundest number between the highest ratio below the split and the lowest above it."""
    r, c = W.forecast_coverage_ratio, W.absolute_context            # absolute_context is the class of the forecast ratio
    out = {}
    for name, k in (("exceed", 0), ("moderate", 1), ("oversupplied", 2)):
        above, below = CONTEXT[:k + 1], CONTEXT[k + 1:]
        lo, hi = r[c.isin(below)].max(), r[c.isin(above)].min()
        assert lo < hi, f"absolute contexts overlap at the '{name}' split: {lo} vs {hi}"
        for d in range(0, 6):                                          # the roundest cut that lies in the gap: lo < cut <= hi
            cut = math.floor(lo * 10 ** d + 1) / 10 ** d
            if cut <= hi:
                break
        out[name] = [float(lo), float(hi), round(cut, d)]
    return out


def ym(ts):
    return ts.strftime("%Y-%m")


def build_data():
    man = json.loads((FC / "manifest.json").read_text(encoding="utf-8"))
    assert man["origin"] == ORIGIN and man["history_last_month"].startswith(ORIGIN), "manifest origin differs from the folder"
    for name in ("forecast_long.csv", "flags.csv"):
        assert sha(FC / name) == man["files_sha256"][name], f"{name} does not match the hash in manifest.json (file changed after the forecast run)"
    assert sha(ROOT / "data" / "processed" / "panel_monthly.parquet") == man["panel_sha256"], "panel_monthly.parquet is not the panel the forecast was made from"

    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str}).sort_values("Series_ID").reset_index(drop=True)
    sid = dims.Series_ID.tolist()
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date", *HIST.values(), "Is_Covid_Window", "Is_Eshram_Ramp"])
    panel = panel[panel.Date <= pd.Timestamp(ORIGIN + "-01")].sort_values(["Series_ID", "Date"])
    months = sorted(panel.Date.unique())
    assert all(len(g) == len(months) for _, g in panel.groupby("Series_ID", observed=True)) and len(sid) == man["coverage"]["series"]
    hist = {}
    for k, col in HIST.items():
        piv = panel.pivot(index="Series_ID", columns="Date", values=col).loc[sid]
        assert not piv.isna().any().any(), col
        hist[k] = (piv * 10).round().astype(int).values.tolist() if k == "U" else piv.round().astype(int).values.tolist()

    # ---- forecasts: copied from forecast_long.csv exactly as written ----
    L = pd.read_csv(FC / "forecast_long.csv", dtype={"district_lgd_code": str})
    assert len(L) == man["coverage"]["forecast_rows"] == len(sid) * len(TARGETS) * 12 and set(L.origin_month) == {ORIGIN}
    assert set(L.Series_ID) == set(sid) and not L[["forecast", "lo90", "hi90"]].isna().any().any() and ((L.lo90 <= L.forecast) & (L.forecast <= L.hi90)).all()
    fc = {}
    for k, tv in TARGETS.items():
        g = L[L.target_variable == tv]
        assert g.groupby("Series_ID").confidence.nunique().max() == 1, "confidence differs between horizons of one series"
        last_seen = g.groupby("Series_ID").last_observed.first().loc[sid].round().astype(int).tolist()
        assert last_seen == [row[-1] for row in hist[k]], f"last_observed in forecast_long.csv differs from the last month of the {k} history"
        out = {}
        for col, name in (("forecast", "f"), ("lo90", "lo"), ("hi90", "hi"), ("typical_test_error_pct", "err")):
            piv = g.pivot(index="Series_ID", columns="horizon", values=col).loc[sid]
            assert list(piv.columns) == list(range(1, 13)) and not piv.isna().any().any()
            out[name] = piv.values.tolist()
        out["conf"] = g.groupby("Series_ID").confidence.first().loc[sid].tolist()
        fc[k] = out
    fmonths = sorted(L.target_month.unique())
    assert len(fmonths) == 12 and L.groupby("horizon").target_month.nunique().max() == 1

    # ---- early-warning flags: copied from flags.csv exactly as written ----
    W = pd.read_csv(FC / "flags.csv", dtype={"district_lgd_code": str}).sort_values(["Series_ID", "horizon"])
    assert len(W) == man["coverage"]["flag_rows"] == len(sid) * 12 and set(W.Series_ID) == set(sid)
    th = thresholds_from(W)
    flag_conf = W.groupby("Series_ID").confidence.first().loc[sid].tolist()
    fl = []
    for s_id in sid:
        g = W[W.Series_ID == s_id]
        assert len(g) == 12 and g.horizon.tolist() == list(range(1, 13))
        fl.append([[float(r.forecast_percentile), STATUS.index(r.forecast_status), CONTEXT.index(r.absolute_context), STATUS.index(r.current_status), CHANGE.index(r.change),
                    None if pd.isna(r.historical_precision) else float(r.historical_precision), float(r.forecast_coverage_ratio)] for r in g.itertuples()])

    models = set(re.findall(r"models/(xgboost_v\d+)/", json.dumps(man["interval_policy"])))
    assert len(models) == 1, models
    series = [{"id": r.Series_ID, "code": r.District_LGD_Code, "district": r.District_Name, "state": r.State_Name, "sector": r.Sector_Name, "tier": r.Econ_Tier, "low": bool(r.Low_Volume)} for r in dims.itertuples()]
    cur = W[W.horizon == 1].set_index("Series_ID").loc[sid]
    covid = panel[panel.Is_Covid_Window == True].Date  # noqa: E712
    ramp = panel[panel.Is_Eshram_Ramp == True].Date    # noqa: E712
    data = {"meta": {"origin": ORIGIN, "origin_label": pd.Timestamp(ORIGIN + "-01").strftime("%B %Y"), "months": [ym(pd.Timestamp(m)) for m in months], "fmonths": fmonths,
                     "model": sorted(models)[0], "covid": [ym(covid.min()), ym(covid.max())], "eshram": {"launch": ym(ramp.min()), "ramp": [ym(ramp.min()), ym(ramp.max())]},
                     "forecast_rows": int(len(L)), "flag_rows": int(len(W)), "states": sorted(dims.State_Name.unique()), "sectors": sorted(dims.Sector_Name.unique()),
                     "tiers": int(dims.Econ_Tier.nunique()), "target_names": TARGETS, "horizons": man["coverage"]["horizons"], "targets": list(man["coverage"]["targets"]),
                     "layout": {"hist": "hist[k][series][month]; U is tenths of a percent", "fc": "fc[k].f|lo|hi[series][horizon-1]",
                                "fl": "fl[series][horizon-1] = [percentile, status, context, current_status, change, precision (null: none), forecast ratio]"},
                     "status": STATUS, "context": CONTEXT, "change": CHANGE, "flag_class": [FLAG_CLASS[x] for x in STATUS], "flag_conf": flag_conf,
                     "thresholds": {k: v[2] for k, v in th.items()},
                     "manifest": {"flag_rules": man["flag_rules"], "confidence_rules": man["confidence_rules"], "interval_policy": man["interval_policy"], "created": man["created"]},
                     "sources": {"forecast_long.csv": man["files_sha256"]["forecast_long.csv"], "flags.csv": man["files_sha256"]["flags.csv"], "panel_monthly.parquet": man["panel_sha256"]}},
            "series": series, "hist": hist, "fc": fc, "fl": fl, "current_ratio": [float(v) for v in cur.current_coverage_ratio]}
    return data


def shell():
    """The page shell, with the stylesheet and scripts versioned by content so a changed file is never served stale."""
    def ver(p):
        return hashlib.sha1(p.read_bytes()).hexdigest()[:8]
    html = (SRC / "dashboard" / "shell.html").read_text(encoding="utf-8").replace("{LOGO}", logo.inline())
    for token, path in (("{CSS}", OUT / "dashboard.css"), ("{JS}", OUT / "dashboard.js"), ("{DATA}", OUT / "data" / "dash_data.js"), ("{MAP}", ROOT / "app" / "data" / "map_data.js"),
                        ("{CHATCSS}", ROOT / "app" / "assets" / "chat.css"), ("{CHATJS}", ROOT / "app" / "assets" / "chat.js")):
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
