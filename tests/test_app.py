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
    L = pd.read_csv(FC / "forecast_long.csv")
    W = pd.read_csv(FC / "flags.csv")
    m = D["meta"]
    assert (m["series"], m["districts"], m["states"], m["sectors"], m["tiers"]) == (280, 56, 4, 5, 16)
    assert m["forecast_rows"] == len(L) == 10080 and m["flag_rows"] == len(W) == 3360
    assert "coverage" not in D
    h = D["hero"]
    f = L[(L.Series_ID == h["series_id"]) & (L.target_variable == "Active_Job_Vacancies")].sort_values("horizon")
    assert abs(h["V"]["forecast"][-1] - f.forecast.iloc[-1] / f.last_observed.iloc[0] * 100) < 0.01
    assert len(h["V"]["history"]) == 37 and h["V"]["history"][-1] == 100.0 and len(h["V"]["forecast"]) == 12
    assert all(a < b < c for a, b, c in zip(h["V"]["lo"], h["V"]["forecast"], h["V"]["hi"]))
    for k, v in D["accuracy"]["original"].items():
        if k != "label":
            assert v["model"] < v["baseline"] * 1.01
    assert "updates" not in D and "snapshot" not in D                # the home page has no Updates or sector-by-sector section


def test_claims_in_the_text_match_the_evidence():
    D = data()
    a = D["accuracy"]["original"]
    home = read("index.html")
    assert round(100 * (1 - a["E"]["model"] / a["E"]["baseline"])) == 29 and '<b class="c-demand">29%</b>' in home
    assert round(100 * (1 - a["S"]["model"] / a["S"]["baseline"])) == 15 and '<b class="c-demand">15%</b>' in home
    assert f"{a['E']['model']:.2f}% against {a['E']['baseline']:.2f}%" in home and f"{a['S']['model']:.2f}% against {a['S']['baseline']:.2f}%" in home
    for k, v in a.items():
        if k != "label":
            assert v["model"] < v["baseline"] * 1.01


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
    assert ids == ["project", "timeline", "dataset", "principles", "engine", "evaluation"], ids       # project, overview, data, principles, architecture, results
    assert len(re.findall(r"<section", main)) == 6                                     # the hero is the "About the project" section
    heads = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", main)]
    assert heads == ["How it works", "Dataset used", "Model engine overview and core principles", "Machine learning engine and architecture", "Model evaluation achievements"], heads
    assert re.search(r"<h1[^>]*>About the project</h1>", main) and main.count("<h1") == 1 and "page-head big" in main
    assert 'class="eyebrow"' not in main and "In more detail" not in main                 # no label repeating a heading
    for gone in ("From monthly counts to twelve-month forecasts", "A forecasting engine that shows where", "Coverage and pilot scope", 'id="coverage"', "Smart India Hackathon", "SIH26246", "It was built for"):
        assert gone not in main, gone
    assert 'class="toc"' not in main and 'href="#' not in main                           # no jump links in the hero
    hero = main[:main.index('id="timeline"')]
    assert hero.index("<h1") < hero.index('class="grid1"') and hero.count('class="lead"') == 1 and re.search(r'class="lead">\s*<h1', hero)   # cards sit beside the heading
    assert main.count('class="tl-dot"') == 6 and 'class="timeline"' in main and "tl-scroll" in main        # the horizontal timeline
    assert main.count('class="arch-n"') == 6 and 'class="step"' not in main
    for gone in ("Questions and terms", "How wide is the range", "faq", "explainer", "Download the forecasts", "cta-card", 'id="flags"', "Open the dashboard"):
        assert gone not in main, gone
    # the facts the page states come from the project's documents
    assert "36 for employed workers, 29 for vacancies and 68 for job seekers" in main and "10,080 forecast rows" in main and "15 models per run" in main
    assert "January 2011 to February 2022" in main and "March to December 2022" in main and "January 2023 to December 2026" in main


def test_about_dataset_section_matches_the_project_data():
    html = read("about.html")
    sec = html[html.index('id="dataset"'):html.index('id="principles"')]
    man = json.loads((ROOT / "data" / "raw" / "DATA_MANIFEST.json").read_text(encoding="utf-8"))["files"]["lmis_district_monthly_2011_2026.csv"]
    assert f"{man['rows']:,}" in sec and f">{man['columns']}<" in sec
    cols = pd.read_csv(ROOT / "data" / "raw" / "lmis_district_monthly_2011_2026.csv", nrows=2).columns.tolist()
    assert len(cols) == man["columns"]
    for c in ("State_Name", "District_LGD_Code", "Timestamp", "Sector_Name", "NIC_Code", "NCO_Code", "NSQF_Level", "Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers",
              "Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "District_Total_Population_Est", "Training_Seats_Sanctioned", "Trainees_Certified_Monthly"):
        assert c in cols and c in sec, c
    dd = pd.read_csv(ROOT / "data" / "dashboard" / "dim_district.csv")
    counts = dd.groupby("state").size().to_dict()
    for state, n in counts.items():
        total = n + sum(1 for o in map_data()["others"] if o["s"] == state)
        assert re.search(rf"<td[^>]*>{state}</td>\s*<td[^>]*>{n} of {total}</td>", sec), (state, n, total)
    sx = pd.read_csv(ROOT / "data" / "raw" / "sector_nco_crosswalk.csv")
    for r in sx[sx.Is_Anchor_Code].itertuples():
        assert r.Sector_Name in sec and r.NCO_2015_Title.lower() in sec.lower(), r.Sector_Name


def test_about_evaluation_figures_match_the_evaluation_outputs():
    html = read("about.html")
    sec = html[html.index('id="evaluation"'):html.index("</main>")]
    D = data()["accuracy"]["original"]
    nf = json.load(open(ROOT / "reports" / "evaluation" / "noise_floor.json"))["mean_over_horizons"]
    names = {"E": "Employed workers", "S": "Registered job seekers", "V": "Job vacancies"}
    for k in "EVS":
        row = re.search(rf"<td[^>]*>{names[k]}</td>(.*?)</tr>", sec, re.S).group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row)
        floor = nf[k]["floor_wape"]
        assert cells[:4] == [f"{D[k]['model']:.2f}%", f"{D[k]['baseline']:.2f}%", f"{floor:.2f}%", f"{round(100 * (1 - D[k]['model'] / D[k]['baseline']))}%"], (k, cells)
    assert f"{nf['E']['model_wape'] / nf['E']['floor_wape']:.2f}&times;" in sec
    for src, col in (("fresh_2027", "E"), ("fresh_2028", "E")):
        m = pd.read_csv(ROOT / "reports" / "evaluation" / "v3" / src / "metrics.csv").set_index(["target", "model"])
        assert f"{m.loc[(col, 'v3'), 'wape_mean_horizon']:.2f}%" in sec, src
    s_fresh = [pd.read_csv(ROOT / "reports" / "evaluation" / "v3" / f"fresh_{y}" / "metrics.csv").set_index(["target", "model"]).loc[("S", "v3"), "wape_mean_horizon"] for y in (2027, 2028)]
    assert abs(sum(s_fresh) / 2 - 6.0) < 0.1 and "about 6.0%" in sec


def test_resources_page_has_only_the_data_used_section_with_website_links():
    html = read("resources.html")
    main = html[html.index("<main"):html.index("</main>")]
    ids = re.findall(r'<section class="section[^"]*" id="([\w-]+)"', main)
    assert ids == ["datasets"], ids
    assert re.findall(r"<h2[^>]*>(.*?)</h2>", main) == ["Data used"] and "calibrated from" not in main and "Variables" not in main and 'id="calibration"' not in main
    for needle in ("Monthly district and sector panel", "District catalogue", "Occupation list (NCO-2015)", "Sector to occupation crosswalk", "District boundaries", "bharatlas", "CC0 1.0 or CC BY 4.0",
                   "Local Government Directory", "Census 2011", "53,760 rows and 41 columns", "17,920 rows and 40 columns", "3,447 occupations", "785 districts"):
        assert needle in main, needle
    # website links sit in the dataset column
    rows = re.findall(r"<tr><td[^>]*>(.*?)</td>", main)
    linked = [r for r in rows if "href=\"https://" in r]
    assert len(linked) == 4, len(linked)
    for host in ("mospi.gov.in", "nasscom.in", "censusindia.gov.in", "lgdirectory.gov.in", "mahavillages.mahabhumi.gov.in", "dge.gov.in", "labour.gov.in", "bharatlas.com"):
        assert f'href="https://{host}/"' in main, host
    # sizes quoted on the page match the project's own manifest
    man = json.loads((ROOT / "data" / "raw" / "DATA_MANIFEST.json").read_text(encoding="utf-8"))["files"]
    assert man["lmis_district_monthly_2011_2026.csv"]["rows"] == 53760 and man["lmis_district_monthly_2011_2026.csv"]["columns"] == 41
    assert man["lmis_district_quarterly_2011_2026.csv"]["rows"] == 17920 and man["lmis_district_quarterly_2011_2026.csv"]["columns"] == 40
    assert len(pd.read_csv(ROOT / "data" / "raw" / "district_catalog.csv")) == 56
    assert len(pd.read_csv(FC / "forecast_long.csv")) == 10080 and "10,080" in main and "3,360" in main
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
    for needle in ("Coverage map", "Why this exists", "From monthly counts to a twelve-month view", "Features of this website", "Measured, not asserted", "grid-bg", "cta-card", 'class="how"'):
        assert needle in home, needle
    assert "Updates" not in home and 'id="updates"' not in home
    assert "Smart India Hackathon" not in home[home.index("<main"):home.index("</main>")] and "map-details" not in home and "Show every district as a table" not in home    # no hero pill, no table under the map
    assert 'class="open"' not in home and 'eyebrow">Features' not in home and "The weak spot, stated plainly" not in home and 'class="callout"' not in home
    assert "Twelve months ahead, sector by sector" not in home and 'id="snapshot"' not in home and "What you can do here" not in home
    assert 'id="features"' in home and home.count('<article class="card"><span class="icon-box">') == 9 and home.index('id="how"') < home.index('id="features"') < home.index("Measured, not asserted")
    assert home.index('id="map"') < home.index('id="how"')                     # the map comes before the method
    assert len(re.findall(r'class="how-step( on)?"', home)) == 4 and len(re.findall(r'class="how-panel( on)?"', home)) == 4


def test_map_data_matches_the_forecast_files_and_the_district_list():
    M = map_data()
    L = pd.read_csv(FC / "forecast_long.csv", dtype={"district_lgd_code": str})
    dd = pd.read_csv(ROOT / "data" / "dashboard" / "dim_district.csv", dtype={"district_lgd_code": str})
    assert {d["c"] for d in M["districts"]} == set(dd.district_lgd_code) and len(M["districts"]) == 56
    assert M["sectors"] == sorted(L.sector.unique()) and M["horizons"] == [3, 6, 12] and M["targets"] == ["E", "V", "S"]
    assert len({d["s"] for d in M["districts"]}) == 4 and all(d["d"].startswith("M") and d["d"].endswith("z") for d in M["districts"])
    assert len(M["backdrop"]) > 50_000                                          # the faint outline of the rest of India
    lgd_file = ROOT / "data" / "external" / "lgd_districts" / "LGD_Districts.parquet"
    if lgd_file.exists():                                                       # the 22 MB source file is git-ignored: this check runs only where it has been downloaded (see app/README.md)
        import pyarrow.parquet as pq
        lgd = pq.read_table(lgd_file, columns=["dist_lgd", "state_lgd"]).to_pandas()
        for state, code in (("Maharashtra", 27), ("Delhi", 7), ("West Bengal", 19), ("Tamil Nadu", 33)):
            every = {str(int(c)) for c in lgd[lgd.state_lgd.astype(int) == code].dist_lgd}
            drawn = {d["c"] for d in M["districts"] if d["s"] == state} | {o["c"] for o in M["others"] if o["s"] == state}
            assert drawn == every, state                                        # every district of each project state is drawn
    assert {o["s"] for o in M["others"]} == {"West Bengal", "Tamil Nadu"} and len(M["others"]) == 52
    assert not {o["c"] for o in M["others"]} & {d["c"] for d in M["districts"]} and all(o["d"].startswith("M") and o["d"].endswith("z") for o in M["others"])
    tv = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
    for code in ("482", "489", "303"):
        for si, sector in enumerate(M["sectors"]):
            for ti, k in enumerate(M["targets"]):
                g = L[(L.district_lgd_code == code) & (L.sector == sector) & (L.target_variable == tv[k])].set_index("horizon")
                if g.empty:
                    continue
                arr = M["values"][code][si][ti]
                assert abs(arr[0] - g.last_observed.iloc[0]) < 0.06 and abs(arr[3] - g.loc[12, "forecast"]) < 0.06 and abs(arr[8] - g.loc[12, "lo90"]) < 0.06 and abs(arr[9] - g.loc[12, "hi90"]) < 0.06
                assert arr[8] < arr[3] < arr[9]
    for s in M["sectors"]:
        assert M["confidence"][s]["E"] == "high" and M["confidence"][s]["V"] == "low"
    assert M["source"]["licence"] == "CC0-1.0 / CC-BY-4.0" and M["origin"] == "2026-10"


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
