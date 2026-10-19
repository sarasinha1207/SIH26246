#!/usr/bin/env python3
"""
Public website - assemble the pages from one shared header, footer and head plus the page bodies in src/app/pages/.
Keeps the navigation, Display options and footer identical on every page, and adds the Hindi text (data-hi) to every translatable element.
Run: python src/app/build_pages.py
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "app"
BODIES = Path(__file__).resolve().parent / "pages"


def ver(rel):
    """Short content hash for cache-busting: a changed asset gets a new URL, so visitors never see a stale stylesheet or script."""
    return hashlib.sha1((SITE / rel).read_bytes()).hexdigest()[:8]


PAGES = [  # file, nav key, title, description, body file
    ("index.html", "home", "LMIS India: labour market forecasts for districts", "Twelve-month forecasts of employment, job vacancies and job seekers for 56 districts and five sectors, with honest ranges.", "index"),
    ("about.html", "about", "About | LMIS India", "What LMIS India is, how monthly counts become twelve-month district forecasts, what the pilot covers and how the forecasting engine is built.", "about"),
    ("resources.html", "res", "Resources | LMIS India", "The data behind the forecasts and where each part came from: the datasets, what the simulator was calibrated to, and what each column measures.", "resources"),
]

PREPAINT = """<script>(function(){var h=document.documentElement,s={};try{s=JSON.parse(localStorage.getItem('lmis-display')||'{}')}catch(e){}
h.dataset.theme=s.theme==='light'?'light':'dark';h.dataset.size=s.size||'m';var l=s.lang==='hi'?'hi':'en';h.dataset.lang=l;h.lang=l;
h.dataset.motion=(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)?'reduced':'full';})();</script>"""

LOGO = ('<svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="9" fill="#0F2B63"/>'
        '<path d="M6 25 L15 17 L22 20 L28 8" fill="none" stroke="#8FB0FF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M6 10 L14 14 L21 12 L28 24" fill="none" stroke="#F2A93B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')

DISPLAY = """<div class="display">
  <button class="display-btn" type="button" aria-expanded="false" aria-controls="display-panel" aria-label="Display options">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4v5M6 13v7M12 4v10M12 18v2M18 4v2M18 10v10" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/><circle cx="6" cy="11" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="16" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="8" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/></svg>
  </button>
  <div class="display-panel" id="display-panel" role="group" aria-label="Display options" hidden>
    <div class="dp-title">Display options</div>
    <div class="dp-row"><span class="dp-label">Text size</span><div class="seg" role="group" aria-label="Text size">
      <button type="button" data-size-step="-1" aria-label="Smaller text" translate="no">A&minus;</button><button type="button" data-size-step="0" aria-label="Default text size" translate="no">A</button><button type="button" data-size-step="1" aria-label="Larger text" translate="no">A+</button></div></div>
    <div class="dp-row"><span class="dp-label">Theme</span><div class="seg" role="group" aria-label="Theme">
      <button type="button" data-opt="theme" data-val="light">Light</button><button type="button" data-opt="theme" data-val="dark">Dark</button></div></div>
    <div class="dp-row"><span class="dp-label">Language</span><div class="seg" role="group" aria-label="Language">
      <button type="button" data-opt="lang" data-val="en" translate="no">English</button><button type="button" data-opt="lang" data-val="hi" lang="hi" translate="no">हिन्दी</button></div></div>
  </div>
</div>"""


def head(title, desc, p):
    return f"""<!doctype html>
<html lang="en" data-theme="dark" data-size="m" data-lang="en" data-motion="full">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#0A0E16">
<link rel="icon" href="{p}assets/favicon.svg" type="image/svg+xml">
{PREPAINT}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400..800&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400..800&display=swap"></noscript>
<link rel="stylesheet" href="{p}assets/styles.css?v={ver("assets/styles.css")}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>"""


def header(active, p):
    links = [("home", "index.html", "Home"), ("about", "about.html", "About"), ("res", "resources.html", "Resources")]
    li = "".join(f'<li><a href="{p}{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a></li>' for key, href, label in links)
    return f"""
<header class="site-header">
  <div class="wrap">
    <nav class="nav" aria-label="Main">
      <a class="brand" href="{p}index.html" aria-label="LMIS India home">{LOGO}<span translate="no">LMIS <b>India</b></span></a>
      <ul class="nav-links" id="nav-links">{li}</ul>
      <div class="nav-actions">
        {DISPLAY}
        <a class="btn small nav-cta" href="{p}dashboard/index.html">Open dashboard</a>
        <button class="nav-toggle" aria-expanded="false" aria-controls="nav-links">Menu</button>
      </div>
    </nav>
  </div>
  <div class="progress" aria-hidden="true"><i></i></div>
</header>
"""


def footer(p, extra_scripts):
    return f"""
<footer class="site-footer">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <h4>About</h4>
        <p>An AI-enabled labour market intelligence and skill demand-supply forecasting engine for the Ministry of Skill Development and Entrepreneurship.</p>
        <p>All figures on this site are simulated for demonstration. They are not official statistics.</p>
      </div>
      <div><h4>Pages</h4><ul><li><a href="{p}index.html">Home</a></li><li><a href="{p}about.html">About</a></li><li><a href="{p}resources.html">Resources</a></li><li><a href="{p}dashboard/index.html">Dashboard</a></li></ul></div>
      <div><h4>Data</h4><ul><li><a href="{p}resources.html#datasets">Data sources</a></li><li><a href="{p}about.html#dataset">Dataset details</a></li><li><a href="{p}about.html#evaluation">Model evaluation</a></li></ul></div>
      <div><h4>Contact</h4><p><a href="mailto:feedback@lmis-demo.example" translate="no">feedback@lmis-demo.example</a></p><p>No login. This site sets no cookies and has no analytics. Your display choices stay on your device.</p></div>
    </div>
    <div class="legal">Forecast for <span data-fill="meta.first_target">November 2026</span> to <span data-fill="meta.last_target">October 2027</span>, made from data up to <span data-fill="meta.origin_label">October 2026</span>.</div>
  </div>
</footer>
<button class="to-top" type="button" aria-label="Back to top"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V6M6 11l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
<div class="tip" id="tip" role="status" aria-live="polite" hidden></div>
<script src="{p}assets/i18n-hi.js?v={ver("assets/i18n-hi.js")}"></script>
<script src="{p}data/site_data.js?v={ver("data/site_data.js")}"></script>
{extra_scripts.format(p=p)}<script src="{p}assets/site.js?v={ver("assets/site.js")}"></script>
</body>
</html>
"""


def main():
    i18n.write_js(SITE / "assets" / "i18n-hi.js")
    missing = []
    for file, active, title, desc, body in PAGES:
        p = "../" if "/" in file else ""
        text = (BODIES / f"{body}.html").read_text(encoding="utf-8").replace("{P}", p)
        extra = '<script src="{p}data/map_data.js?v=' + ver("data/map_data.js") + '"></script>\n' if 'id="map-svg"' in text else ""
        html = head(title, desc, p) + header(active, p) + text + footer(p, extra)
        html, miss = i18n.inject(html)
        missing += [(file, m) for m in miss]
        out = SITE / file
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print("wrote", out.relative_to(ROOT))
    if missing:
        print(f"\n{len(missing)} text elements have no Hindi translation yet:")
        for f, m in missing:
            print(" -", f, "|", m)
    (SITE / "assets" / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 34"><rect width="34" height="34" rx="9" fill="#0F2B63"/><path d="M6 25 L15 17 L22 20 L28 8" fill="none" stroke="#8FB0FF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M6 10 L14 14 L21 12 L28 24" fill="none" stroke="#F2A93B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>\n', encoding="utf-8")


if __name__ == "__main__":
    main()
