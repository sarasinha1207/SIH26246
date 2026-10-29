"""Assistant tests: the widget is on every page of both sites, it makes no network request, and its answers are the exported values of the v4 forecast (roll-ups, alerts, rankings, capacity gap).
The answer engine (app/assets/chat.js) is run under node, so the answers checked here are the ones a visitor gets.  Runs under pytest or standalone: python tests/test_chat.py"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
EXP = ROOT / "data" / "v4" / "exports"
NODE = shutil.which("node")


def ask(mode, queries, ctx=None, facts=False):
    args = [NODE, str(ROOT / "tests" / "chat_engine_run.js"), mode, json.dumps(queries)] + ([json.dumps(ctx)] if ctx else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env={**os.environ, **({"CHAT_FACTS": "1"} if facts else {})})
    assert r.returncode == 0, r.stderr[:600]
    return json.loads(r.stdout)


def compact(n):
    a, s = abs(n), "-" if n < 0 else ""
    return f"{s}{a / 1e7:.2f} Cr" if a >= 1e7 else f"{s}{a / 1e5:.2f} L" if a >= 1e5 else f"{s}{a / 1e3:.1f}K" if a >= 1e3 else f"{s}{round(a)}"


def test_the_widget_is_on_every_page_of_both_sites():
    for rel in ("index.html", "about.html", "resources.html", "dashboard/index.html"):
        h = (APP / rel).read_text(encoding="utf-8")
        assert re.search(r'assets/chat\.css\?v=[0-9a-f]{8}', h) and re.search(r'assets/chat\.js\?v=[0-9a-f]{8}', h), rel
        assert "{CHAT" not in h
    assert (APP / "assets" / "chat.js").exists() and (APP / "assets" / "chat.css").exists()


def test_the_assistant_makes_no_network_request_and_types_in_no_data():
    js = (APP / "assets" / "chat.js").read_text(encoding="utf-8")
    for bad in ("XMLHttpRequest", "WebSocket", "sendBeacon", "navigator.", "eval(", "new Function", "document.cookie", "localStorage", "Math.random", "import("):
        assert bad not in js, bad
    calls = re.findall(r"fetch\(([^,)]*)", js)                                                          # the only request is to this site's own /api/chat; the key and Google are the server's business
    assert len(calls) == 2 and all(c.strip() == "API" for c in calls), calls                             # one status check and one question, both to API
    assert 'API = BASE + "api/chat"' in js and "generativelanguage" not in js and "googleapis" not in js and "x-goog" not in js.lower() and "GEMINI_API_KEY" not in js
    assert js.count("innerHTML") == 1                                                                   # only the fixed icon markup; replies are built with textContent
    assert not re.search(r"\[\s*-?\d+(\.\d+)?(\s*,\s*-?\d+(\.\d+)?){3,}\s*\]", js), "a literal array of numbers"
    if NODE:
        r = subprocess.run([NODE, "--check", str(APP / "assets" / "chat.js")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:400]


def rollups():
    return pd.read_csv(EXP / "forecast_rollups.csv.gz", low_memory=False)


def test_the_facts_sent_with_a_question_are_the_exported_values():
    if not NODE:
        return
    r = rollups()
    row = r[(r.level == "state") & (r.State_Name == "Kerala") & (r.horizon == 60)].iloc[0]
    f = ask("dash", ["employed workers in Kerala in 2030"], {"page": "forecast", "p": {"state": "Kerala"}}, facts=True)[0]
    assert len(f) <= 8000
    assert f"{compact(row.E)} forecast for Dec 2030" in f, "the forecast from forecast_rollups.csv.gz"
    assert "dashboard page 'forecast'" in f and "state Kerala" in f and "Demand Index" in f and "capacity gap" in f.lower() and "alerts" in f
    assert "Hello." not in f and "You are welcome" not in f and "I am the assistant" not in f
    p = ask("pub", ["Is the data real?"], None, facts=True)[0]
    assert "simulated" in p and "districts in" in p and len(p) <= 8000


def test_dashboard_value_answers_equal_the_roll_up_export_with_ranges():
    if not NODE:
        return
    r = rollups()
    ans = ask("dash", ["How many employed workers will Kerala have in 2030?", "vacancies of nursing professionals by 2028"], {"page": "overview", "p": {}})
    k = r[(r.level == "state") & (r.State_Name == "Kerala") & (r.horizon == 60)].iloc[0]
    line = ans[0]["list"][0]
    assert f"{compact(k.E)} forecast for Dec 2030" in line and f"usual 90% range {compact(k.E_lo)} to {compact(k.E_hi)}" in line and f"wide {compact(k.E_lo_wide)} to {compact(k.E_hi_wide)}" in line, line
    t = r[(r.level == "trade") & (r.Trade_Code == "HLT-2221") & (r.horizon == 36)].iloc[0]
    assert f"{compact(t.V)} forecast for Dec 2028" in ans[1]["list"][0], ans[1]["list"][0]
    a = ask("dash", ["employed workers in Agra"])[0]
    assert "state's data file" in a["text"] and a["links"][0]["href"].startswith("#/forecast?"), a


def test_dashboard_alert_answers_equal_the_alert_table():
    if not NODE:
        return
    al = pd.read_csv(EXP / "flag_alerts.csv")
    g = al[(al.State_Name == "Tamil Nadu") & (al.horizon == 12)]
    r = ask("dash", ["Shortage alerts in Tamil Nadu"])[0]
    m = re.search(r"(\d+) shortage alerts and (\d+) oversupply alerts", r["text"])
    assert m and [int(x) for x in m.groups()] == [int((g.flag == "Shortage alert").sum()), int((g.flag == "Oversupply alert").sum())], r["text"]
    top = g[g.flag == "Shortage alert"].coverage_pct.max()
    first = g[(g.flag == "Shortage alert") & (g.coverage_pct == top)].District_Name.tolist()
    assert r["list"][0].split(" (")[0] in first and all("shortage alert" in x for x in r["list"]), (r["list"][0], first)
    assert r["src"] == "flag_alerts.csv" and "state=Tamil%20Nadu" in r["links"][0]["href"]


def test_dashboard_ranking_and_capacity_answers_equal_the_exports():
    if not NODE:
        return
    rk = pd.read_csv(EXP / "rankings.csv")
    fastest = rk[rk.ranking.str.startswith("Trades with the fastest vacancy growth")].iloc[0]
    r = ask("dash", ["Which trades are growing fastest?", "Capacity gap in construction", "Where is trained supply most stretched?"])
    assert r[0]["list"][0].startswith("#1 ") and f"({fastest.key})" in r[0]["list"][0] and f"{fastest.value:,.2f}" in r[0]["list"][0], r[0]["list"][0]
    cap = pd.read_csv(EXP / "capacity_gap_sector.csv")
    c = cap[cap.Sector_Name == "Construction"].set_index("year")
    assert f"{c.loc[2026, 'supply_per_opening']:,.2f} certified per opening" in r[1]["text"] and f"{c.loc[2030, 'supply_per_opening']:,.2f} certified per opening" in r[1]["text"], r[1]["text"]
    most = rk[rk.ranking.str.startswith("Trades where trained supply is most stretched")].iloc[0]
    assert f"({most.key})" in r[2]["list"][0], r[2]


def test_severity_answers_equal_the_capacity_tables():
    if not NODE:
        return
    cap = pd.read_csv(EXP / "capacity_gap_trade.csv")
    c30 = cap[cap.year == 2030].sort_values("supply_per_opening")
    r = ask("dash", ["Which trades are most undersupplied?", "most oversupplied trades"], {"page": "ranking", "p": {}})
    assert f"{c30.iloc[0].supply_per_opening:,.2f} per opening" in r[0]["list"][0] and "severe undersupply" in r[0]["list"][0], r[0]["list"][0]
    assert f"{c30.iloc[-1].supply_per_opening:,.2f} per opening" in r[1]["list"][0] and "oversupply" in r[1]["list"][0], r[1]["list"][0]
    assert r[0]["links"][0]["href"].startswith("#/ranking")


def test_dashboard_definitions_use_the_page_context():
    if not NODE:
        return
    r = ask("dash", ["What is the demand index?", "What does this page show?", "explain the capacity gap"], {"page": "ranking", "p": {}})
    assert "0 to 100" in r[0]["text"] and "50 is the median district" in r[0]["text"] and "84 is one standard deviation" in r[0]["text"], r[0]["text"]
    assert r[1]["text"].startswith("Rankings:"), r[1]["text"]
    assert "0.6 times" in r[2]["text"] and "1.65 times" in r[2]["text"] and "held flat" in r[2]["text"], r[2]["text"]


def test_public_answers_come_from_the_site_data():
    if not NODE:
        return
    t = (APP / "data" / "site_data.js").read_text(encoding="utf-8")
    sd = json.loads(t[t.index("{"):t.rindex("}") + 1])
    r = ask("pub", ["How accurate is it?", "Is the data real?", "Which sectors are covered?", "What is this project?", "do you sell insurance", "How many employed workers in India by 2030?", "forecast for Agra construction"])
    a = sd["accuracy"]["test"]
    assert f'typical error {a["E"]["model"]}% against {a["E"]["baseline"]}%' in r[0]["list"][0], r[0]
    assert r[1]["text"].startswith("No."), r[1]
    assert all(s in r[2]["text"] for s in sd["meta"]["sector_list"]) and all(s in r[2]["text"] for s in sd["meta"]["state_list"]), r[2]
    assert f'{sd["meta"]["districts"]} districts' in r[3]["text"] and f'{sd["meta"]["series"]:,} series' in r[3]["text"] and f'{sd["meta"]["trades"]} trades' in r[3]["text"], r[3]
    assert r[4]["text"].startswith("I cannot answer that"), r[4]
    h = sd["headline"]["h60"]["E"]
    assert f"forecast {compact(h['point'])} in December 2030" in r[5]["list"][0] and f"usual 90% range {compact(h['usual'][0])} to {compact(h['usual'][1])}" in r[5]["list"][0], r[5]
    rl = rollups()
    ds = rl[(rl.level == "district_sector") & (rl.District_LGD_Code == 118) & (rl.Sector_Name == "Construction") & (rl.horizon == 60)].iloc[0]
    assert f"{compact(ds.E)} in 60 months" in r[6]["list"][0] and r[6]["text"].startswith("Agra, Uttar Pradesh (Construction)"), r[6]


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
