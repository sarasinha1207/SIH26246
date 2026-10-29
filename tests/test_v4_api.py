"""v4 phase 9 tests: the read-only forecast API returns the exported numbers and refuses what it should, the API page documents what exists and quotes real output,
the deployment stays within its size and speed budget, and the pages meet the accessibility checks that can be made without a browser.
Runs under pytest or standalone: python tests/test_v4_api.py"""
import functools
import gzip
import http.client
import json
import re
import subprocess
import shutil
import sys
import threading
import time
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
EXP = ROOT / "data" / "v4" / "exports"
sys.path.insert(0, str(APP / "api"))
sys.path.insert(0, str(ROOT / "src" / "app"))
sys.path.insert(0, str(ROOT / "tests"))
import _guard  # noqa: E402

_guard.skip_module_unless(APP / "dashboard" / "data" / "core.js", EXP / "forecast_rollups.csv.gz", why="needs the v4 dashboard data and the phase 6 exports")
import _v4api as A  # noqa: E402

ENDPOINTS = ["forecast", "flags", "demand-index", "capacity-gap", "severity", "meta"]


def call(endpoint, qs="", ip="10.0.0.1", method="GET", limiter=None):
    code, headers, body = A.respond(endpoint, qs, ip, method, limiter=limiter or A.Limiter(per_minute=1000, per_day=10 ** 6))
    return code, headers, (json.loads(body) if body else None)


def rollups():
    return pd.read_csv(EXP / "forecast_rollups.csv.gz", low_memory=False)


# ---- the numbers are the exported ones ---------------------------------------------------------------------------------------------------------------
def test_forecast_equals_the_roll_up_export_with_both_ranges():
    r = rollups()
    code, _, d = call("forecast", "state=Kerala&sector=Healthcare&measure=E&horizon=12,60")
    assert code == 200 and d["ok"] is True and d["data_simulated"] is True and d["level"] == "state_sector" and d["forecast_origin"] == "2025-12"
    for row in d["data"]:
        e = r[(r.level == "state_sector") & (r.State_Name == "Kerala") & (r.Sector_Name == "Healthcare") & (r.horizon == row["horizon"])].iloc[0]
        c = row["employed_workers"]
        assert c["point"] == e.E and abs(c["usual_90"][0] - e.E_lo) <= 1 and abs(c["usual_90"][1] - e.E_hi) <= 1 and abs(c["wide_90"][0] - e.E_lo_wide) <= 1 and abs(c["wide_90"][1] - e.E_hi_wide) <= 1
        assert c["usual_90"][0] <= c["point"] <= c["usual_90"][1] and c["wide_90"][0] <= c["point"] <= c["wide_90"][1]
        assert row["month"] == {12: "2026-12", 60: "2030-12"}[row["horizon"]]
    code, _, d = call("forecast", "")                                                  # India, all measures, default horizons
    i = r[(r.level == "india") & (r.horizon == 36)].iloc[0]
    row = [x for x in d["data"] if x["horizon"] == 36][0]
    assert d["level"] == "india" and row["employed_workers"]["point"] == i.E and row["job_vacancies"]["point"] == i.V and row["registered_job_seekers"]["point"] == i.S


def test_series_forecast_and_the_district_trade_range():
    code, _, d = call("forecast", "district=118&trade=CON-7111&horizon=24")
    assert code == 200 and d["level"] == "series" and d["scope"]["district"] == "Agra" and d["scope"]["trade_name"] == "House Builders"
    cell = d["data"][0]["employed_workers"]
    assert cell["usual_90"][0] <= cell["point"] <= cell["usual_90"][1] and cell["wide_90"] is not None
    code, _, d = call("forecast", "state=Kerala&trade=HLT-2221")
    assert d["level"] == "state_subset" and d["data"][0]["employed_workers"]["usual_90"] is None and any("No checked 90% range" in n for n in d["notes"])
    code, _, d = call("forecast", "state=Kerala&sector=Healthcare&detail=series&limit=3&offset=1&horizon=60&measure=V")
    assert d["level"] == "series" and len(d["series"]) == 3 and d["series_total"] == 14 * 5 and d["series"][0]["confidence_by_12_month_band"]["job_vacancies"]["1-12"] in ("high", "medium", "low")
    code, _, d2 = call("forecast", "state=Kerala&sector=Healthcare&detail=series&limit=3&offset=0&horizon=60&measure=V")
    assert d2["series"][1]["series_id"] == d["series"][0]["series_id"]                       # offset pages through the same list


def test_flags_equal_the_alert_table_and_the_series_flags_are_percentiles():
    al = pd.read_csv(EXP / "flag_alerts.csv")
    g = al[(al.State_Name == "Tamil Nadu") & (al.horizon == 12)]
    code, _, d = call("flags", "state=Tamil%20Nadu&horizon=12&limit=1000")
    assert d["total"] == len(g) and d["total"] == len(d["data"])
    assert sum(1 for x in d["data"] if x["alert"] == "shortage") == (g.flag == "Shortage alert").sum()
    code, _, d = call("flags", "state=Tamil%20Nadu&horizon=12&type=oversupply&limit=5")
    assert all(x["alert"] == "oversupply" and x["percentile"] <= 10 for x in d["data"]) and len(d["data"]) <= 5
    code, _, d = call("flags", "district=118&trade=CON-7111&months=1,12,60")
    assert [x["horizon"] for x in d["data"]] == [1, 12, 60] and all(0 <= x["percentile"] <= 100 and x["flag"] for x in d["data"])


def test_demand_index_and_capacity_gap_equal_the_exports():
    r = rollups()
    code, _, d = call("demand-index", "sector=Healthcare&from=2026-12&to=2030-12")
    want = r[(r.level == "sector") & (r.Sector_Name == "Healthcare") & r.month.str.endswith("-12")].set_index("month").DI
    for x in d["data"]:
        assert abs(x["demand_index"] - want[x["month"]]) < 0.051 and x["forecast"] is True
    code, _, d = call("demand-index", "state=Kerala&trade=HLT-2221")
    assert d["level"] == "state_trade" and len(d["data"]) == 5 and all(0 <= x["demand_index"] <= 100 for x in d["data"])
    code, _, d = call("demand-index", "district=118&trade=CON-7111&resolution=monthly&from=2030-10")
    assert [x["month"] for x in d["data"]] == ["2030-10", "2030-11", "2030-12"]
    cap = pd.read_csv(EXP / "capacity_gap_sector.csv")
    code, _, d = call("capacity-gap", "sector=Construction&year=2026,2030")
    c = cap[cap.Sector_Name == "Construction"].set_index("year")
    assert [x["year"] for x in d["data"]] == [2026, 2030] and all(abs(x["certified_per_opening"] - c.loc[x["year"], "supply_per_opening"]) < 1e-3 for x in d["data"])
    code, _, d = call("capacity-gap", "district=118&trade=CON-7111")
    assert d["level"] == "series" and len(d["data"]) == 5 and d["data"][0]["seats"] > 0
    code, _, m = call("meta")
    assert len(m["districts"]) == 317 and len(m["trades"]) == 25 and len(m["states"]) == 10 and m["measures"]["E"] == "employed_workers" and m["files"]


def test_severity_ranking_equals_the_capacity_tables_and_orders_correctly():
    import math
    cap = pd.read_csv(EXP / "capacity_gap_trade.csv")
    code, _, d = call("severity", "level=trade&order=under&year=2030&limit=25")
    assert code == 200 and d["total"] == 25 and d["data"][0]["rank"] == 1 and d["order"] == "under"
    for r in d["data"]:
        c = cap[(cap.Trade_Code == r["trade"]) & (cap.year == 2030)].iloc[0]
        assert abs(r["certified_per_opening"] - c.supply_per_opening) < 1e-3 and abs(r["score"] - math.log(c.supply_per_opening)) < 2e-3 and abs(r["average_monthly_openings"] - c.avg_vacancies) < 0.2
        assert r["direction"] == ("undersupply" if r["score"] < 0 else "oversupply") or r["severity"] == "balanced"
        assert r["severity"] == next((n for n, v in A.core()["meta"]["severity_bands"] if abs(r["score"]) >= v), "balanced")
    sc = [r["score"] for r in d["data"]]
    assert sc == sorted(sc)
    over = call("severity", "level=trade&order=over&limit=25")[2]["data"]
    assert [r["score"] for r in over] == sorted([r["score"] for r in over], reverse=True) and {r["trade"] for r in over} == {r["trade"] for r in d["data"]}
    big = call("severity", "level=trade&order=severity&limit=25")[2]["data"]
    assert [abs(r["score"]) for r in big] == sorted([abs(r["score"]) for r in big], reverse=True)
    st = pd.read_csv(EXP / "capacity_gap_state_trade.csv")
    code, _, d = call("severity", "level=state_trade&sector=Construction&year=2026&limit=500")
    assert d["total"] == 50 and all(abs(r["certified_per_opening"] - st[(st.State_Name == r["state"]) & (st.Trade_Code == r["trade"]) & (st.year == 2026)].supply_per_opening.iloc[0]) < 1e-3 for r in d["data"])
    ser = pd.read_parquet(EXP / "capacity_series.parquet") if (EXP / "capacity_series.parquet").exists() else None
    if ser is not None:
        code, _, d = call("severity", "level=district_sector&sector=Healthcare&limit=500")
        assert d["total"] == 317
        r = d["data"][0]
        g = ser[(ser.District_LGD_Code == r["district_lgd"]) & (ser.Sector_Name == "Healthcare") & (ser.year == 2030)]
        assert abs(r["average_monthly_openings"] - g.avg_vacancies.sum()) < 0.2 and abs(r["seats"] - g.seats.sum()) < 1
        code, _, d = call("severity", "level=district&state=Kerala&limit=100")
        assert d["total"] == 14
    code, _, d = call("severity", "level=series&state=Kerala&limit=3")
    assert d["total"] == 14 * 25 or d["total"] > 300
    assert call("severity", "level=series")[0] == 400 and call("severity", "level=district&trade=HLT-2221")[0] == 400 and call("severity", "order=sideways")[0] == 400 and call("severity", "year=2026,2027")[0] == 400


# ---- what it refuses ----------------------------------------------------------------------------------------------------------------------------------
def test_bad_requests_are_refused_with_a_clear_message():
    for ep, qs in [("forecast", "bogus=1"), ("forecast", "state=Atlantis"), ("forecast", "state=Kerala&state=Delhi"), ("forecast", "horizon=0"), ("forecast", "horizon=61"), ("forecast", "horizon=a,b"), ("forecast", "measure=X"),
                   ("forecast", "district=999999"), ("forecast", "district=118&state=Kerala"), ("forecast", "trade=HLT-2221&sector=Construction"), ("forecast", "detail=series"), ("forecast", "detail=everything"),
                   ("forecast", "state=Kerala&detail=series&limit=0"), ("forecast", "state=Kerala&detail=series&limit=201"), ("flags", "horizon=7"), ("flags", "type=both"), ("flags", "limit=5000"),
                   ("demand-index", "district=118"), ("demand-index", "from=2026-13"), ("capacity-gap", "year=2031"), ("meta", "x=1"), ("forecast", "state=" + "a" * 2000)]:
        code, _, d = call(ep, qs)
        assert code == 400 and d["ok"] is False and d["error"] == "bad_parameter" and d["message"], (ep, qs, code)
    assert call("forecast", "district=118&trade=CON-7111&state=uttar%20pradesh")[0] == 200                  # names are not case sensitive
    code, _, d = call("demand-index", "from=2031-01&to=2031-12")
    assert code == 404 and d["error"] == "not_found"


def test_only_get_and_options_are_allowed_and_cors_is_open_for_reads():
    code, h, d = call("forecast", "", method="POST")
    assert code == 405 and h["Allow"] == "GET, OPTIONS" and d["error"] == "method_not_allowed"
    for m in ("PUT", "DELETE", "PATCH"):
        assert call("meta", "", method=m)[0] == 405
    code, h, d = call("forecast", "", method="OPTIONS")
    assert code == 204 and d is None and h["Access-Control-Allow-Origin"] == "*" and "GET" in h["Access-Control-Allow-Methods"]
    code, h, d = call("forecast", "")
    assert h["Access-Control-Allow-Origin"] == "*" and h["X-Content-Type-Options"] == "nosniff" and "application/json" in h["Content-Type"] and "max-age" in h["Cache-Control"]


def test_rate_limits_per_address_and_per_day():
    lim = A.Limiter(per_minute=3, per_day=10)
    t = 1_000_000.0
    got = [A.respond("meta", "", "1.1.1.1", "GET", limiter=lim, now=t + i)[0] for i in range(5)]
    assert got == [200, 200, 200, 429, 429]
    code, h, _ = A.respond("meta", "", "1.1.1.1", "GET", limiter=lim, now=t + 70)
    assert code == 200                                                                    # a minute later the address may ask again
    assert A.respond("meta", "", "2.2.2.2", "GET", limiter=lim, now=t + 1)[0] == 200                  # another address is not affected
    lim = A.Limiter(per_minute=100, per_day=4)
    codes = [A.respond("meta", "", f"9.9.9.{i}", "GET", limiter=lim, now=t)[0] for i in range(6)]
    assert codes == [200, 200, 200, 200, 429, 429]
    code, h, body = A.respond("meta", "", "1.1.1.1", "GET", limiter=lim, now=t)
    assert json.loads(body)["error"] == "daily_cap" and h["Retry-After"] == "60"


def test_an_unreadable_data_file_gives_a_safe_error_not_a_path():
    saved = A.DATA
    try:
        A.DATA = ROOT / "no-such-folder"
        A.core.cache_clear()
        code, _, d = call("forecast", "")
        assert code == 500 and d["error"] == "server_error" and "no-such-folder" not in json.dumps(d)
    finally:
        A.DATA = saved
        A.core.cache_clear()


def test_the_local_server_routes_the_api_like_vercel_does():
    import serve
    srv = serve.Server(("127.0.0.1", 0), functools.partial(serve.Handler, directory=str(APP)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
        c.request("GET", "/api/meta")
        r = c.getresponse()
        assert r.status == 200 and json.loads(r.read())["ok"] is True and "json" in r.getheader("Content-Type")
        c.request("GET", "/api/forecast?state=Kerala&bogus=1")
        r = c.getresponse()
        assert r.status == 400
        r.read()
        c.request("POST", "/api/forecast", body="{}")
        r = c.getresponse()
        assert r.status == 405
        r.read()
        c.request("GET", "/api/_v4api.py")
        r = c.getresponse()
        assert r.status == 404                                                            # the source is not served
        r.read()
    finally:
        srv.shutdown()


# ---- deployment ---------------------------------------------------------------------------------------------------------------------------------------
def test_vercel_config_registers_every_api_function_with_its_data():
    cfg = json.loads((APP / "vercel.json").read_text(encoding="utf-8"))
    for name in ENDPOINTS:
        f = APP / "api" / f"{name}.py"
        assert f.exists(), name
        src = f.read_text(encoding="utf-8")
        assert f'handler = _v4api.make_handler("{name}")' in src and "import" in src
        c = cfg["functions"][f"api/{name}.py"]
        assert c["maxDuration"] <= 10 and "dashboard/data/**" in c["includeFiles"] and "_v4api.py" in c["includeFiles"], name
    lib = (APP / "api" / "_v4api.py").read_text(encoding="utf-8")
    imports = set(re.findall(r"^(?:import|from) (\w+)", lib, re.M))
    std = set(sys.stdlib_module_names)
    assert imports <= std, imports - std                                                  # standard library only: nothing to install on Vercel
    assert not (APP / "api" / "__init__.py").exists()


def test_the_deployment_stays_within_its_size_and_speed_budget():
    files = [p for p in APP.rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith("_a11y")]
    tracked = subprocess.run(["git", "ls-files", "app"], cwd=ROOT, capture_output=True, text=True).stdout.split() if shutil.which("git") else None
    if tracked:
        files = [p for p in files if p.relative_to(ROOT).as_posix() in set(tracked) or p.name == "names_hi.js"]
    total = sum(p.stat().st_size for p in files)
    assert total < 60e6, total / 1e6                                                      # well under the platform's upload limit
    assert max(p.stat().st_size for p in files) < 6e6
    gz = lambda p: len(gzip.compress(p.read_bytes(), 6))
    for page, budget in (("index.html", 450e3), ("about.html", 100e3), ("resources.html", 100e3), ("docs/api.html", 100e3), ("dashboard/index.html", 450e3)):
        h = (APP / page).read_text(encoding="utf-8")
        parts = [APP / page] + [(APP / page).parent / m.split("?")[0] for m in re.findall(r'(?:src|href)="([^"]+\\.(?:js|css))(?:\\?[^"]*)?"', h) if not m.startswith("http")]
        assert sum(gz(p) for p in parts) < budget, (page, sum(gz(p) for p in parts))
    A.core.cache_clear()
    A.shard.cache_clear()
    t = time.time()
    A.core()
    A.shard("Uttar Pradesh")                                                              # the largest state, cold
    assert time.time() - t < 2.0, time.time() - t
    t = time.time()
    for _ in range(20):
        call("forecast", "state=Kerala&sector=Healthcare")
    assert (time.time() - t) / 20 < 0.05


# ---- the API page ---------------------------------------------------------------------------------------------------------------------------------------
def page():
    return (APP / "docs" / "api.html").read_text(encoding="utf-8")


def test_the_api_page_documents_every_endpoint_and_parameter():
    h = page()
    main = h[h.index("<main"):h.index("</main>")]
    for ep in ENDPOINTS:
        assert f"<code>/api/{ep}</code>" in main, ep
    src = (APP / "api" / "_v4api.py").read_text(encoding="utf-8")
    for fn, name in (("api_forecast", "forecast"), ("api_flags", "flags"), ("api_demand_index", "demand-index"), ("api_capacity_gap", "capacity-gap"), ("api_severity", "severity")):
        allowed = re.search(rf'def {fn}\(q\):\n(?:    """.*\n)?    q = parse_query\(q, \(([^)]*)\)', src).group(1)
        for p in re.findall(r'"(\w+)"', allowed):
            assert f"<code>{p}</code>" in main, (name, p)                                   # every accepted parameter is documented
    for p in ("measure", "horizon", "detail", "type", "resolution", "limit", "offset", "state", "district", "sector", "trade", "level", "order", "year"):
        assert f"<code>{p}</code>" in main, p
    for status in ("200", "400", "404", "405", "429"):
        assert f"<code>{status}</code>" in main, status
    assert "simulated" in main and "<h1" in main and main.count("<h1") == 1 and 'class="skip"' in h
    assert 'href="../dashboard/index.html">Open dashboard' in h


def test_the_try_it_links_work_and_the_example_is_real_output():
    h = page()
    for href in re.findall(r'href="\.\./(api/[^"]+)"', h):
        ep, _, qs = href[len("api/"):].partition("?")
        code, _, d = call(ep, qs.replace("&amp;", "&"))
        assert code == 200 and d["ok"], href
    ex = h[h.index('aria-label="Example request and response"'):h.index("</pre>")]
    ex = ex.replace("&amp;", "&")
    code, _, d = call("forecast", "state=Kerala&sector=Healthcare&measure=E&horizon=12,60")
    assert "GET /api/forecast?state=Kerala&sector=Healthcare&measure=E&horizon=12,60" in ex
    assert f'"employed_workers": {d["last_observed"]["employed_workers"]}' in ex
    for row in d["data"]:
        c = row["employed_workers"]
        assert f'"point": {c["point"]}, "usual_90": [{c["usual_90"][0]}, {c["usual_90"][1]}], "wide_90": [{c["wide_90"][0]}, {c["wide_90"][1]}]' in ex, row


def test_the_api_page_is_in_the_build_the_footer_and_hindi():
    import i18n
    h = page()
    assert "data-hi=" in h and h.count("data-hi=") > 25
    src = (ROOT / "src" / "app" / "pages" / "api.html").read_text(encoding="utf-8").replace("{P}", "../")
    items, _ = i18n.units(src)
    import i18n_hi
    missing = [k for _, k in items if k not in i18n_hi.PAGE]
    assert not missing, missing[:3]
    for rel in ("index.html", "about.html", "resources.html", "docs/api.html"):
        t = (APP / rel).read_text(encoding="utf-8")
        assert 'href="' + ("../" if "/" in rel else "") + 'docs/api.html">' in t, rel


def test_the_readme_counts_and_links_are_right():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    files = sorted((ROOT / "tests").glob("test_*.py"))
    n = sum(len(re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.M)) for f in files)
    assert f"**{n} automated tests in {len(files)} files.**" in readme and f"{n} automated tests;" in readme, (n, len(files))
    for rel in re.findall(r"\]\(((?:docs|app)/[^)]+)\)", readme):
        assert (ROOT / rel).exists(), rel
    for f in files:                                                                       # every test file is named in the table
        assert f.name in readme or f.stem.replace("test_", "") in readme, f.name
    for v in ("317", "7,925", "24,72,600", "4.64%", "16.15%", "13.14%", "87%", "submitted-v1"):
        assert v in readme, v
    plan = (ROOT / "docs" / "v4-implementation-plan.md").read_text(encoding="utf-8")
    assert "### Phase 9:" in plan and "Result" in plan[plan.index("### Phase 9:"):plan.index("## Risks")]


# ---- accessibility checks that need no browser ------------------------------------------------------------------------------------------------------
def test_pages_have_a_language_a_skip_link_landmarks_and_ordered_headings():
    from bs4 import BeautifulSoup
    for rel in ("index.html", "about.html", "resources.html", "docs/api.html", "dashboard/index.html"):
        soup = BeautifulSoup((APP / rel).read_text(encoding="utf-8"), "html.parser")
        assert soup.html.get("lang") and soup.title and soup.title.string.strip(), rel
        assert soup.find("a", class_="skip") and soup.find("main") or soup.find(id="main") or soup.find(id="view"), rel
        assert soup.find("meta", attrs={"name": "viewport"}) and "user-scalable=no" not in str(soup.find("meta", attrs={"name": "viewport"})), rel      # zoom stays possible
        last = 0
        for hd in soup.find_all(re.compile(r"^h[1-6]$")):
            n = int(hd.name[1])
            assert not last or n <= last + 1, (rel, hd.name, hd.get_text()[:40])
            last = n
        assert not [i for i in soup.find_all("img") if not i.has_attr("alt")], rel
        ids = [t["id"] for t in soup.find_all(id=True)]
        assert len(ids) == len(set(ids)), rel
    d = BeautifulSoup((APP / "index.html").read_text(encoding="utf-8"), "html.parser")
    f = d.find(id="map-find")
    assert f and d.find("label", attrs={"for": "map-find"}), "the map has a keyboard way to a district"


def test_dashboard_rows_and_charts_are_operable_without_a_mouse():
    js = (APP / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
    assert "function keyboardRows" in js and 'e.key === "Enter"' in js and "tr.tabIndex = 0" in js
    assert 'role: "img"' in js and 'class="sr-only"' in js                                  # charts have a name and a text summary
    assert '<th scope="row">' in js                                                       # key-value tables have row headers
    css = (APP / "dashboard" / "dashboard.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css and "focus-visible" in css
    audit = ROOT / "tests" / "a11y_audit.js"
    node = shutil.which("node")
    assert audit.exists()
    if node:
        assert subprocess.run([node, "--check", str(audit)], capture_output=True).returncode == 0


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
                print("FAIL", name, repr(e)[:400])
    sys.exit(1 if fails else 0)
