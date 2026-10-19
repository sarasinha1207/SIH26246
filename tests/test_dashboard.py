"""Dashboard tests: the data file matches the project outputs, the shell has the requested frame (top bar, collapsible sidebar, filters, one-line footer, Exit buttons),
the script has every page and the URL filters, and the palette has no green.  Runs under pytest or standalone: python tests/test_dashboard.py"""
import colorsys
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "app" / "dashboard"
FC = ROOT / "outputs" / "forecasts" / "origin_2026-10"
TARGETS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
PAGES = ["overview", "demand", "supply", "gap", "ranking", "warnings", "data"]


def data():
    t = (DASH / "data" / "dash_data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def shell():
    return (DASH / "index.html").read_text(encoding="utf-8")


def test_history_matches_the_panel():
    d = data()
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str}).sort_values("Series_ID").reset_index(drop=True)
    assert [s["id"] for s in d["series"]] == dims.Series_ID.tolist() and len(d["series"]) == 280
    assert [s["low"] for s in d["series"]].count(True) == int(dims.Low_Volume.sum()) == 4
    months = d["meta"]["months"]
    assert len(months) == 190 and months[0] == "2011-01" and months[-1] == d["meta"]["origin"] and len(d["meta"]["fmonths"]) == 12
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet")
    panel = panel[panel.Date == d["meta"]["origin"] + "-01"].set_index("Series_ID")
    for k, col in (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers"), ("W", "Avg_Monthly_Wage_INR"), ("T", "Training_Seats_Sanctioned"), ("C", "Trainees_Certified_Monthly")):
        got = [row[-1] for row in d["hist"][k]]
        assert got == [int(round(panel.loc[s, col])) for s in dims.Series_ID], k
    assert [row[-1] / 10 for row in d["hist"]["U"]] == [round(panel.loc[s, "Unemployment_Rate_Pct"], 1) for s in dims.Series_ID]
    assert all(len(row) == 190 for k in d["hist"] for row in d["hist"][k])


def test_every_forecast_value_equals_forecast_long_csv():
    """All 10,080 rows, not a sample: forecast, lo90, hi90 and confidence are the file's own numbers, unrounded."""
    d = data()
    L = pd.read_csv(FC / "forecast_long.csv")
    ids = [s["id"] for s in d["series"]]
    assert len(L) == d["meta"]["forecast_rows"] == 10080
    for k, tv in TARGETS.items():
        g = L[L.target_variable == tv].set_index(["Series_ID", "horizon"])
        for col, name in (("forecast", "f"), ("lo90", "lo"), ("hi90", "hi")):
            want = [[g.loc[(sid, h), col] for h in range(1, 13)] for sid in ids]
            assert d["fc"][k][name] == want, (k, name)
        assert d["fc"][k]["conf"] == [g.loc[(sid, 1), "confidence"] for sid in ids], k
        assert d["fc"][k]["err"] == [[g.loc[(sid, h), "typical_test_error_pct"] for h in range(1, 13)] for sid in ids], k
        assert all(d["fc"][k]["lo"][i][h] <= d["fc"][k]["f"][i][h] <= d["fc"][k]["hi"][i][h] for i in range(280) for h in range(12))
        # the history line meets the forecast line: last_observed is the last month of the history
        assert [g.loc[(sid, 1), "last_observed"] for sid in ids] == [float(row[-1]) for row in d["hist"][k]], k
    months = L.groupby("horizon").target_month.first().tolist()
    assert d["meta"]["fmonths"] == months and d["meta"]["target_names"] == TARGETS


def test_every_flag_equals_flags_csv_and_the_levels_are_a_lookup_on_its_status():
    d = data()
    W = pd.read_csv(FC / "flags.csv").set_index(["Series_ID", "horizon"])
    st, cx, ch = d["meta"]["status"], d["meta"]["context"], d["meta"]["change"]
    assert len(W) == d["meta"]["flag_rows"] == 3360
    for i, s in enumerate(d["series"]):
        assert d["meta"]["flag_conf"][i] == W.loc[(s["id"], 1), "confidence"]
        assert abs(d["current_ratio"][i] - W.loc[(s["id"], 1), "current_coverage_ratio"]) == 0
        for h in range(12):
            f = d["fl"][i][h]
            r = W.loc[(s["id"], h + 1)]
            assert f[0] == r.forecast_percentile and st[f[1]] == r.forecast_status and cx[f[2]] == r.absolute_context and st[f[3]] == r.current_status and ch[f[4]] == r.change, (s["id"], h)
            assert f[5] == (None if pd.isna(r.historical_precision) else r.historical_precision) and f[6] == r.forecast_coverage_ratio
    th = d["meta"]["thresholds"]
    ctx = lambda x: cx[0 if x >= th["exceed"] else 1 if x >= th["moderate"] else 2 if x >= th["oversupplied"] else 3]       # noqa: E731
    assert (W.forecast_coverage_ratio.map(ctx) == W.absolute_context).all()                              # the cuts reproduce every context in the file
    assert th == {"exceed": 1.0, "moderate": 0.2, "oversupplied": 0.1}
    cls = dict(zip(st, d["meta"]["flag_class"]))
    assert cls["Typical"] is None and cls["Tightest decile"] == ["shortage", "alert"] and cls["Loosest decile"] == ["oversupply", "alert"]
    assert cls["Tight"] == ["shortage", "watch"] and cls["Loose"] == ["oversupply", "watch"]


def test_the_data_is_tied_to_the_forecast_run_by_hash():
    d = data()
    man = json.loads((FC / "manifest.json").read_text(encoding="utf-8"))
    for name in ("forecast_long.csv", "flags.csv"):
        assert hashlib.sha256((FC / name).read_bytes()).hexdigest() == man["files_sha256"][name] == d["meta"]["sources"][name], name
    assert d["meta"]["sources"]["panel_monthly.parquet"] == man["panel_sha256"] == hashlib.sha256((ROOT / "data" / "processed" / "panel_monthly.parquet").read_bytes()).hexdigest()
    assert d["meta"]["origin"] == man["origin"] and d["meta"]["manifest"]["flag_rules"] == man["flag_rules"] and d["meta"]["manifest"]["confidence_rules"] == man["confidence_rules"]


def test_the_script_holds_no_typed_in_model_numbers():
    """The script may do arithmetic on the data file; it may not carry confidence levels, cuts, flag rules or data arrays of its own."""
    js = (DASH / "dashboard.js").read_text(encoding="utf-8")
    assert "Math.random" not in js
    assert not re.search(r"\[\s*-?\d+(\.\d+)?(\s*,\s*-?\d+(\.\d+)?){4,}\s*\]", js), "a literal array of numbers"
    assert not re.search(r"""confChip\(["']""", js) and not re.search(r"""return ["'](high|medium|low)["']""", js), "a typed-in confidence level"
    assert "r >= 1 ?" not in js and "r >= 0.2" not in js and "r >= 0.1" not in js, "typed-in coverage cuts"
    assert "f[2] >= 2" not in js and "f[2] === 0" not in js, "an invented alert rule: the level must be read from flags.csv"
    assert "FLAGC[" in js and "TH.exceed" in js and "D.fc[k].conf" in js and "D.meta.flag_conf" in js
    assert "xgboost" not in js and "xgboost" not in shell(), "the model name is read from the data file"
    assert "2 to 4%" not in js and "56 districts" not in js and "of 56" not in js and "23" not in re.sub(r"\d{3,}", "", js.split("render.data")[1])


def test_the_shell_has_the_requested_frame_and_is_separate_from_the_public_site():
    h = shell()
    assert '<header class="topbar">' in h and '<aside class="sidebar"' in h and '<footer class="foot"' in h and 'class="main"' in h
    assert 'id="sb-toggle"' in h and 'aria-controls="sidebar"' in h                                   # a collapsible sidebar
    nav = re.findall(r'<a href="#/(\w+)" data-page="(\w+)">', h)
    assert [a for a, _ in nav] == PAGES and all(a == b for a, b in nav)                                # the seven pages, in order
    for sel in ('id="f-sector"', 'id="f-state"', 'id="f-district"', 'id="f-csv"', 'id="f-reset"'):
        assert sel in h, sel
    assert h.count('class="btn-exit"') == 2 and 'id="exit-top"' in h and 'id="exit-side"' in h        # Exit in the top bar and the sidebar
    assert h.count('href="../index.html"') >= 2 and "Logout" not in h and "logout" not in (DASH / "dashboard.js").read_text(encoding="utf-8").lower()
    foot = h[h.index('<footer class="foot"'):h.index("</footer>")]
    assert "<br" not in foot and "<p" not in foot and "<div" not in foot and foot.count("<footer") == 1       # one line
    assert "styles.css" not in h and "site-header" not in h and "site.js" not in h                      # its own layout, not the public header and footer
    assert not re.search(r'type="password"|type="email"', h)
    for token in ("{CSS}", "{JS}", "{DATA}", "{MAP}"):
        assert token not in h
    assert re.search(r'dashboard\.css\?v=[0-9a-f]{8}', h) and re.search(r'dashboard\.js\?v=[0-9a-f]{8}', h)


def test_the_script_has_every_page_the_url_filters_and_csv():
    js = (DASH / "dashboard.js").read_text(encoding="utf-8")
    for page in PAGES:
        assert f"render.{page} = function" in js, page
    for needle in ("location.hash", "sector", "state", "district", "new Blob", "text/csv", "function download", "function warnRows", "function mapView", "e-Shram", "Exit"[:0]):
        assert needle in js, needle
    assert "cur.csv = " in js and js.count("cur.csv = ") >= 7                                          # every page defines its CSV
    assert "ctxOf = function (r) { return r >= TH.exceed ? 0 : r >= TH.moderate ? 1 : r >= TH.oversupplied ? 2 : 3; }" in js     # cuts come from the data file
    if shutil.which("node"):
        r = subprocess.run(["node", "--check", str(DASH / "dashboard.js")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:400]


def test_one_logo_is_used_everywhere_and_the_old_one_is_gone():
    sys.path.insert(0, str(ROOT / "src" / "app"))
    import logo
    for rel in ("index.html", "about.html", "resources.html", "dashboard/index.html"):
        h = (ROOT / "app" / rel).read_text(encoding="utf-8")
        assert logo.SHAPES in h, rel
        assert "M6 25 L15 17" not in h, rel                                                              # the previous mark
    for f in ("favicon.svg", "logo.svg"):
        t = (ROOT / "app" / "assets" / f).read_text(encoding="utf-8")
        assert t == logo.standalone() and "M6 25 L15 17" not in t, f
    assert "{LOGO}" not in shell()


def test_dashboard_palette_has_no_green():
    css = (DASH / "dashboard.css").read_text(encoding="utf-8")
    seen = set(re.findall(r"#[0-9A-Fa-f]{6}\b", css))
    assert len(seen) >= 12
    for c in seen:
        h = c.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        assert not (70 <= hh * 360 <= 175 and ss > 0.12 and 0.08 < ll < 0.97), f"green-looking colour {c}"
    assert not re.search(r"\b(green|teal|emerald|lime|mint|olive)\b", css + (DASH / "dashboard.js").read_text(encoding="utf-8"), flags=re.I)
    for needle in ("grid-template-areas", "html.sb-collapsed", "@media (max-width: 900px)", "prefers-reduced-motion"):
        assert needle in css, needle


if __name__ == "__main__":
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"[PASS] {n}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {n}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {n}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
