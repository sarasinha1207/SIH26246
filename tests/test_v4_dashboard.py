"""v4 phase 7 tests: every figure on the dashboard traces to the phase 6 exports, the shell and script have the pages, filters, exports and both languages,
and the files the browser loads stay within a size budget.  Runs under pytest or standalone: python tests/test_v4_dashboard.py"""
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "v4"))
sys.path.insert(0, str(ROOT / "tests"))
import _guard  # noqa: E402
import config as C  # noqa: E402

DASH = ROOT / "app" / "dashboard"
DATA = DASH / "data"
EXPORTS = C.DATA / "exports"
PAGES = ["overview", "map", "forecast", "index", "capacity", "ranking", "warnings", "data"]

_guard.skip_module_unless(DATA / "core.js", EXPORTS / "forecast_rollups.csv.gz", why="needs the v4 dashboard build (src/v4/build_dashboard.py) and the phase 6 exports")

_CORE = {}


def core():
    if not _CORE:
        t = (DATA / "core.js").read_text(encoding="utf-8")
        _CORE.update(json.loads(t[t.index("{"):t.rindex("}") + 1]))
    return _CORE


def need(path):
    if not Path(path).exists():
        raise unittest.SkipTest(f"{Path(path).name} is git-ignored and not rebuilt in this clone")


def js():
    return (DASH / "dashboard.js").read_text(encoding="utf-8")


def shell():
    return (DASH / "index.html").read_text(encoding="utf-8")


def rollups():
    return pd.read_csv(EXPORTS / "forecast_rollups.csv.gz", low_memory=False)


# ---- the numbers ---------------------------------------------------------------------------------------------------------------------------------
def test_group_forecasts_equal_the_rollup_table():
    r, g = rollups(), core()["groups"]
    HC = core()["meta"]["hist_core"][2]
    checks = {"india": ("india", None), "sector": ("sector", "Sector_Name"), "trade": ("trade", "Trade_Code"), "state": ("state", "State_Name")}
    for lv, (level, col) in checks.items():
        sub = r[r.level == level]
        for key, G in g[lv].items():
            s = sub if col is None else sub[sub[col] == key]
            s = s.sort_values("horizon")
            for k in "EVS":
                assert s[k].tolist() == G[k][HC:], (lv, key, k)
    sub = r[r.level == "state_sector"]
    for key, G in g["state_sector"].items():
        st, sec = key.split("|")
        s = sub[(sub.State_Name == st) & (sub.Sector_Name == sec)].sort_values("horizon")
        assert all(s[k].tolist() == G[k][HC:] for k in "EVS"), key
    assert len(g["trade"]) == 25 and len(g["state"]) == 10 and len(g["state_sector"]) == 50 and len(g["sector"]) == 5


def test_group_history_equals_the_panel_and_demand_index_is_in_range():
    need(C.DATA / "raw" / "trade_monthly_2000_2025.parquet")
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Date", "Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"])
    t = raw.groupby("Date").sum().iloc[core()["meta"]["hist_core"][2] * -1:]
    G = core()["groups"]["india"][""]
    HC = core()["meta"]["hist_core"][2]
    assert G["E"][:HC] == t.Total_Employed_Workers.astype(int).tolist() and G["V"][:HC] == t.Active_Job_Vacancies.astype(int).tolist() and G["S"][:HC] == t.eShram_Registered_Seekers.astype(int).tolist()
    for lv in core()["groups"].values():
        for g in lv.values():
            assert len(g["DI"]) == HC + 60 and 0 <= min(g["DI"]) and max(g["DI"]) <= 100


def test_ranges_computed_in_the_browser_equal_the_exported_ones():
    """The script applies exp(offset) from the calibration tables of core.js to the point forecast, with the offsets clamped so the point is inside; same recipe as rollups.py."""
    r, cal = rollups(), core()["cal_levels"]
    for level in ("india", "sector", "state", "trade", "state_sector", "district_sector"):
        s = r[r.level == level].sort_values(["horizon"])
        s = s.iloc[: 60 * 50] if len(s) > 3000 else s
        h = s.horizon.to_numpy() - 1
        for k in "EVS":
            for nm, lo in (("lo", 1), ("hi", 0), ("lo_wide", 1), ("hi_wide", 0)):
                off = np.array(cal[level][k][nm])[h]
                off = np.minimum(off, 0) if lo else np.maximum(off, 0)
                got = np.rint(s[k].to_numpy() * np.exp(off))
                assert np.abs(got - s[f"{k}_{nm}"].to_numpy()).max() <= 1, (level, k, nm)


def test_series_ranges_are_close_to_the_exported_ones():
    need(EXPORTS / "forecast_series.parquet")
    f = pd.read_parquet(EXPORTS / "forecast_series.parquet")
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    cal = core()["cal_series"]
    sub = f[f.series_row % 97 == 0].merge(dim[["Series_ID", "Sector_Name"]], on="Series_ID")
    for k in "EVS":
        for nm, lo in (("lo", 1), ("hi", 0)):
            off = np.array([cal[k]["all" if k == "S" else sec][nm][h - 1] for sec, h in zip(sub.Sector_Name, sub.horizon)])
            off = np.minimum(off, 0) if lo else np.maximum(off, 0)
            got = np.rint(sub[k].to_numpy() * np.exp(off))
            tol = np.ceil(0.5 * np.exp(np.abs(off)) + 1)               # the export rounds an unrounded forecast, the browser the whole-person one
            assert (np.abs(got - sub[f"{k}_{nm}"].to_numpy()) <= tol).all(), (k, nm)


def test_state_shards_hold_every_series_and_equal_the_forecast():
    need(EXPORTS / "forecast_series.parquet")
    need(EXPORTS / "demand_index.parquet")
    f = pd.read_parquet(EXPORTS / "forecast_series.parquet")
    di = pd.read_parquet(EXPORTS / "demand_index.parquet")
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    tot = 0
    for st in C.STATES:
        sh = json.loads((DATA / "shards" / (re.sub(r"[^a-z0-9]+", "-", st.lower()).strip("-") + ".json")).read_text(encoding="utf-8"))
        assert sh["state"] == st and len(sh["ids"]) == (dim.State_Name == st).sum()
        rows = dim.index[dim.State_Name == st].to_numpy()
        assert sh["ids"] == dim.Series_ID.to_numpy()[rows].tolist()
        for k in "EVS":
            want = f[f.series_row.isin(rows)].pivot(index="series_row", columns="horizon", values=k).sort_index().to_numpy()
            assert (np.array(sh["fc"][k]) == want).all(), (st, k)
        d = di[di.series_row.isin(rows) & (di.month >= "2021-01")].pivot(index="series_row", columns="month", values="DI").sort_index().to_numpy()
        assert np.allclose(np.array(sh["DI"]), d, atol=0.051), st
        assert len(sh["conf"]["E"]) == len(rows) and all(len(x) == 5 for x in sh["conf"]["V"])
        tot += len(sh["ids"])
    assert tot == C.n_series()


def test_alerts_equal_the_exported_alert_table():
    t = (DATA / "alerts.js").read_text(encoding="utf-8")
    a = json.loads(t[t.index("{"):t.rindex("}") + 1])
    al = pd.read_csv(EXPORTS / "flag_alerts.csv")
    assert len(a["rows"]) == len(al) and {r[1] for r in a["rows"]} == {0, 1, 2} and {r[0] for r in a["rows"]} == {0, 1}
    assert sum(1 for r in a["rows"] if r[0] == 0 and r[1] == 0) == ((al.flag == "Shortage alert") & (al.horizon == 12)).sum()
    assert sum(r[6] for r in a["rows"]) == al.V.sum() and sum(r[7] for r in a["rows"]) == al.S.sum()


def test_capacity_and_rankings_tables_are_the_exported_ones():
    cap, c = core()["capacity"], EXPORTS
    for name in ("india", "sector", "trade", "state", "state_sector", "state_trade"):
        assert len(cap[name]) == len(pd.read_csv(c / f"capacity_gap_{name}.csv")), name
    assert len(core()["rankings"]) == len(pd.read_csv(c / "rankings.csv"))
    di = core()["di_state_trade"]
    assert len(di) == 250 and all(len(v) == 5 and all(0 <= x <= 100 for x in v) for v in di.values())
    assert len(core()["di_district_sector"]) == 317 * 5


def test_text_claims_match_the_evidence():
    chk = json.loads((C.REPORTS / "forecast" / "demand_index_check.json").read_text(encoding="utf-8"))["v_only_vs_three_channels_by_year"]
    corr = [v["correlation"] for v in chk.values()]
    assert 0.88 <= min(corr) and max(corr) <= 0.945, (min(corr), max(corr))                # "correlation 0.89 to 0.94 in 2012-2025"
    p = core()["coverage"]["alert_precision_test"]
    assert 0.65 <= p["1-12|Shortage alert"][0] <= 0.80 and 0.65 <= p["1-12|Oversupply alert"][0] <= 0.80          # "right about seven times in ten"
    import capacity as CAP
    assert abs(np.exp(CAP.SHORT) - 0.6) < 0.01 and abs(np.exp(CAP.SURPLUS) - 1.65) < 0.01                 # "0.6 times ... 1.65 times"
    import early_warning as EW
    assert EW.ALERT == 90 and EW.WATCH == 75 and EW.HIGH_WAPE == 8 and EW.MEDIUM_WAPE == 20                 # "top 10%", "next 15%", "up to 8%", "up to 20%"


# ---- the page --------------------------------------------------------------------------------------------------------------------------------
def test_the_shell_has_the_frame_the_four_filters_and_the_exports():
    h = shell()
    assert '<header class="topbar">' in h and '<aside class="sidebar"' in h and '<footer class="foot"' in h and 'class="main"' in h
    for f in ("f-sector", "f-trade", "f-state", "f-district", "f-csv", "f-json", "lang-toggle", "theme-toggle", "f-reset"):
        assert f'id="{f}"' in h, f
    for p in PAGES:
        assert f'data-page="{p}"' in h, p
    assert "{CSS}" not in h and "{JS}" not in h and "{CORE}" not in h and "{ALERTS}" not in h and "{LOGO}" not in h
    assert re.search(r'data/core\.js\?v=[0-9a-f]{8}', h) and re.search(r'dashboard\.js\?v=[0-9a-f]{8}', h)
    assert "Simulated data" in h and 'class="skip"' in h and 'aria-live="polite"' in h


def test_the_script_has_every_page_the_filters_the_shards_and_both_downloads():
    s = js()
    for p in PAGES:
        assert f"render.{p} = " in s, p
    for token in ("shard(", "downloadCsv", "downloadJson", "location.hash", "p.trade", "p.district", "p.state", "p.sector"):
        assert token in s, token
    assert "Math.random" not in s and "eval(" not in s and "innerHTML = esc" not in s
    assert "xgboost" not in s.lower()
    assert not re.search(r"\[\s*-?\d+(\.\d+)?(\s*,\s*-?\d+(\.\d+)?){6,}\s*\]", s), "a literal array of numbers"


def test_every_text_has_a_hindi_translation():
    s = js()
    hi = dict(re.findall(r'^    "((?:[^"\\]|\\.)*)": "((?:[^"\\]|\\.)*)"', s, re.M))
    assert len(hi) > 150
    keys = set()
    for m in re.finditer(r'\bt(?:f)?\(\s*"((?:[^"\\]|\\.)*)"', s):
        keys.add(json.loads('"' + m.group(1) + '"'))
    for m in re.finditer(r'data-t="([^"]+)"', (ROOT / "src" / "v4" / "dashboard_shell.html").read_text(encoding="utf-8")):
        keys.add(m.group(1))
    for sector in core()["meta"]["sectors"]:
        keys.add(sector)
    keys -= {"Loading…"}
    missing = sorted(k for k in keys if json.dumps(k, ensure_ascii=False)[1:-1] not in hi)
    assert not missing, missing
    plain = {"CSV", "JSON"}
    assert all(re.search(r"[ऀ-ॿ]", v) or k in plain for k, v in hi.items()), [k for k, v in hi.items() if not re.search(r"[ऀ-ॿ]", v) and k not in plain]


def test_the_dashboard_has_a_hindi_name_for_every_state_district_and_trade():
    t = (DATA / "names_hi.js").read_text(encoding="utf-8")
    hi = json.loads(t[t.index("{"):t.rindex("}") + 1])
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    for col in ("State_Name", "District_Name", "Trade_Name"):
        for n in dim[col].unique():
            assert re.search(r"[ऀ-ॿ]", hi.get(n, "")), n
    assert 'src="data/names_hi.js' in shell()


def test_the_files_the_browser_loads_stay_within_the_size_budget():
    assert (DATA / "core.js").stat().st_size < 1.5e6 and (DATA / "alerts.js").stat().st_size < 3e5
    sizes = [p.stat().st_size for p in (DATA / "shards").glob("*.json") if p.name != "index.json"]
    assert len(sizes) == 10 and max(sizes) < 6e6 and sum(sizes) < 30e6
    assert (DASH / "dashboard.js").stat().st_size < 150e3 and (DASH / "dashboard.css").stat().st_size < 50e3


def test_the_map_page_is_wired_to_the_map_data_and_the_state_borders():
    js_ = js()
    assert "render.map = " in js_ and "loadMap()" in js_ and 'getAttribute("data-map")' in js_ and "M.borders" in js_ and "mapVal(" in js_
    assert re.search(r'<body data-map="\.\./data/map_data\.js\?v=[0-9a-f]{8}"', shell()) and 'data-page="map"' in shell()
    t = (ROOT / "app" / "data" / "map_data.js").read_text(encoding="utf-8")
    md = json.loads(t[t.index("{"):t.rindex("}") + 1])
    assert md["borders"].startswith("M") and md["borders"].count("M") > 60 and len(md["districts"]) == 317
    assert ".mborder" in (DASH / "dashboard.css").read_text(encoding="utf-8") and ".mborder" in (ROOT / "app" / "assets" / "styles.css").read_text(encoding="utf-8")


def test_the_severity_ranking_uses_the_capacity_inputs_of_the_exports():
    need(EXPORTS / "capacity_series.parquet")
    cap = pd.read_parquet(EXPORTS / "capacity_series.parquet")
    tab = core()["severity_district_sector"]
    assert len(tab) == 317 * 5 and [b[0] for b in core()["meta"]["severity_bands"]] == ["severe", "high", "moderate"]
    for key in ("118|Construction", "555|Healthcare", "7|IT-ITeS"):
        if key not in tab:
            continue
        d, sec = key.split("|")
        g = cap[(cap.District_LGD_Code == int(d)) & (cap.Sector_Name == sec)]
        v = tab[key]
        assert v[0] == g[g.year == 2026].seats.sum() and abs(v[1] - g[g.year == 2026].expected_certified.sum()) < 0.2
        assert all(abs(v[2 + i] - g[g.year == 2026 + i].avg_vacancies.sum()) < 0.2 for i in range(5))
    j = js()
    assert "function severityRows" in j and "function scoreRows" in j and "Math.log(ratio)" in j and "severity_bands" in j and 'render.ranking' in j


def test_the_data_says_it_is_simulated_and_carries_the_hashes():
    m = core()["meta"]
    assert m["simulated"] is True and m["series"] == C.n_series() and len(m["states"]) == 10 and len(m["districts"]) == 317 and len(m["trades"]) == 25
    man = json.loads((C.DATA / "FORECAST_MANIFEST.json").read_text(encoding="utf-8"))
    assert m["manifest"]["generated_at_utc"] == man["generated_at_utc"], "the dashboard was built from an older forecast: re-run src/v4/build_dashboard.py"
    assert all(len(v) == 16 for v in m["files"].values()) and "forecast_rollups.csv.gz" in m["files"]


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except unittest.SkipTest as e:
                print("SKIP", name, e)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e)[:300])
    sys.exit(1 if fails else 0)
