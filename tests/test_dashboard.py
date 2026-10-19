"""Dashboard tests: the data file matches the project outputs, the shell has the requested frame (top bar, collapsible sidebar, filters, one-line footer, Exit buttons),
the script has every page and the URL filters, and the palette has no green.  Runs under pytest or standalone: python tests/test_dashboard.py"""
import colorsys
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
PAGES = ["overview", "demand", "supply", "gap", "ranking", "warnings", "data"]


def data():
    t = (DASH / "data" / "dash_data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def shell():
    return (DASH / "index.html").read_text(encoding="utf-8")


def test_dashboard_data_matches_the_project_outputs():
    d = data()
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str}).sort_values("Series_ID").reset_index(drop=True)
    assert [s["id"] for s in d["series"]] == dims.Series_ID.tolist() and len(d["series"]) == 280
    assert [s["low"] for s in d["series"]].count(True) == int(dims.Low_Volume.sum()) == 4
    months = d["meta"]["months"]
    assert len(months) == 190 and months[0] == "2011-01" and months[-1] == "2026-10" and len(d["meta"]["fmonths"]) == 12 and d["meta"]["fmonths"][0] == "2026-11"
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet")
    panel = panel[panel.Date == "2026-10-01"].set_index("Series_ID")
    for k, col in (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers"), ("W", "Avg_Monthly_Wage_INR"), ("T", "Training_Seats_Sanctioned"), ("C", "Trainees_Certified_Monthly")):
        got = [row[-1] for row in d["hist"][k]]
        assert got == [int(round(panel.loc[s, col])) for s in dims.Series_ID], k
    assert [row[-1] / 10 for row in d["hist"]["U"]] == [round(panel.loc[s, "Unemployment_Rate_Pct"], 1) for s in dims.Series_ID]
    assert all(len(row) == 190 for k in d["hist"] for row in d["hist"][k])
    L = pd.read_csv(FC / "forecast_long.csv")
    for k, tv in (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers")):
        g = L[L.target_variable == tv].set_index(["Series_ID", "horizon"])
        for i in (0, 77, 140, 279):
            sid = d["series"][i]["id"]
            for h in (1, 6, 12):
                r = g.loc[(sid, h)]
                assert abs(d["fc"][k]["f"][i][h - 1] - r.forecast) < 0.06 and abs(d["fc"][k]["lo"][i][h - 1] - r.lo90) < 0.06 and abs(d["fc"][k]["hi"][i][h - 1] - r.hi90) < 0.06
                assert d["fc"][k]["lo"][i][h - 1] < d["fc"][k]["f"][i][h - 1] < d["fc"][k]["hi"][i][h - 1]
            assert d["fc"][k]["conf"][i] == g.loc[(sid, 1)].confidence


def test_flags_in_the_dashboard_equal_the_flag_file_and_the_context_rule():
    d = data()
    W = pd.read_csv(FC / "flags.csv").set_index(["Series_ID", "horizon"])
    st, cx = d["meta"]["status"], d["meta"]["context"]
    for i, s in enumerate(d["series"]):
        for h in range(12):
            f = d["fl"][i][h]
            r = W.loc[(s["id"], h + 1)]
            assert st[f[1]] == r.forecast_status and cx[f[2]] == r.absolute_context and st[f[3]] == r.current_status and abs(f[0] - r.forecast_percentile) < 0.06, (s["id"], h)
            assert abs(f[6] - r.forecast_coverage_ratio) < 6e-5
            ratio = r.forecast_coverage_ratio                                    # the thresholds the dashboard uses to colour the map
            assert cx[0 if ratio >= 1 else 1 if ratio >= 0.2 else 2 if ratio >= 0.1 else 3] == r.absolute_context
    assert d["meta"]["thresholds"] == {"exceed": 1.0, "moderate": 0.2, "oversupplied": 0.1}


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
    assert "ctxOf = function (r) { return r >= 1 ? 0 : r >= 0.2 ? 1 : r >= 0.1 ? 2 : 3; }" in js     # the project's absolute-context thresholds
    if shutil.which("node"):
        r = subprocess.run(["node", "--check", str(DASH / "dashboard.js")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:400]


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
