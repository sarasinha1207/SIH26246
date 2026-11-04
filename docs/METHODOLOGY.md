# Methodology

How KaushalSetu turns several imperfect labour-market signals into one **Demand Index**, forecasts employment, vacancies and job seekers five years ahead, and sets the result against training capacity. It is written so that each step can be reproduced and challenged: every formula is in the code named beside it, and every number quoted here is checked against the exports by `tests/test_v4_api.py`.

> **All data is simulated.** The simulator reproduces the *kinds* of imperfection real sources have (coverage that grows, lead and lag, noise, late start dates); it does not describe any real district. Section 11 says what changes when real sources replace it.

Contents: 1 Scope · 2 Data and signals · 3 The Demand Index · 4 Checking the index · 5 The forecasting engine · 6 Ranges · 7 Reconciliation · 8 Flags and confidence labels · 9 Capacity gap and severity · 10 How it was evaluated · 11 Assumptions and limits · 12 Reproducing it

---

## 1. Scope

| | |
|---|---|
| Geography | 10 states, all 317 districts (official LGD codes) |
| Industry and occupation | 5 sectors (NIC divisions), 5 NCO-2015 trades each: 25 trades |
| Series | 7,925 = 317 districts × 25 trades, monthly, January 2000 to December 2025 (312 months) |
| What is forecast | employed workers (E), active job vacancies (V), registered job seekers (S), 1 to 60 months ahead (January 2026 to December 2030) |
| What is derived | Demand Index, capacity gap, severity ranking, early-warning flags, confidence labels, two 90% ranges |

Code: `src/v4/config.py` holds the scope; nothing else types a state, trade or date.

## 2. Data and signals

Each series has the three forecast targets, training seats and certifications, wages, unemployment, population, worker shares, and **four demand channels**. The channels are the heterogeneous sources the problem statement asks to combine. Their identifiers are LGD district codes and NCO-2015 trade codes (series id, for example `118-CON-7111` for house builders in Agra); the v3 panel also carried NSQF levels, which the v4 panel does not.

| Channel | Column | What it measures | Imperfection built in (`src/v4/generate.py`) | In the Demand Index? |
|---|---|---|---|---|
| Administrative vacancies | `Active_Job_Vacancies` | Open jobs in the trade; also a forecast target | The reference signal; all months | **Yes** (the only channel in forecast months) |
| Job-portal postings | `Sig_Portal_Postings` | Postings on job portals | A share of all openings that rises logistically with online hiring (about a tenth of its eventual level in 2000, about half by 2012); leads the opening by a month; AR(1) plus white noise | **Yes** (history) |
| National Career Service | `Sig_NCS_Vacancies` | Vacancies listed on NCS | Starts in 2015-07; coverage grows from 2% to about 20% by 2025 (higher in construction and textiles); missing before launch | **Yes** (from 2015-07) |
| Quarterly hiring survey | `Sig_Hiring_Survey_Index` | An index of hiring intentions (2010-2019 = 100) | From 2009-01; one reading per quarter held until the next | No: an index relative to its own series cannot be compared between districts. Used as a model input. |
| Labour-force survey | `Sig_Labour_Survey_Employment` | Employment estimate | From 2017-07; quarterly; noisier for small series | No: it measures employment, not demand. Used as a model input. |
| Registered job seekers | `eShram_Registered_Seekers` | Supply side | The registry ramps up from August 2021 (a break, not a labour-market change) | No: supply, not demand. Forecast as a target. |

Why these choices: the index is meant to say *how strong hiring demand is*, so it uses only channels that count openings, and excludes the ones that measure employment or supply or cannot be compared across districts.

## 3. The Demand Index (0 to 100)

Code: `src/v4/demand_index.py` (the method is also written in its header).

For a district-trade *i* in month *m*, and each demand channel *c* in {vacancies V, portal P, NCS N}:

1. **Openings per worker, in logs.** `x_c = ln((signal_c + 1) / employed workers)`. Dividing by employment removes the size of the district; the log turns ratios into differences; the `+1` keeps empty cells defined.
2. **Position among peers.** `z_c` is `x_c` standardised across the districts of the *same trade in the same month* (mean 0, standard deviation 1). This removes every national or trade-wide shift in a channel, including the portal's growing coverage and NCS's launch, and keeps only how a district compares with its peers.
3. **Composite.** The mean of the available `z_c` (a channel that has not started contributes nothing), divided by its own standard deviation across the districts of the trade-month so that it again has standard deviation 1.
4. **National level.** `L = (ln(national V / national E of the trade) − its mean in 2018-2019) / (the mean cross-district standard deviation of x_V in 2018-2019)`. Steps 2 and 3 are relative, so a trade whose demand rises everywhere would not move; `L` carries the trade's national level, in units of the district spread, so that the index rises and falls with demand over the years.
5. **Index.** `DI = 100 × Φ(composite + L)`, where Φ is the standard normal distribution function. **50** is the median district of the trade at the 2018-2019 national level; **84** is one standard deviation above, **16** one below. The scale is bounded by construction.

**Forecast months** (2026-2030) use the forecast vacancies and employed workers only, because the other channels are measurements of the same openings, not separate forecasts: `composite = z_V` and `L` from the forecast national ratio. **Roll-ups** (state, sector, trade, India) are employed-worker-weighted means of the series indices.

**Worked example** (Agra, house builders, December 2025; the same figures are in `data/v4/exports/demand_index.parquet`): employed workers 105,743, vacancies 1,434, portal postings 247, NCS vacancies 449. Across the 317 districts of the trade the vacancy ratio `x_V` has mean −4.41 and standard deviation 0.24, and Agra's is −4.30, so `z_V = +0.46`; likewise `z_P = +0.85` and `z_N = +0.68`. The mean of the three is 0.66; rescaled to unit spread across districts the composite is **0.74**. The national level `L` is +0.03. `DI = 100 × Φ(0.74 + 0.03) =` **77.9**: Agra is in the upper quarter of districts for this trade.

## 4. Checking the index

What has been checked, and what has not:

* **The forecast-month version tracks the full one.** In history, the vacancy-only index (what forecast months use) correlates with the three-channel index at 0.89 to 0.94 in each year 2012-2025 (0.93 in 2025); mean absolute difference 8 to 10 index points (`reports/v4/forecast/demand_index_check.json`).
* **Bounds and scale.** Every value lies between 0 and 100; each trade-month has mean `z` 0 and spread 1 (unit tests on synthetic panels, `tests/test_v4_forecast.py`).
* **Not checked:** agreement with an external ground truth. The data is simulated, so a correlation with a real outcome (for example later placement results) cannot be computed. The weights (equal across available channels) are a modelling choice, not estimated. With real data the first task is to test the index against realised hiring.

## 5. The forecasting engine

Code: `src/v4/features.py`, `model_lib.py`, `tune.py`, `evaluate.py`, `deploy_fit.py`, `forecast.py`.

* **Direct multi-horizon.** One XGBoost model per target (E, V, S). One training example is (series, forecast origin *t*, horizon *h*); the horizon is an input; the target is the change in the log level, `ln(level at t+h) − ln(level at t)`. There is no recursion, so errors do not compound month on month.
* **Inputs (82 of 119 candidates).** Trailing growth over 1, 3, 6, 12 and 36 months, level against the recent average, 12-month volatility, vacancy and seeker rates and their changes, relative size within the trade, training seats and certification ratios, wage and unemployment, worker shares, growth and deviation of the four channels (a channel not yet started is missing; XGBoost handles that natively), and group aggregates. Every input uses only data at or before the origin; the year-ago anchor of horizon *h* is the latest observation in the target's calendar month that is not after the origin; calendar-trend proxies are kept out. A test cuts the data at the origin and checks the features are unchanged.
* **Inputs that were dropped.** The sector, trade and state-sector aggregates and near-unique identities (district, economic tier) let the trees memorise the period instead of the series: removing them cut the validation error of employed workers from 10.9% to 4.5% (`reports/v4/evaluation/ablation_validation.csv`).
* **Settings.** Optuna (TPE), 20 trials per target, scored on the validation years only (2010-2014). The number of trees for each twelve-month horizon band is also chosen there: employed 400, 250, 200, 100, 100; vacancies 100, 100, 100, 150, 150; seekers 250, 250, 250, 400, 400 (bands 1-12 to 49-60). Three random seeds are averaged.
* **Windows, by calendar time (never random).** Fit on targets to 2009; tune on 2010-2014; **test** on 2015-2019 (opened once, after the settings were fixed); **stress** on 2020-2025 (opened once, information only); final fit on all targets to 2025-12.
* **The final fit leaves out the shock.** A first fit on all pairs learned the 2020-2023 recovery (employment up 28% in three years, registered seekers ×2.7) as the normal outcome of an ordinary month and forecast seekers ×3.8 by 2030. The deployed fit leaves out the (origin, horizon) pairs that reach into March 2020 to December 2023 from an origin up to December 2023 (`BREAK` in `deploy_fit.py`). Long horizons are therefore learned from 2000-2019 dynamics, horizons up to 24 months also from 2024-2025. This is a judgement about a simulated shock, not a tuned choice; its side effect is lumpier seeker growth where the horizon crosses 24 months.

## 6. Ranges

Code: `src/v4/intervals.py`, `rollups.py`.

* **Split-conformal on the log change.** The score of a past forecast is its error `actual − predicted` (log scale). For a new forecast at horizon *h* the 90% range is `predicted + [q05, q95]`, with the quantiles taken over the scores of earlier *out-of-sample* forecasts of the same target and group at horizons *h−2 … h+2*, widened until the pool has at least 400 scores from at least 8 origins (100 scores for the aggregates). The pool holds only forecasts of windows the model had not seen, so the range does not shrink with the in-sample fit.
* **Scheme chosen on validation only** (lowest mean interval score, horizons up to 24): by horizon and sector for employed workers and vacancies, by horizon alone for seekers.
* **Two ranges.** *Usual*: calibrated on validation and test (2010-2019, no shock). *Wide*: also the stress window (2020-2025), so it allows for a shock. The wide range cannot be tested on the years it was calibrated on.
* **Aggregates have their own calibration.** Errors of neighbouring series move together, so the range of a state or of India is not the sum of series ranges: it is calibrated on the errors of the aggregate itself, by level (district-sector, state-sector, state, sector, trade, India). A range exists only where such a calibration exists; elsewhere the point forecast is given alone.
* **Coverage, honestly.** On the test years the usual range held for 87% of employed-worker outcomes, 85% of vacancies and 64% of seekers (target 90%). For the totals of a state or India it held about six times in ten on calm years and almost never in the shock years, which is why the wide range is shown for totals.

## 7. Reconciliation

Code: `forecast.reconcile`. The five trades of a district-sector are forecast separately; their rounded sum is made equal to the district-sector total by largest-remainder rounding to whole persons, so every trade stays within one person of its own forecast and totals at every level (district-sector, state-sector, state, sector, India) add up exactly. Ranges do not add up (section 6).

## 8. Early-warning flags and confidence labels

Code: `src/v4/early_warning.py`.

* **Flags are relative.** For each trade and target month, districts are ranked by forecast tightness, `ln(V / S)` (forecast vacancies per registered seeker). A **shortage alert** is the top tenth (percentile ≥ 90), a **shortage watch** 75 to 90; an **oversupply alert** is the bottom tenth (≤ 10), a watch 10 to 25. Because the flags are relative, about a tenth of districts are in each tail by construction: an alert means "among the tightest districts for this trade", not "openings exceed seekers".
* **Tested against the future.** Truth is the actual tightness of the target month being in the top (bottom) decile of its trade. On the test years, one to twelve months ahead, 72% of shortage alerts and 71% of oversupply alerts were right, against a base rate of about 10% (7 times better than chance). The benchmark is persistence (flagging from the tightness at the origin, nothing forecast): the model is only slightly better at 1-12 months (72.4% against 70.7% for shortage alerts) and a little more at 49-60 months (62.2% against 57.0%), so most of the flags' value is that tightness is persistent, with a modest gain from forecasting it.
* **Alerts that begin or end.** Comparing the actual tightness of December 2025 with the forecast at 12, 36 or 60 months shows which series *enter* or *leave* an alert tail. Alerts are persistent: of the 800 shortage and 774 oversupply alerts now, 103 and 105 are out of their tail 12 months ahead (143 and 146 at 36 months), and 103 and 108 have moved in. Because flags are relative, a series can leave a tail because others rose faster, not because it fell. The list (`app/dashboard/data/transitions.json`, the Early warnings page and `/api/flags?change=entering`) also gives the first forecast month at which a series is in the tail.
* **Confidence labels.** Per target, trade and twelve-month horizon band: the level-scale WAPE that earlier out-of-sample forecasts of the same trade and band reached. **High** up to 8%, **Medium** up to 20%, **Low** above; a low-volume series is one level lower. A label is useful only if observed error rises from High to Low on later windows; it does for employed workers and vacancies on the test years, not reliably for seekers, and the site says so.

## 9. Capacity gap and severity ranking

Code: `src/v4/capacity.py`, `exports.py`; the ranking in `app/dashboard/dashboard.js` and `app/api/_v4api.py`.

* **Inputs.** *Openings*: the mean of the 12 monthly vacancy forecasts of the calendar year. *Seats*: the annual seats sanctioned in 2025-26 (the December 2025 stock), **held flat to 2030** because no seat plans are forecast (an assumption). *Expected certified*: seats × the median certification rate of 2023-2025 (certified in the year ÷ seats, capped at 1.2).
* **Absolute measures.** `openings per seat = openings ÷ seats`; `certified per opening = expected certified ÷ openings`. Below 1 certified per opening, fewer people finish training in a year than there are openings.
* **Relative mismatch.** `ln(seat share ÷ vacancy share)` of the district within its trade across the 317 districts; below −0.5 (a seat share under 0.6 times the openings share) is "seats fall short of demand", above +0.5 (over 1.65 times) "seats exceed demand".
* **Severity ranking.** `score = ln(certified per opening)` of a year, banded by the ratio: severe at 2 (or ½) or more, high at 1.5, moderate at 1.25, otherwise balanced; negative is undersupply, positive oversupply. Trades, states, state-trade pairs, districts, district-sectors and district-trades are ranked for any year to 2030. The bands are conventions, not tuned.
* **Seat scenario.** Seats are multiplied by `1 + c/100` from a chosen year (`c` from −90% to +500%); expected certified scales with seats (the certification rate is unchanged) and the forecast openings are unchanged, so `certified per opening` in a year `y` is `rate × seats × (1 + c/100) / openings(y)` and the score and band follow as above. **Seats needed for a target ratio T** in year `y` are `openings(y) × T / rate`; the change from today's seats can be negative (surplus capacity). Totals add the rows, with a weighted ratio. No lag is modelled between sanctioning a seat and a trainee being certified, teaching capacity is not limited, and a uniform percentage across rows is a simplification (narrow the scope with the trade, state and district filters). The dashboard card (Capacity gap page) and `/api/scenario` use the same formulas.
* **Caveat.** Openings are a monthly stock and certification an annual flow, so the ratios are a ranking of where capacity is stretched, not a count of unfilled places.

## 10. How it was evaluated

All numbers are WAPE (total absolute miss ÷ total actual, lower is better) against the best of three simple forecasts in each cell (no change, seasonal naive, damped trend). Tables: `reports/v4/evaluation/`.

| Target | Test 2015-2019 model | Best simple | Closer | Shock years 2020-2025 model | Best simple | Closer |
|---|---|---|---|---|---|---|
| Employed workers | 4.64% | 5.65% | 17.8% | 14.29% | 16.65% | 14.2% |
| Job vacancies | 13.14% | 13.61% | 3.5% | 20.57% | 24.51% | 16.0% |
| Registered job seekers | 16.15% | 17.63% | 8.4% | 43.01% | 42.90% | −0.3% |

Employed workers beat the baseline at every horizon (4% at 1-12 months to 30% at 49-60). Seekers are 3.7% worse in the first year and 23% better in the fifth; vacancies are better to 48 months and 3% worse beyond. In the shock years seekers are under-forecast by 41%: a pandemic and a registration drive cannot be foreseen from earlier years. On two fresh simulated worlds (seeds 101 and 202, no refit) employed workers scored 4.61% and 4.60% against 5.61% and 5.55%, so the test result is not one lucky draw.

## 11. Assumptions and limits

1. **Simulated data**, calibrated where possible to PLFS, Census 2011, NASSCOM and the e-Shram timeline; everything else is a stated assumption. Results show the method, not the real market.
2. **Index weights are equal and not estimated**; the national level term uses 2018-2019 as its reference.
3. **Seats are held flat**; there is no seat-plan input yet.
4. **Seekers are the least reliable measure**, and long horizons rest on pre-2020 behaviour.
5. **The usual ranges are calibrated on calm years**; totals need the wide range; some combinations have no checked range.
6. **Flags are relative**; thresholds (90, 75, 25, 10; labels at 8% and 20%) are conventions fixed before the test window was opened.
7. **Severity bands** (ratios 1.25, 1.5, 2) are conventions.
8. **Exclusion of the 2020-2023 shock** from the final fit is a judgement.

**With real data** the order of work is: replace each simulated channel with its real extract (job-portal postings, NCS, hiring survey, PLFS, e-Shram), keeping the identifiers (LGD, NCO-2015); re-check that the channels' relative scales are comparable after the within-trade standardisation; test the Demand Index against realised hiring; refit and re-run the one-shot test on a held-out period; and replace the flat seats with sanctioned seat plans.

## 12. Reproducing it

Everything derives from seed 42 and the code in `src/v4/`; file checksums are in `data/v4/DATA_MANIFEST.json`, `SPLITS_MANIFEST.json` and `FORECAST_MANIFEST.json`. The commands, in order, are in the README (section 7) and the refresh steps in `docs/RUNBOOK.md`. The tests that guard this document are `tests/test_v4_forecast.py`, `test_v4_intervals.py` and `test_v4_api.py`.
