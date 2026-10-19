# LMIS India public website

A static site: plain HTML, CSS and JavaScript. No server and no login. The pages are assembled from shared parts by a small script (below), but what you publish is plain files.

| Page | File |
|---|---|
| Home (map, method, features, results) | `index.html` |
| About (project, how it works timeline, coverage, dataset used, principles, engine, evaluation) | `about.html` |
| Resources (the data used, with its source websites) | `resources.html` |
| Dashboard (its own layout: top bar, collapsible sidebar, one-line footer) | `dashboard/index.html` |
| Dashboard (placeholder until it is built) | `dashboard/index.html` |

## Preview
```bash
python src/app/serve.py
```
then open http://localhost:8080. Leave the terminal open; stop it with Ctrl+C. The server keeps running while files change: it serves the latest files on every refresh (the browser is told not to keep copies), and it rebuilds the pages by itself when you edit a page in `src/app/pages/`, the Hindi text, the stylesheet or the script. It refuses to start if the port is already taken (`python src/app/serve.py 8081` uses another port). Rebuilding the data files is a separate command (below).

Opening `index.html` directly from the disk also works, because the data is a script file, not a fetch. The old `python -m http.server 8099 --directory app` still works too, but does not rebuild or avoid stale copies.

## Publish
Upload the contents of `app/` to any static host (GitHub Pages, Netlify, Cloudflare Pages, an institutional web server). Nothing else is needed.

## Editing the pages
The three pages and the dashboard placeholder share one header (with the Display options), footer and head, so edit the page bodies in `src/app/pages/` (the preview server rebuilds by itself; otherwise run):
```bash
python src/app/build_pages.py          # rewrites app/*.html and assets/i18n-hi.js, adds a content hash to the CSS/JS links (cache-busting)
```
Colours, fonts and the dark and light themes are CSS variables at the top of `assets/styles.css`.

## Display options (header)
The round button in the header opens a panel with three rows: **Text size** (A−, A, A+; four steps), **Theme** (Light, Dark; dark by default) and **Language** (English, हिन्दी). The choice is saved in the visitor's own browser (`localStorage`) and applied before the page paints. Animation is reduced automatically for visitors whose device asks for it; a high-contrast device setting strengthens the lines.

## Hindi
Every visible text on every page has a Hindi version, and so do the charts, tooltips and the map. The translations are in `src/app/i18n_hi.py`:
* `PAGE`: text written in the page files. The key is the English text exactly as it appears (including any tags); the build adds the Hindi to the element as `data-hi`. If you edit English text in `src/app/pages/`, the build lists any element that now has no Hindi, and `tests/test_app.py` fails until it has one.
* `JS`: text the page script builds (chart labels, tooltips, the map), with `{name}` marking values the script fills in. Keep the same `{names}` and tags in the Hindi.
* `NAMES`: states, sectors and the 56 districts; `MONTHS`, `TITLES`.
Have a Hindi speaker read the translation before launch. The Devanagari font (Noto Sans Devanagari) loads from Google Fonts only when Hindi is chosen.

## The map
`index.html#map` shows India with every district of the four states. The 56 project districts are coloured by sector, measure (employed workers, vacancies, job seekers, or openings per 100 job seekers) and months ahead (3, 6, 12); the other 52 districts of West Bengal and Tamil Nadu are outlined and marked "no forecast data". Select a state to zoom in; hover or tap a district for its numbers; the side panel ranks the highest and lowest five districts, and a table below lists all of them. Colours sort the districts into five equal groups.
```bash
python src/app/build_map_data.py        # writes app/data/map_data.js (296 KB): district shapes, the faint India outline and the forecast values
```
It reads `data/dashboard/district_boundaries.geojson` (the 56 districts), `data/external/lgd_districts/LGD_Districts.parquet` (the rest of India, for the outline only; 22,178,335 bytes, SHA-256 `c205da56…`, from the bharatlas site; not in git) and `outputs/forecasts/origin_<month>/forecast_long.csv`. To fetch the parquet again:
```bash
curl -L -o data/external/lgd_districts/LGD_Districts.parquet https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/districts/LGD_Districts.parquet
```
Boundaries are simplified for orientation, not for survey use or as an authoritative border.

## The dashboard
`dashboard/index.html` is a separate single-page app, not part of the public pages: a top bar, a fixed collapsible left sidebar, a body that changes by page, and a one-line footer. **Exit** (top bar and sidebar) returns to the public site; there is no login, so there is nothing to sign out of. Seven pages: Overview (4 KPIs, district map coloured by absolute context, openings against seekers, early-warning summary, coverage by sector, sector table), Demand, Supply (e-Shram break marked), Gap, District ranking (56 districts within one sector, relative status beside absolute context, small-count series greyed), Early warnings (alert and watch), and Data and notes. The Sector, State and District filters are on every page and live in the URL (`#/overview?sector=Healthcare&state=Delhi`), so a view can be bookmarked or shared; clicking a district on the map sets them. **Download CSV** exports the current view.

Alert and watch: a series in the tightest tenth of its sector is a shortage flag, and in the loosest tenth an oversupply flag. It is an *alert* when the absolute context agrees (openings exceed seekers, or oversupplied or deep surplus) and a *watch* when it does not. Forecast ranges appear only when one district and one sector are selected. The dashboard is English only.
```bash
python src/app/build_dashboard.py     # writes dashboard/data/dash_data.js (2 MB: 280 series, 190 months, forecasts, flags) and the page shell
python tests/test_dashboard.py
```
`serve.py` rebuilds the shell when `dashboard.css`, `dashboard.js` or `src/app/dashboard/shell.html` change. Rerun `build_dashboard.py` after a new forecast (and change `ORIGIN`).

## Where the numbers come from
Every number comes from the project's outputs. Rebuild after a new forecast:
```bash
python src/app/build_site_data.py        # writes app/data/site_data.js (hero example, coverage, test-period accuracy)
python src/app/build_map_data.py         # writes app/data/map_data.js
python src/app/build_pages.py
python tests/test_app.py                 # checks the site against the source files
```
Edit `ORIGIN` in `src/app/build_site_data.py` and `src/app/build_map_data.py` when the forecast month changes.

## Before launch: things only you can fill in
* **Contact address:** `feedback@lmis-demo.example` in each footer is a placeholder. Replace it.
* **Hindi review:** see above.
* **Fonts:** Geist (and Noto Sans Devanagari in Hindi) load from Google Fonts without blocking the page. That sends the visitor's IP address to Google. To avoid it, download the fonts, serve them from `assets/` and add `@font-face` rules. The footer says the site has no cookies and no analytics, which stays true either way.

## Notes
* Every page carries a notice that the data is simulated. Keep it until real statistics are connected.
* Design: dark-first and app-like. Hero with the forecast chart, key figures, the map, "why this exists", an interactive four-step "how it works" (steps advance on their own, pause on hover, work from the keyboard), a features-of-this-website card grid, a results row that states the weak spot, and a closing call to action. Cards have a soft glow that follows the pointer.
* Animations: the headline and hero chart play once on load, figures count up, bars and districts animate as they scroll into view, the map zooms between states, and the header shows scroll progress. All of it switches off with the device's reduced-motion setting.
* Palette: blues for the interface, employed workers and vacancies; marigold only for job seekers (supply) and for medium confidence; red only for low confidence. No green is used anywhere (`tests/test_app.py` checks this).
* The hero example (Parbhani, Manufacturing) is chosen by a stated rule (the series whose vacancy forecast grows fastest relative to its seeker forecast) and the page says so.
