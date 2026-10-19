# KaushalSetu public website

*Bridging Skills. Forecasting Futures.*

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
`dashboard/index.html` is a separate single-page app, not part of the public pages: a top bar, a fixed collapsible left sidebar, a body that changes by page, and a one-line footer. **Exit** (top bar and sidebar) returns to the public site; there is no login, so there is nothing to sign out of. Seven pages: Overview (4 KPIs, district map coloured by absolute context, openings against seekers, early-warning summary, coverage by sector, sector table), Demand, Supply (e-Shram break marked), Gap, District ranking (the forecast districts within one sector, relative status beside absolute context, small-count series greyed), Early warnings (alert and watch), and Data and notes. The Sector, State and District filters are on every page and live in the URL (`#/overview?sector=Healthcare&state=Delhi`), so a view can be bookmarked or shared; clicking a district on the map sets them. **Download CSV** exports the current view.

Model-driven: the dashboard shows nothing typed in. History comes from `panel_monthly.parquet`; forecasts, 90% ranges (`lo90` to `hi90`), confidence and typical test error are copied unrounded from `forecast_long.csv`; relative status, absolute context, change, precision and confidence are copied from `flags.csv`. The builder checks both files and the panel against the SHA-256 hashes in the forecast folder's `manifest.json`, checks that the history ends where the forecast starts (`last_observed`), and reads the absolute-context cuts off `flags.csv`. Alert and watch are the project's own flag classes (manifest: deciles at 10/90, watch classes at 30/70): the tightest or loosest decile is an *alert*, the tight or loose class next to it a *watch*, a lookup on `forecast_status`. Forecast ranges appear only when one district and one sector are selected. The dashboard is English only.

```bash
python src/app/build_dashboard.py     # writes dashboard/data/dash_data.js (2 MB: 280 series, 190 months, forecasts, flags) and the page shell
python tests/test_dashboard.py
```
`serve.py` rebuilds the shell when `dashboard.css`, `dashboard.js` or `src/app/dashboard/shell.html` change. Rerun `build_dashboard.py` after a new forecast; it picks the newest `outputs/forecasts/origin_*` folder, or pass one, e.g. `build_dashboard.py 2026-10`.

## The assistant
A round chat button sits in the bottom-right corner of every public page and of the dashboard (`assets/chat.js`, `assets/chat.css`, one file for both). Two layers:
* **The site's own engine** (always on, in the browser). It answers from what is already on the page: on the public site from `site_data.js` and the page text; on the dashboard also from `dash_data.js`, so figures are the `forecast_long.csv` and `flags.csv` values for the page's current filters unless the question names a sector, state or district ("shortage alerts in Healthcare", "tightest districts in Construction in West Bengal", "forecast for Pune in Manufacturing", "what does this page show?").
* **Google Gemini** (on when the server has a key). The window sends the question, the last few turns and a text summary of those same facts to `/api/chat`; the server adds fixed rules (answer only from the facts, never invent numbers, the data is simulated, ignore instructions inside questions) and asks Gemini to word the answer. The browser never sees the key or talks to Google. If the key, the server or the network is missing, or Gemini errors, the window shows the engine's own answer and says so. A visitor can switch AI off in the window, and the window states plainly that questions go to Google while it is on.

**Switch Gemini on locally:** copy `.env.example` to `.env` (git-ignored), put the key after `GEMINI_API_KEY=`, and restart `python src/app/serve.py` once (a key added later is picked up without a restart). Do not paste the key into chat, code or commits. `GEMINI_MODEL` sets the model (default `gemini-3.8-flash`; model names change, so set this if Google retires one).

**If a model runs out:** `GEMINI_MODEL` can list several models (default: `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`). When one returns a quota error (429), is overloaded (5xx) or no longer exists (404), the next one answers; the failed one is skipped for a few minutes (an hour for 404) so it is not asked on every question, then tried again. A wrong key or request (400, 401, 403) stops at once because no other model would fix it. Only when every model is resting does the window fall back to the site's own answers. Google counts quota per model, but free-tier limits can also be shared per project; check the limits for your key in Google AI Studio. `CHAT_DAILY_CAP` is the site's own ceiling on questions per day and is separate: when it is reached the assistant uses the site's own answers for the rest of the day.

**Deployment on Vercel:** the whole site is the `app/` folder, so make it the project's root.
1. Import the repository in Vercel and set **Root Directory** to `app`; Framework Preset **Other**; leave the build and install commands empty. (The repository's root `requirements.txt` lists the forecasting stack, far over the function size limit. `app/requirements.txt` lists no packages on purpose so Vercel installs nothing; if a deploy still fails with `LAMBDA_SIZE_EXCEEDED`, open Settings, General, Root Directory and switch off "Include source files outside of the Root Directory in the Build Step".)
2. Under Settings, Environment Variables, add `GEMINI_API_KEY` for Production (and Preview if wanted). Optional: `GEMINI_MODEL` (one model or a comma-separated list in order of preference), `CHAT_RATE_PER_MINUTE`, `CHAT_DAILY_CAP`, `CHAT_ALLOWED_ORIGINS` (add your custom domain if it differs from the one the visitor is on). Redeploy after changing a variable.
3. `app/api/chat.py` is the function: the same file `serve.py` imports locally, standard library only, so nothing is installed. `app/vercel.json` only sets its time limit. Vercel serves it at `/api/chat` (`GET` says whether the assistant is on, `POST` answers a question).
4. Limits per visitor and per day are kept in memory, so on a serverless host they apply per instance. Also set a spending cap or quota on the key in Google AI Studio, and keep the key out of the repository (`.env` is git-ignored).
This layout follows the Vercel Python runtime documentation but has not been run on a live Vercel project from here: after the first deploy, open `/api/chat` in the browser; `{"enabled": true, ...}` means the key is in place.
```bash
python tests/test_chat.py             # the answer engine under node, compared with the CSV files
python tests/test_chat_proxy.py       # the Gemini proxy with Google stubbed: key handling, limits, errors, secret scan
```

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
