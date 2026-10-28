"""Web app tests: every page exists and links resolve, every number comes from the project outputs, the synthetic-data notice is on every page,
the map matches the forecast files, the Hindi text is complete, and no unfinished placeholders other than the documented ones.
Runs under pytest or standalone: python tests/test_app.py"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "app"
PAGES = ["index.html", "about.html", "resources.html"]           # the public pages; the dashboard has its own tests
FC = ROOT / "outputs" / "forecasts" / "origin_2026-10"
V4 = ROOT / "data" / "v4"
sys.path.insert(0, str(ROOT / "src" / "app"))


def data():
    t = (SITE / "data" / "site_data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def map_data():
    t = (SITE / "data" / "map_data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def read(p):
    return (SITE / p).read_text(encoding="utf-8")


def test_pages_exist_and_internal_links_resolve():
    for p in PAGES:
        assert (SITE / p).exists(), p
        html = read(p)
        for href in re.findall(r'(?:href|src)="([^"#?]+)', html):
            if href.startswith(("http", "mailto:")):
                continue
            assert ((SITE / p).parent / href).exists(), f"{p}: broken link {href}"
        for page, anchor in re.findall(r'href="([a-z\-]+\.html)#([\w\-]+)"', html):
            assert f'id="{anchor}"' in read(page), f"{p}: anchor {page}#{anchor} missing"
        for anchor in re.findall(r'href="#([\w\-]+)"', html):
            assert f'id="{anchor}"' in html, f"{p}: anchor #{anchor} missing"


def test_the_public_site_has_three_pages_plus_footer_and_a_dashboard_button():
    for p in PAGES:
        html = read(p)
        assert 'class="btn small nav-cta" href="dashboard/index.html">Open dashboard' in html, p
        assert len(re.findall(r'<nav[^>]*class="nav"', html)) == 1 and "<footer" in html, p
    assert len(list(SITE.glob("*.html"))) == 3 and (SITE / "dashboard" / "index.html").exists()


def test_every_page_says_the_data_is_simulated_and_asks_for_no_login():
    for p in PAGES:
        html = read(p)
        assert "simulated" in html and "are not official statistics" in html, p              # the footer carries the notice on every page
        assert 'class="notice"' not in html and "Demonstration data:" not in html, p        # no strip above the header
        assert not re.search(r"<input[^>]*type=\"password\"|type=\"email\"", html), p
    for p in PAGES:
        assert "No login" in read(p)


def test_site_data_matches_the_forecast_files():
    D = data()
    man = json.loads((V4 / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
    fman = json.loads((V4 / "FORECAST_MANIFEST.json").read_text(encoding="utf-8"))
    m = D["meta"]
    assert (m["series"], m["districts"], m["states"], m["sectors"], m["trades"]) == (7925, 317, 10, 5, 25) == (man["series"], man["districts"], man["states"], man["sectors"], man["trades"])
    assert (m["rows"], m["months"], m["horizons"], m["columns"]) == (2472600, 312, 60, 17) and m["forecast_rows"] == fman["files"]["forecast_series.parquet"]["rows"] == 475500
    assert m["origin"] == "2025-12" and m["first_target"] == "January 2026" and m["last_target"] == "December 2030" and m["synthetic"] is True
    assert sum(m["districts_by_state"].values()) == 317 and len(m["trade_list"]) == 25 and m["data_sha256"] == man["content_sha256"]
    rl = pd.read_csv(V4 / "exports" / "forecast_rollups.csv.gz", low_memory=False)
    ind = rl[rl.level == "india"].set_index("horizon")
    H = D["headline"]
    for h, key in ((12, "h12"), (60, "h60")):
        for k in "EVS":
            assert H[key][k]["point"] == ind.loc[h, k] and H[key][k]["usual"] == [ind.loc[h, f"{k}_lo"], ind.loc[h, f"{k}_hi"]] and H[key][k]["wide"] == [ind.loc[h, f"{k}_lo_wide"], ind.loc[h, f"{k}_hi_wide"]]
        assert abs(H[key]["DI"] - ind.loc[h, "DI"]) < 1e-9
    h = D["hero"]
    assert len(h["V"]["history"]) == 37 and h["V"]["history"][-1] == 100.0 and len(h["V"]["forecast"]) == 60 and h["V"]["forecast_months"][0] == "2026-01" and h["V"]["forecast_months"][-1] == "2030-12"
    assert all(a <= b <= c for a, b, c in zip(h["V"]["lo"], h["V"]["forecast"], h["V"]["hi"])) and all(a <= b <= c for a, b, c in zip(h["S"]["lo"], h["S"]["forecast"], h["S"]["hi"]))
    fs = V4 / "exports" / "forecast_series.parquet"
    if fs.exists():
        f = pd.read_parquet(fs)
        f = f[f.Series_ID == h["series_id"]].sort_values("horizon")
        assert abs(h["V"]["forecast"][-1] - f.V.iloc[-1] / h["V"]["last_value"] * 100) < 0.01 and abs(h["S"]["forecast"][-1] - f.S.iloc[-1] / h["S"]["last_value"] * 100) < 0.01
    assert D["accuracy"]["test"]["E"]["model"] < D["accuracy"]["test"]["E"]["baseline"] and D["accuracy"]["test"]["S"]["model"] < D["accuracy"]["test"]["S"]["baseline"]
    assert "updates" not in D and "snapshot" not in D                # the home page has no Updates or sector-by-sector section


def test_claims_in_the_text_match_the_evidence():
    D = data()
    a, cv = D["accuracy"]["test"], D["accuracy"]["coverage"]["test"]
    ev = pd.read_csv(ROOT / "reports" / "v4" / "evaluation" / "test_metrics.csv")
    ev = ev[(ev.slice == "all") & (ev.band == "all horizons")].set_index("target")
    for k in "EVS":
        assert a[k]["model"] == round(ev.loc[k, "wape_model"], 2) and a[k]["baseline"] == round(ev.loc[k, "wape_best_baseline"], 2)
    home = read("index.html")
    assert round(a["E"]["gain_pct"]) == 18 and '<b class="c-demand">18%</b>' in home
    assert round(a["S"]["gain_pct"]) == 8 and '<b class="c-demand">8%</b>' in home
    assert round(100 * cv["E"]) == 87 and '<b class="c-demand">87%</b>' in home and f"Vacancies {round(100 * cv['V'])}%, job seekers {round(100 * cv['S'])}%" in home
    assert f"{a['E']['model']:.2f}% against {a['E']['baseline']:.2f}%" in home and f"{a['S']['model']:.2f}% against {a['S']['baseline']:.2f}%" in home
    assert a["E"]["model"] < a["E"]["baseline"] and a["S"]["model"] < a["S"]["baseline"]


def hue_of(hexcolor):
    import colorsys
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, ss, ll


def test_the_palette_is_blue_with_one_warm_accent_and_no_green():
    files = [SITE / "assets" / "styles.css", SITE / "assets" / "site.js", SITE / "assets" / "favicon.svg"] + [SITE / p for p in PAGES]
    seen = set()
    for f in files:
        text = f.read_text(encoding="utf-8")
        for c in re.findall(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b", text):
            h, sat, light = hue_of(c)
            seen.add(c.upper())
            assert not (70 <= h <= 175 and sat > 0.12 and 0.08 < light < 0.97), f"{f.name}: green-looking colour {c} (hue {h:.0f})"
        assert not re.search(r"\b(green|teal|emerald|lime|mint|olive)\b", text, flags=re.I) or f.name == "site.js", f.name
    blues = [c for c in seen if 200 <= hue_of(c)[0] <= 235 and hue_of(c)[1] > 0.3]
    assert len(blues) >= 6, "the palette should be dominated by blues"


def test_display_options_are_text_size_theme_and_language_in_the_header_of_every_page():
    for p in PAGES:
        html = read(p)
        head = html[html.index("<header"):html.index("</header>")]
        assert 'class="display-btn"' in head and 'id="display-panel"' in head and 'aria-label="Display options"' in head, p
        assert head.index('class="brand"') < head.index('class="nav-links"') < head.index('class="nav-actions"') < head.index('class="display"'), p     # brand left, pages centre, actions right
        assert 'class="status"' not in head and "Data to" not in head and 'class="pill warn"' not in head, p     # the data-month and Demo data pills are gone
        for needle in ('data-size-step="-1"', 'data-size-step="0"', 'data-size-step="1"', 'data-opt="theme" data-val="light"', 'data-opt="theme" data-val="dark"',
                       'data-opt="lang" data-val="en"', 'data-opt="lang" data-val="hi"'):
            assert needle in head, (p, needle)
        assert 'data-opt="font"' not in head and 'data-opt="motion"' not in head and "contrast" not in head, p
        assert "localStorage" in html and "s.theme==='light'?'light':'dark'" in html, p        # dark by default, saved choice applied before the page paints
    css, js = read("assets/styles.css"), read("assets/site.js")
    assert "grid-template-columns: 1fr auto 1fr" in css and ".nav-links { display: flex; justify-content: center;" in css
    for sel in ('html[data-theme="dark"]', 'html[data-size="xl"]', 'html[lang="hi"]', 'html[data-motion="reduced"]', "prefers-contrast: more"):
        assert sel in css, sel
    assert "localStorage.setItem" in js and re.search(r"try\s*\{\s*localStorage", js) and "Escape" in js and "Noto+Sans+Devanagari" in js


def test_fonts_changed_and_loaded_without_a_build_step():
    for p in PAGES:
        html = read(p)
        assert "family=Geist" in html and "Sora" not in html and "Public+Sans" not in html, p
        assert "media=\"print\" onload=" in html, "font stylesheet must not block the first paint"
    css = read("assets/styles.css")
    assert '--display: "Geist"' in css and '--body: "Geist"' in css and "Noto Sans Devanagari" in css and "Sora" not in css and "Public Sans" not in css


def test_animations_and_interactions_exist_and_respect_the_motion_setting():
    css, js = read("assets/styles.css"), read("assets/site.js")
    for kf in ("@keyframes lineUp", "@keyframes float", "@keyframes pulse", "@keyframes pop", "@keyframes ring", "@keyframes drawIn", "@keyframes dotPop", "@keyframes howBar", ".reveal", ".tl-fill"):
        assert kf in css, kf
    for fn in ("function heroChart", "function reveal", "function counters",
               "function how", "function mapInit", "function mapZoom", "pointermove"):
        assert fn in js, fn
    assert js.count("reduced()") >= 8 and 'html[data-motion="reduced"] *' in css


def test_the_site_has_exactly_the_requested_pages_and_nothing_left_over():
    assert sorted(p.name for p in SITE.glob("*.html")) == ["about.html", "index.html", "resources.html"]
    for gone in ("how-it-works.html", "data-and-accuracy.html"):
        assert not (SITE / gone).exists(), gone
    assert not (SITE / "downloads").exists()
    for p in PAGES:
        html = read(p)
        assert "how-it-works" not in html and "data-and-accuracy" not in html and "downloads/" not in html, p
        nav = html[html.index('class="nav-links"'):html.index("</ul>")]
        if True:
            assert ">Home<" in nav and ">About<" in nav and ">Resources<" in nav and "How it works<" not in nav and "Data and accuracy" not in nav, p
    D = data()
    for k in ("flags", "flag_labels", "downloads", "by_horizon", "noise_floor", "interval_half_width", "typical_error", "updates", "snapshot"):
        assert k not in D, k


def test_about_page_sections_are_in_a_professional_order_with_no_repeated_headings():
    html = read("about.html")
    main = html[html.index("<main"):html.index("</main>")]
    ids = re.findall(r'<section class="(?:section|page-head)[^"]*" id="([\w-]+)"', main)
    assert ids == ["project", "timeline", "dataset", "principles", "engine", "measures", "evaluation", "limits"], ids       # project, overview, data, principles, architecture, measures, results, limits
    assert len(re.findall(r"<section", main)) == 8                                     # the hero is the "About the project" section
    heads = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", main)]
    assert heads == ["Forecasts", "Honest ranges", "Demand and capacity", "How it works", "Dataset used", "Model engine overview and core principles", "Machine learning engine and architecture", "Demand Index, capacity gap and early warnings",
                     "Model evaluation achievements", "What to keep in mind"], heads
    assert re.search(r"<h1[^>]*>About the project</h1>", main) and main.count("<h1") == 1 and "page-head big" in main
    assert 'class="eyebrow"' not in main and "In more detail" not in main                 # no label repeating a heading
    for gone in ("Smart India Hackathon", "SIH26246", "It was built for", "twelve-month forecast", "56 districts", "280 district"):
        assert gone not in main, gone
    assert 'class="toc"' not in main and 'href="#' not in main                           # no jump links in the hero
    hero = main[:main.index('id="timeline"')]
    assert hero.index("<h1") < hero.index('class="grid1"') and hero.count('class="lead"') == 1 and re.search(r'class="lead">\s*<h1', hero)   # cards sit beside the heading
    assert main.count('class="tl-dot"') == 6 and 'class="timeline"' in main and "tl-scroll" in main        # the horizontal timeline
    assert main.count('class="arch-n"') == 6 and 'class="step"' not in main
    # the facts the page states come from the project's documents
    summ = json.loads((ROOT / "reports" / "v4" / "evaluation" / "test_summary.json").read_text(encoding="utf-8"))
    assert f"{len(summ['inputs'])} inputs" in main and "119 candidates" in main and "nine models in the final fit" in main
    assert "475,500".replace(",", "") in main.replace(",", "") and "Trained on 2000 to 2009, tuned on 2010 to 2014, tested once on 2015 to 2019 and once on 2020 to 2025" in main
    assert "20 trials per measure" in main and "three random starts" in main
    tp = json.loads((ROOT / "reports" / "v4" / "evaluation" / "validation_summary.json").read_text(encoding="utf-8"))
    assert tp["fit_targets_to"] == "2009-12" and summ["fit_targets_to"] == "2014-12"


def test_about_dataset_section_matches_the_project_data():
    html = read("about.html")
    sec = html[html.index('id="dataset"'):html.index('id="principles"')]
    man = json.loads((V4 / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
    assert str(man["rows"]) in sec.replace(",", "") and ">312<" in sec and ">17<" in sec and "7,925" in sec and man["months"] == 312
    import pyarrow.parquet as pq
    tp = V4 / "raw" / "trade_monthly_2000_2025.parquet"
    cols = pq.read_schema(tp).names if tp.exists() else None
    if cols is not None:
        assert len(cols) == 17
        for c in cols:
            assert c in sec, c
    dim = pd.read_csv(V4 / "dim_series.csv")
    per = dim.groupby("State_Name").District_LGD_Code.nunique().to_dict()
    assert len(per) == 10 and sum(per.values()) == 317
    for state, n in per.items():
        assert re.search(rf"<td[^>]*>{state}</td>\s*<td[^>]*>{n} of {n}</td>", sec), (state, n)
    for r in dim.drop_duplicates("Trade_Code").itertuples():
        assert r.Sector_Name in sec and f"({r.NCO_Code})" in sec, (r.Sector_Name, r.NCO_Code)
    xw = pd.read_csv(ROOT / "data" / "raw" / "sector_nco_crosswalk.csv")
    assert len(xw) == 25


def test_about_evaluation_figures_match_the_evaluation_outputs():
    html = read("about.html")
    sec = html[html.index('id="evaluation"'):html.index('id="limits"')]
    D = data()["accuracy"]
    ev = ROOT / "reports" / "v4" / "evaluation"
    t = pd.read_csv(ev / "test_metrics.csv")
    t = t[(t.slice == "all")]
    names = {"E": "Employed workers", "S": "Registered job seekers", "V": "Job vacancies"}
    for k in "EVS":
        row = re.search(rf"<td[^>]*>{names[k]}</td>(.*?)</tr>", sec, re.S).group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row)
        g = t[(t.target == k) & (t.band == "all horizons")].iloc[0]
        bias = f"{'+' if g.bias_pct > 0 else '&minus;'}{abs(g.bias_pct):.1f}%"
        assert cells[:4] == [f"{g.wape_model:.2f}%", f"{g.wape_best_baseline:.2f}%", f"{g.improvement_vs_best_baseline_pct:.1f}%", bias], (k, cells)
    by = t[(t.target == "E") & (t.band != "all horizons")].set_index("band").improvement_vs_best_baseline_pct
    assert f"by {round(by['1-12'])}% in the first year and {round(by['49-60'])}% in the fifth" in sec
    s = t[(t.target == "S") & (t.band != "all horizons")].set_index("band").improvement_vs_best_baseline_pct
    assert s["1-12"] < 0 and s["13-24"] < 0 and round(s["37-48"]) == 15 and round(s["49-60"]) == 23 and "15 to 23% better in years four and five" in sec
    st = pd.read_csv(ev / "stress_metrics.csv")
    st = st[(st.slice == "all") & (st.band == "all horizons")].set_index("target")
    assert f"employed workers were still {round(st.loc['E', 'improvement_vs_best_baseline_pct'])}% closer" in sec and f"by {round(abs(st.loc['S', 'bias_pct']))}%" in sec
    fw = pd.read_csv(ev / "fresh_worlds.csv")
    fw = fw[(fw.band == "all horizons") & (fw.target == "E")].set_index("world_seed")
    assert f"{fw.loc[101, 'wape_model']:.2f}% and {fw.loc[202, 'wape_model']:.2f}%" in sec and f"{fw.loc[101, 'wape_best_baseline']:.2f}% and {fw.loc[202, 'wape_best_baseline']:.2f}%" in sec
    cv = pd.read_csv(ev / "interval_coverage.csv")
    cv = cv[(cv.slice == "all") & (cv.calibration == "forward") & (cv.window == "test")].set_index("target").coverage
    assert f"<b class=\"c-demand\">{round(100 * cv['E'])}%</b>" in sec and f"Job vacancies {round(100 * cv['V'])}% and job seekers {round(100 * cv['S'])}%" in sec
    fp = pd.read_csv(ev / "flag_precision.csv")
    fp = fp[(fp.window == "test") & (fp.source == "model") & (fp.volume == "all") & (fp.band == "1-12")].set_index("flag")
    assert f"<b class=\"c-demand\">{round(100 * fp.loc['Shortage alert', 'precision_decile'])}%</b>" in sec and f"Oversupply alerts {round(100 * fp.loc['Oversupply alert', 'precision_decile'])}%" in sec
    assert round(fp.loc["Shortage alert", "lift_decile"]) == 7 and "7 times better than chance" in sec


def test_resources_page_has_only_the_data_used_section_with_website_links():
    html = read("resources.html")
    main = html[html.index("<main"):html.index("</main>")]
    ids = re.findall(r'<section class="section[^"]*" id="([\w-]+)"', main)
    assert ids == ["datasets"], ids
    assert re.findall(r"<h2[^>]*>(.*?)</h2>", main) == ["Data used"] and "calibrated from" not in main and "Variables" not in main and 'id="calibration"' not in main
    for needle in ("Monthly district and trade panel", "Monthly district and sector table", "District catalogue", "Occupation list (NCO-2015)", "Sector to trade crosswalk", "District boundaries", "Forecasts, ranges, indexes and flags",
                   "bharatlas", "CC0 1.0 or CC BY 4.0", "Local Government Directory", "Census 2011", "24,72,600 rows and 17 columns", "4,94,520 rows and 8 columns", "3,447 occupations", "785 districts", "317 districts"):
        assert needle in main, needle
    # website links sit in the dataset column
    rows = re.findall(r"<tr><td[^>]*>(.*?)</td>", main)
    linked = [r for r in rows if "href=\"https://" in r]
    assert len(linked) == 4, len(linked)
    for host in ("mospi.gov.in", "nasscom.in", "censusindia.gov.in", "lgdirectory.gov.in", "dge.gov.in", "labour.gov.in", "bharatlas.com"):
        assert f'href="https://{host}/"' in main, host
    # sizes quoted on the page match the project's own manifest
    man = json.loads((V4 / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
    assert man["rows"] == 2472600 and man["districts"] == 317 and len(pd.read_csv(V4 / "district_catalog.csv")) == 317
    assert man["districts"] * man["sectors"] * man["months"] == 494520
    fman = json.loads((V4 / "FORECAST_MANIFEST.json").read_text(encoding="utf-8"))
    assert fman["files"]["forecast_series.parquet"]["rows"] == 475500 and "4,75,500" in main
    assert "tag sim" in main and "tag real" in main and "Simulated" in main
    hero = main[:main.index('id="datasets"')]
    assert "page-head big" in hero and "<h1" in hero and "hero-text" in hero and len(re.findall(r"<p", hero)) >= 3          # a real description in the hero
    tags = re.findall(r'class="tag (real|sim|model)"', main)
    chips = dict((re.sub(r"<[^>]+>", "", c[1]), int(c[0])) for c in re.findall(r"<li><b>(\d+)</b><span[^>]*>(.*?)</span></li>", hero))
    assert chips["datasets listed"] == len(tags) == 7 and chips["real sources"] == tags.count("real") and chips["simulated datasets"] == tags.count("sim")
    assert chips["built by the project"] == tags.count("model")                                          # the crosswalk and the forecasts


def test_dark_first_app_style_home_page_without_updates():
    home = read("index.html")
    for p in PAGES:
        assert 'data-theme="dark"' in read(p), p
    for needle in ("Coverage map", "Why this exists", "From monthly counts to a five-year view", "Features of this website", "Measured, not asserted", "grid-bg", "cta-card", 'class="how"'):
        assert needle in home, needle
    assert "Updates" not in home and 'id="updates"' not in home
    assert "Smart India Hackathon" not in home[home.index("<main"):home.index("</main>")] and "map-details" not in home and "Show every district as a table" not in home    # no hero pill, no table under the map
    assert 'class="open"' not in home and 'eyebrow">Features' not in home and "The weak spot, stated plainly" not in home and 'class="callout"' not in home
    assert "twelve months early" not in home and "56 districts" not in home and 'data-count="280"' not in home and "280 district" not in home
    assert 'id="features"' in home and home.count('<article class="card"><span class="icon-box">') == 12 and home.index('id="how"') < home.index('id="features"') < home.index("Measured, not asserted")
    assert home.index('id="map"') < home.index('id="how"')                     # the map comes before the method
    assert len(re.findall(r'class="how-step( on)?"', home)) == 4 and len(re.findall(r'class="how-panel( on)?"', home)) == 4
    for n in ('data-count="10"', 'data-count="317"', 'data-count="7925"', 'data-count="60"'):
        assert n in home, n


def test_map_data_matches_the_forecast_files_and_the_district_list():
    M = map_data()
    dim = pd.read_csv(V4 / "dim_series.csv")
    dd = dim.drop_duplicates("District_LGD_Code")
    assert {d["c"] for d in M["districts"]} == {str(c) for c in dd.District_LGD_Code} and len(M["districts"]) == 317
    assert sorted(M["sectors"]) == sorted(dim.Sector_Name.unique()) and M["horizons"] == [12, 36, 60] and M["targets"] == ["E", "V", "S", "D"]
    assert len({d["s"] for d in M["districts"]}) == 10 and M["others"] == [] and all(d["d"].startswith("M") and d["d"].endswith("z") for d in M["districts"])
    by = dd.set_index(dd.District_LGD_Code.astype(str)).State_Name
    assert all(by[d["c"]] == d["s"] for d in M["districts"])
    assert M["borders"].startswith("M") and M["borders"].count("M") > 60                         # the lines between the states
    assert len(M["backdrop"]) > 50_000                                          # the faint outline of the rest of India
    assert len(M["values"]) == 317 and all(len(v) == 5 and all(len(x) == 4 for x in v[0][3:4]) and len(v[0][0]) == 10 for v in M["values"].values())
    rl = pd.read_csv(V4 / "exports" / "forecast_rollups.csv.gz", low_memory=False)
    ds = rl[(rl.level == "district_sector") & rl.horizon.isin([12, 36, 60])].set_index(["District_LGD_Code", "Sector_Name", "horizon"])
    for code in ("118", "332", "7"):
        if code not in M["values"]:
            continue
        for si, sector in enumerate(M["sectors"]):
            for ti, k in enumerate("EVS"):
                arr = M["values"][code][si][ti]
                for j, h in enumerate((12, 36, 60)):
                    row = ds.loc[(int(code), sector, h)]
                    assert arr[1 + j] == row[k] and arr[4 + 2 * j] == row[f"{k}_lo"] and arr[5 + 2 * j] == row[f"{k}_hi"], (code, sector, k, h)
                    assert arr[4 + 2 * j] <= arr[1 + j] <= arr[5 + 2 * j]
            for j, h in enumerate((12, 36, 60)):
                assert abs(M["values"][code][si][3][1 + j] - ds.loc[(int(code), sector, h), "DI"]) < 0.051
    for s in M["sectors"]:
        for k in "EVS":
            assert len(M["confidence"][s][k]) == 3 and all(w.split(" ")[0] in ("high", "medium", "low") for w in M["confidence"][s][k])
    assert M["source"]["licence"] == "CC0-1.0 / CC-BY-4.0" and M["origin"] == "2025-12"


def test_hindi_text_is_complete_and_keeps_the_markup():
    import i18n
    import i18n_hi
    for p in PAGES:
        src = read(p)
        assert "data-hi=" in src, p
    # every translatable element has Hindi (the build lists any that does not)
    sys.path.insert(0, str(ROOT / "src" / "app"))
    import build_pages
    for file, active, title, desc, body in build_pages.PAGES:
        pp = "../" if "/" in file else ""
        text = (build_pages.BODIES / f"{body}.html").read_text(encoding="utf-8").replace("{P}", pp)
        html = build_pages.head(title, desc, pp) + build_pages.header(active, pp) + text + build_pages.footer(pp, "")
        _, missing = i18n.inject(html)
        assert not missing, (file, missing[:3])
        assert title in i18n_hi.TITLES, title
    for en, hi in i18n_hi.PAGE.items():
        assert sorted(re.findall(r"<[^>]+>", en)) == sorted(re.findall(r"<[^>]+>", hi)), en[:60]       # the same tags, so layout and links are unchanged
        assert re.search(r"[ऀ-ॿ]", hi), en[:60]
    # the strings the page script builds: every literal t("...") has Hindi and the same {placeholders}
    js = read("assets/site.js")
    keys = {json.loads('"' + k + '"') for k in re.findall(r'\bt\("((?:[^"\\]|\\.)*)"', js)}
    keys |= {"high", "medium", "low"}
    D = data()
    keys |= {D["hero"]["rule"]}
    for k in keys:
        assert k in i18n_hi.JS, f"no Hindi for script text: {k[:70]}"
    for k, v in i18n_hi.JS.items():
        assert sorted(re.findall(r"\{\w+\}", k)) == sorted(re.findall(r"\{\w+\}", v)), k[:60]
        assert sorted(re.findall(r"<[^>]+>", k)) == sorted(re.findall(r"<[^>]+>", v)), k[:60]
    # names the script shows: states, sectors and all 56 districts, plus the months
    M = map_data()
    for name in {d["n"] for d in M["districts"]} | {o["n"] for o in M["others"]} | {d["s"] for d in M["districts"]} | set(M["sectors"]) | {D["hero"]["district"]}:
        assert name in i18n_hi.NAMES, name
    assert len(i18n_hi.MONTHS) == 12 and len(i18n_hi.LONG_MONTHS) == 12
    out = (SITE / "assets" / "i18n-hi.js").read_text(encoding="utf-8")
    assert out.startswith("window.HI = ") and "मुंबई" in out


def test_pages_are_generated_reproducibly_from_the_shared_parts():
    import importlib.util
    before = {p: (SITE / p).read_bytes() for p in PAGES}
    before_js = (SITE / "assets" / "i18n-hi.js").read_bytes()
    spec = importlib.util.spec_from_file_location("build_pages", ROOT / "src" / "app" / "build_pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    assert before == {p: (SITE / p).read_bytes() for p in PAGES} and before_js == (SITE / "assets" / "i18n-hi.js").read_bytes()


def test_unfinished_items_are_limited_to_the_documented_ones():
    readme = read("README.md")
    for p in PAGES:
        html = read(p)
        assert "lorem" not in html.lower() and "TODO" not in html
        assert set(re.findall(r"mailto:([^\"]+)", html)) <= {"feedback@lmis-demo.example"}
    assert "feedback@lmis-demo.example" in readme and "Reuse terms" not in readme


def test_reduced_motion_and_accessibility_basics_are_present():
    css, js = read("assets/styles.css"), read("assets/site.js")
    assert "prefers-reduced-motion: reduce" in css and "prefers-reduced-motion" in js and ":focus-visible" in css
    assert 'role="tablist"' in read("index.html") and "ArrowDown" in js                    # the home page steps work from the keyboard
    for p in PAGES:
        html = read(p)
        assert 'lang="en"' in html and 'class="skip"' in html and 'name="viewport"' in html and "<h1" in html and html.count("<h1") == 1, p


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
