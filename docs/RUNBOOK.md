# Runbook: refresh, checks, deployment

Everything runs from the project root, with Python 3.13 and `requirements.txt` installed (xgboost 3.4.1, pandas 2.2.3, numpy 2.1.3). The data is simulated until a real source is connected; with real data step 1 becomes the ingestion job.

## A refresh in order
1. **New month of data.** With the simulator this is a regeneration (`python src/v4/generate.py`); with real data, add the month to `data/v4/raw/` and update `data/v4/DATA_MANIFEST.json`. The origin month is `C.ORIGIN` in `src/v4/config.py`.
2. **Final fit** (only when a trigger below fires; otherwise reuse `models/v4/deploy/`): `python src/v4/deploy_fit.py` (about an hour). It leaves out the training pairs that reach into the 2020-2023 shock and recovery (`BREAK`); revisit that choice when a new shock has been observed.
3. **Forecast, index, capacity, exports:** `python src/v4/forecast.py`, `demand_index.py`, `capacity.py`, `exports.py`. The last writes `data/v4/FORECAST_MANIFEST.json` with the SHA-256 of every file.
4. **Check:** `python tests/test_v4_forecast.py`. It fails if any of the 7,925 series or 60 months is missing, if a range does not contain its forecast, if trades do not add up, or if a checksum differs.
5. **Rebuild the site from the exports:** `python src/v4/build_dashboard.py`, `build_map_data.py`, `build_site_data.py`, then `python src/app/build_pages.py`. Nothing on the site is typed in by hand.
6. **Check the site:** `python tests/test_v4_dashboard.py`, `test_v4_api.py`, `test_app.py`, `test_chat.py`, `test_chat_proxy.py`. Open the dashboard in both languages and both themes and run `tests/a11y_audit.js` in the browser console on a few pages: every list it returns should be empty.
7. **Commit and push to `main`.** Vercel redeploys from the repository; there is no build step.

## Deployment
* Vercel project: Root Directory `app`, no framework, no build command. `app/vercel.json` sets the security headers, long caches for versioned scripts and styles, and for each function a time limit and the data it bundles (`dashboard/data/**` for the five forecast API functions).
* Seven functions, all standard library only (`app/requirements.txt` lists no packages on purpose, so Vercel does not install the ML stack): `/api/chat` (needs `GEMINI_API_KEY` in the project's environment to switch Gemini on; set a spending cap in Google AI Studio too), and `/api/forecast`, `/api/flags`, `/api/demand-index`, `/api/capacity-gap`, `/api/severity`, `/api/meta` (settings `API_RATE_PER_MINUTE`, default 60, and `API_DAILY_CAP`, default 20000; the limits are in memory, per instance).
* Budget (checked by `tests/test_v4_api.py`): the deployed folder under 60 MB (now about 24 MB, 7 MB compressed), no file over 6 MB, the first load of any page under 450 KB compressed, the largest state's data read in under 2 s cold, and a typical API call in under 50 ms.
* The v3 dashboard data file (`app/dashboard/data/dash_data.js`) is git-ignored and not deployed; the submitted version is the tag `submitted-v1`.

## Retraining triggers (starting values; revisit when monitoring exists)
* A new calendar year of data is available (annual refit), or
* the rolling WAPE of a target at horizons 1-12 is more than 25% above its test value (`reports/v4/evaluation/test_metrics.csv`), or
* the usual 90% range of a target stays below 80% coverage for three months in a row, or
* a structural break is known (a registry change like e-Shram, a policy shock). After a break, decide whether to extend `BREAK` in `src/v4/deploy_fit.py` and say so in the plan.

## Never do
* Change a setting, a seed, a threshold or the choice of inputs after looking at the test or stress window: those windows were opened once (`reports/v4/evaluation/test_opened.json`, `stress_opened.json`). A change needs a fresh world check (`src/v4/fresh_worlds.py`) and a note in the plan.
* Build features with data after the origin month.
* Use anything under `Archived/`, `data/superseded/` or `*/quarantine/`.
* Commit `.env` or any key.

## Rollback
* Site and API: revert the commit on `main` (Vercel redeploys the earlier version); the previous export tables are in git history, and `data/v4/FORECAST_MANIFEST.json` names every input by hash.
* Submitted version: `git checkout submitted-v1`.
* Models: `models/v4/deploy/` (git-ignored) is rebuilt by `deploy_fit.py`; `models/v4/deploy_all_pairs/` holds the first fit that repeated the shock, for comparison only.

## Reading the output
* Forecast ranges: the usual range is calibrated on calm years (2010-2019); read the wide range for totals of many series and in any year that may be unusual.
* Confidence labels: employed workers are mostly high, vacancies medium or low, seekers medium or low with an order that is not reliable.
* Flags are relative to the trade in the same month; the capacity gap holds seats flat; seeker forecasts and the fifth year are the weakest.
* Everything is simulated data until a real source is connected.
