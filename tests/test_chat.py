"""Assistant tests: the widget is on every page of both sites, it makes no network request, and its answers on the dashboard are the CSV values.
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
FC = ROOT / "outputs" / "forecasts" / "origin_2026-10"
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


def test_the_facts_sent_with_a_question_are_the_csv_values():
    if not NODE:
        return
    L = pd.read_csv(FC / "forecast_long.csv")
    row = L[(L.Series_ID == "489-MFG") & (L.target_variable == "Active_Job_Vacancies") & (L.horizon == 12)].iloc[0]
    f = ask("dash", ["vacancies forecast for Parbhani in Manufacturing"], {"page": "demand", "p": {"sector": "Manufacturing"}}, facts=True)[0]
    assert len(f) <= 8000
    assert f"forecast {compact(row.forecast)}" in f and f"90% range {compact(row.lo90)} to {compact(row.hi90)}" in f, "the forecast and its range from forecast_long.csv"
    assert "dashboard page 'demand'" in f and "sector Manufacturing" in f and "Absolute context comes from" in f and "alert" in f   # page, filters, definitions and flag facts
    assert "Hello." not in f and "You are welcome" not in f and "I am not a language model" not in f
    p = ask("pub", ["Is the data real?"], None, facts=True)[0]
    assert "simulated" in p and "districts in" in p and len(p) <= 8000


def test_dashboard_alert_answers_equal_flags_csv():
    if not NODE:
        return
    W = pd.read_csv(FC / "flags.csv")
    g = W[(W.sector == "Healthcare") & (W.horizon == 12)]
    cls = {"Tightest decile": "shortage alert", "Tight": "shortage watch", "Loose": "oversupply watch", "Loosest decile": "oversupply alert"}
    n = g.forecast_status.map(cls).value_counts()
    r = ask("dash", ["Shortage alerts in Healthcare"])[0]
    m = re.search(r"(\d+) shortage alerts, (\d+) shortage watches, (\d+) oversupply alerts and (\d+) oversupply watches", r["text"])
    assert m and [int(x) for x in m.groups()] == [int(n.get(k, 0)) for k in ("shortage alert", "shortage watch", "oversupply alert", "oversupply watch")], r["text"]
    alerts = g[g.forecast_status == "Tightest decile"].assign(d=lambda x: (x.forecast_percentile - 50).abs()).sort_values("d", ascending=False)
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv").set_index("Series_ID")
    want = [dims.loc[s, "District_Name"] for s in alerts.Series_ID][:5]
    got = [item.split(",")[0] for item in r["list"]]
    assert got == want[:len(got)] and all("shortage alert" in item for item in r["list"]), (got, want)
    assert r["src"] == "flags.csv" and r["links"][0]["href"].startswith("#/warnings?") and "sector=Healthcare" in r["links"][0]["href"]


def test_dashboard_ranking_and_value_answers_equal_the_csv_files():
    if not NODE:
        return
    W = pd.read_csv(FC / "flags.csv")
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv").set_index("Series_ID")
    g = W[(W.sector == "Construction") & (W.horizon == 12)].sort_values("forecast_percentile", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1
    wb = g[g.Series_ID.map(dims.State_Name) == "West Bengal"]
    r = ask("dash", ["Tightest districts in Construction in West Bengal"])[0]
    top = wb.iloc[0]
    assert r["list"][0].startswith(f"#{int(top['rank'])} {dims.loc[top.Series_ID, 'District_Name']} (West Bengal)"), r["list"][0]
    assert f"{top.forecast_coverage_ratio * 100:,.1f}" in r["list"][0]
    L = pd.read_csv(FC / "forecast_long.csv")
    row = L[(L.Series_ID == "489-MFG") & (L.target_variable == "Active_Job_Vacancies") & (L.horizon == 12)].iloc[0]
    r = ask("dash", ["vacancies forecast for Parbhani in Manufacturing"])[0]
    line = r["list"][0]
    assert f"forecast {compact(row.forecast)}" in line and f"90% range {compact(row.lo90)} to {compact(row.hi90)}" in line and f"{row.typical_test_error_pct:.1f}%" in line and f"{row.confidence} confidence" in line, line
    r = ask("dash", ["How many employed workers in Delhi?"])[0]
    assert "90% range" not in r["list"][0] and any("only for a single district and sector" in x for x in r["list"])
    e = L[(L.target_variable == "Total_Employed_Workers") & (L.horizon == 12) & (L.state == "Delhi")].forecast.sum()
    assert f"forecast {compact(e)}" in r["list"][0], r["list"][0]


def test_dashboard_definitions_use_the_data_files_values_and_the_page_context():
    if not NODE:
        return
    r = ask("dash", ["What is absolute context?", "What does this page show?", "explain relative status"], {"page": "ranking", "p": {}})
    assert "100 or more" in r[0]["text"] and "20 to 100" in r[0]["text"] and "10 to 20" in r[0]["text"] and "under 10" in r[0]["text"], r[0]["text"]
    assert r[1]["text"].startswith("Ranking:"), r[1]["text"]
    assert "tightest decile, tight, typical, loose, loosest decile" in r[2]["text"], r[2]["text"]


def test_public_answers_come_from_the_site_data():
    if not NODE:
        return
    t = (APP / "data" / "site_data.js").read_text(encoding="utf-8")
    sd = json.loads(t[t.index("{"):t.rindex("}") + 1])
    r = ask("pub", ["How accurate is it?", "Is the data real?", "Which sectors are covered?", "What is this project?", "do you sell insurance"])
    a = sd["accuracy"]["original"]
    assert f'typical error {a["E"]["model"]}% against {a["E"]["baseline"]}%' in r[0]["list"][0], r[0]
    assert r[1]["text"].startswith("No."), r[1]
    assert all(s in r[2]["text"] for s in sd["meta"]["sector_list"]) and all(s in r[2]["text"] for s in sd["meta"]["state_list"]), r[2]
    assert f'{sd["meta"]["districts"]} districts' in r[3]["text"] and f'{sd["meta"]["series"]} series' in r[3]["text"], r[3]
    assert r[4]["text"].startswith("I cannot answer that"), r[4]


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
