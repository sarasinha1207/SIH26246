# KaushalSetu v4: implementation plan

Goal: close the remaining gaps between the project and problem statement 26246 (MSDE, AI-Enabled Labour Market Intelligence and Skill Demand-Supply Forecasting Engine).

The submitted version stays untouched: it is the commit tagged `submitted-v1`. All v4 work happens on the `improvements` branch, in new folders (`src/v4/`, `data/v4/`, `models/v4/`, `outputs/v4/`, `reports/v4/`), so v3 can always be rebuilt.

## What changes

| | Submitted (v3) | v4 |
|---|---|---|
| States | 4 (Maharashtra, Delhi, West Bengal, Tamil Nadu) | 10: adds Gujarat, Uttar Pradesh, Karnataka, Telangana, Kerala, Punjab |
| Districts | 56 (only some of West Bengal and Tamil Nadu) | 317: every district of the 10 states (LGD, 2024 layer) |
| Sectors | 5 | the same 5 |
| Trades | none (sector level) | 5 NCO-2015 trades per sector = 25 |
| Series | 280 | 317 x 25 = 7,925 |
| History | 2011-01 to 2026-10 | 2000-01 to 2025-12 (312 months) |
| Forecast | 12 months | 60 months (2026-01 to 2030-12), forecast origin 2025-12 |
| Forecast rows | 10,080 | 7,925 x 3 targets x 60 = 1,426,500 |
| Languages | English, Hindi | English, Hindi (unchanged, by decision) |

Fixed decisions (from the project owner):
* All 10 states with all of their districts; 5 sectors only; 5 trades per sector; trades are forecast and shown in the dashboard.
* Data 2000 to 2025, forecast the next 5 years.
* Only English and Hindi for now.
* Each phase ends with a working, tested state so it can be committed on its own.

Working assumptions (recorded in `src/v4/config.py` and the data documents, open to change):
* The state/sector table from the brief is used as sector weights: the dominant state of a sector gets x1.6, a runner-up x1.25, every other state x1.0 (Delhi and West Bengal are not in the table, so x1.0). All 5 sectors exist in all 10 states.
* The 25 trades are the 25 NCO-2015 occupation families already in `data/raw/sector_nco_crosswalk.csv`.
* The data stays simulated and is labelled that way everywhere. Trades add up to their sector in every district and month.

## PS requirements and where each is closed

| PS requirement | Closed in phase |
|---|---|
| Aggregate and normalise demand signals from several sources | 2 (separate simulated channels), 6 (Demand Index) |
| Cross-reference demand with training capacity and seats by sector, trade, district | 2 (seats per trade), 6 and 7 (capacity-gap page) |
| Forward-looking gap forecasts at sector and district level, updated periodically | 4, 5, 6 |
| Rank trades and geographies by severity | 6, 7 |
| Interactive dashboard, drill-down from national to district | 7 |
| Documented method for one demand index | 6 |
| Early-warning flags | 5, 6 |
| API / export layer | 6 (files), 9 (endpoints) |
| Multilingual, accessible interface | 7, 8, 9 |

## Phases (one commit each)

Each phase: what is built, how it is checked, and the commit message to use. A phase is finished only when its checks pass.

### Phase 0: plan, configuration, scaffolding
* This plan; `src/v4/config.py` (states with LGD codes, sectors, 25 trades, sector-state weights, date ranges, horizons, seeds); the 317-district LGD list `data/v4/lgd_districts_10_states.csv`; `tests/test_v4_config.py`; `.gitignore` rules for large v4 files.
* Check: config test passes (10 states, 317 districts, 5 sectors x 5 trades, 312 months, 60 horizons).
* Commit: `v4 phase 0: implementation plan, configuration and district list`

### Phase 1: district catalogue (317 districts)
* `src/v4/catalog.py` builds `data/v4/district_catalog.csv`: official names and LGD codes, 2011 population, annual growth, economic tier (16 existing tiers, assigned by documented rules plus a named list of known hubs), state multipliers for the six new states.
* Populations: Census 2011 district figures read from public tables (`data/v4/census_2011_district_tables.csv`, source recorded per row); the 56 v3 districts keep their v3 values. Districts that lost territory to a district created after 2011 (Gujarat 2013, Pathankot 2011) are reduced by the new district's population; the Botad, Mahisagar and Morbi shares between two parents are assumptions.
* Check: 317 unique LGD codes; state sums match the Census totals within 0.1% (largest gap 0.015%); every district has a tier, an area and a source; map geometry exists for every code.
* Commit: `v4 phase 1: catalogue of 317 districts in 10 states`

### Phase 2: trade-level dataset, 2000 to 2025
* `src/v4/generate.py` (seeded): monthly employed, vacancies, registered seekers, seats sanctioned, trainees certified, wage, unemployment rate for 7,925 series, 312 months. Trades split each district-sector series with trade-specific trends, seasonality and shocks, and add exactly to the sector totals.
* Separate simulated demand-signal channels per series (job-portal postings, industry hiring survey, NCS-style vacancies, e-Shram registrations, PLFS-style employment) with different coverage, lag and noise; these feed the Demand Index in phase 6.
* The 2000 to 2010 years need national paths (indices, LFPR, unemployment) extended backwards; COVID, demonetisation/GST and the e-Shram ramp are kept in their real years.
* Output: `data/v4/raw/*.parquet` (git-ignored, rebuilt from the seed), `data/v4/DATA_MANIFEST.json` (tracked, with checksums), a short data dictionary.
* Check: sums of trades equal sectors; no negatives or gaps; per-capita ratios plausible; state-sector weights respected; same seed gives the same checksums; size and run time recorded.
* Commit: `v4 phase 2: trade-level dataset for 10 states, 2000-2025`

### Phase 3: splits and features for a 60-month horizon
* `src/v4/splits.py`, `src/v4/features.py`, `src/v4/build_phase3.py`: leak-safe features (the v3 design extended to 60 months, 25 trades, group aggregates for sector, trade and state-sector cell, and the four source channels), and time windows with a strict origin rule.
* A 60-month horizon needs 60 months of evaluation targets after the last fitted month, so the windows are cut by target month: train 2000-2009, validation 2010-2014 (tuning), test 2015-2019 (opened once, calm years), stress 2020-2025 (opened once: COVID-19 and the e-Shram break, information only). Each evaluation fit uses everything before its window: validation fit on targets to 2009, test fit on targets to 2014, stress fit on targets to 2019; the deployed model is fitted on all of 2000-2025. Every evaluation row starts after the last fitted month, for all 60 horizons.
* Sampling: about 1/6 of the (origin, horizon) pairs of each window, at least 6 origins per horizon; the training window has 4.5 million rows with 111 model inputs (1.9 GB, built in 8 seconds).
* Check: windows tile 2000-2025; fit rows use targets up to the cut only; evaluation rows start after it and cover all 60 horizons; test and stress are locked; rewriting every value after month 200 leaves all features for earlier origins unchanged; the year-ago anchor never looks past the origin for any horizon.
* Commit: `v4 phase 3: leak-safe splits and features for 60-month forecasting`

### Phase 4: training, tuning and the one-shot test
* `src/v4/model_lib.py`, `ablation.py`, `tune.py`, `evaluate.py`, `fresh_worlds.py`: one XGBoost model per target (employed, vacancies, seekers) with the horizon as an input; 3-seed ensembles; baselines no change, seasonal naive and damped trend (the best of the three in each cell is the comparison).
* Inputs: 82 of 119 candidates. Dropping the sector, trade and state-sector aggregates and the near-unique identities (district, tier) cut the validation error of employed workers from 10.9% to 4.5%: they let the trees memorise the period instead of the series. Time-proxy features stay out, as in v3.
* Tuning: Optuna (20 trials per target) on the validation window only; the number of trees per horizon band is also chosen there (employed 400/250/200/100/100, vacancies 100/100/100/150/150, seekers 250/250/250/400/400 for horizons 1-12 ... 49-60).
* Test (2015-2019, fit on targets to 2014, scored once): WAPE of the model against the best baseline, all horizons: employed 4.64% vs 5.65% (17.8% better), vacancies 13.14% vs 13.61% (3.5% better), seekers 16.15% vs 17.63% (8.4% better). Employed is better at every horizon (3.7% at 1-12 months, 30.4% at 49-60). Vacancies are better to 48 months and 3.0% worse at 49-60. Seekers are 3.7% worse than the baseline in the first two years and 15-23% better in years four and five. Seekers are under-forecast on average (bias -14.8%).
* Stress (2020-2025, fit on targets to 2019, scored once, information only): employed 14.29% vs 16.65% (14.2% better), vacancies 20.57% vs 24.51% (16.1% better), seekers 43.01% vs 42.90% (no gain; under-forecast by 41%: the model cannot know the COVID-19 and e-Shram jump in seekers). Employed in the first year is 7.1% worse than the baseline.
* Fresh worlds (the test-fit models, not refitted, on two other simulated worlds, seeds 101 and 202): employed 4.61% and 4.60% (best baseline 5.61% and 5.55%), vacancies 13.02% and 12.55% (13.63% and 13.45%), seekers 15.77% and 16.32% (17.37% and 17.91%). The test result is not one lucky draw.
* Caveats to repeat in the documents: all data is simulated; validation scores are not an honest estimate (the validation window was used to tune); the test window is calm by design; long-horizon accuracy is limited by regime changes the model has not seen; vacancies and seekers are noisier than employed workers and do not beat the baseline everywhere.
* Check: ablation, tuning trials, per-window metrics (by slice and horizon band), summaries, lock files (`test_opened.json`, `stress_opened.json`, same parameter hash) and `fresh_worlds.csv` are in `reports/v4/evaluation/`; fitted models (54 MB) are in `models/v4/` (git-ignored).
* Commit: `v4 phase 4: tuned models, one-shot test and stress results`

### Phase 5: intervals, flags, confidence labels
* `src/v4/predictions.py`: out-of-sample predictions of the phase 4 models for the validation, test and stress windows (git-ignored, `data/v4/interim/`). `src/v4/intervals.py`: split-conformal 90% intervals on the log change, quantiles by horizon (neighbouring horizons pooled until at least 8 origins and 400 scores), optionally by sector, volume class or scaled by the series' own volatility. `src/v4/early_warning.py`: trade-level flags and confidence labels.
* Scheme choice (validation only: calibrate on targets 2010-2012, check 2013-2014, horizons to 24): employed and vacancies by horizon and sector, seekers by horizon only. Scaling by the series' own volatility did not help (`interval_scheme_selection.csv`), so intervals depend on horizon, sector and target, not on the individual series.
* Coverage of the usual 90% range, calibrated only on earlier windows: test employed 86.6% (width 18%), vacancies 84.9% (64%), seekers 63.9% (43%); stress employed 31.1%, vacancies 66.0%, seekers 36.5%. Seekers under-cover even in ordinary years (the model under-forecasts them by 15%) and every target under-covers when a shock arrives that no earlier window held (COVID-19, e-Shram). Coverage also differs between forecast origins (`interval_coverage_by_origin.csv`): rows of one origin share the same shocks, and a 60-month horizon has one to three origins per window.
* Two ranges are deployed (`data/v4/interval_calibration.csv`): the usual range (calibrated on validation + test) and the wide range (also the stress window; leave-one-window-out coverage: validation 93-96%, test 84-99%, widths of 40-110% for employed workers and vacancies and 270% for seekers). The dashboard states which range is shown.
* Flags (relative, per trade across all districts, from the forecast vacancy-to-seeker coverage): shortage alert (top decile), watch (75th-90th percentile), oversupply watch and alert likewise. On the test window, all horizons: alerts hold the true tail-decile district 65.6% (shortage) and 63.7% (oversupply) of the time against a base rate of about 10% (lift 6.5), and 92% are in the outer quartile; the persistence benchmark (the same rule on today's coverage) reaches 61.8% and 60.2%. The gain over persistence is 3-5 points, larger at 25-60 months. Recall of the tail by alert or watch is 92%. Stress window: 64.0% and 61.3% against 61.5% and 58.9%. Flags are issued for every series; low-volume series have the same precision but noisier monthly counts.
* Confidence labels (High up to 8% expected WAPE, Medium up to 20%, Low above; one level lower for low-volume series) come from the error of earlier windows for the same trade and horizon band (`data/v4/confidence_cells.csv`). On the test window the observed error rises from High to Low for employed workers (4.5%, 5.6%, 13.2%) and from Medium to Low for vacancies (12.8%, 16.0%); for seekers the order is not reliable (9.7%, 18.7%, 16.7%), and in the stress window no target keeps the order. Phase 6 therefore shows seeker labels with this caveat.
* Check: tests on synthetic data (coverage of exchangeable errors, group quantiles, long-horizon pooling, flag levels, perfect-forecast precision, label thresholds) and on the recorded results (complete calibration table, coverage not overstated, flags beat chance and are compared with persistence); tables in `reports/v4/evaluation/`.
* Commit: `v4 phase 5: calibrated intervals, flags and confidence labels`

### Phase 6: forecast 2026 to 2030, Demand Index, capacity gap, exports
* `src/v4/deploy_fit.py`, `forecast.py`: the final models are refitted on 2000-2025 with the tuned settings of Phase 4 (3 seeds per target, nothing re-tuned) and forecast 60 months (2026-01 to 2030-12) for all 7,925 series. The five trades of a district-sector are reconciled to the rounded district-sector total (largest remainder), so point forecasts add up exactly.
* **A first fit on all pairs was rejected.** It learned the 2020-2023 shock and recovery (employment +28% in three years, registered seekers x2.7) as the normal outcome of an ordinary month: seekers x3.8 by 2030 and employment growth of 4 to 6% a year against about 2.7% recently. The deployed fit therefore leaves out the (origin, horizon) pairs that reach into the break (2020-03 to 2023-12) from an origin up to 2023-12 (`BREAK` in `deploy_fit.py`; 1,255 pairs to 927 per thinning). Long horizons are learned from 2000-2019 dynamics, horizons up to 24 months also from 2024-2025. This is a judgement about a simulated shock, not a tuned choice; the first fit is kept in `models/v4/deploy_all_pairs/` (git-ignored) for comparison. A visible side effect: seeker growth is lumpier where the horizon crosses 24 months (9 to 11% a year at 25 to 31 months against 4 to 5% elsewhere).
* Result: India employed 92.0 M (Dec 2025) to 95.0 M (Dec 2026) and 101.3 M (Dec 2030), about 1.9% a year; vacancies 1.8 M to 1.95 M; registered seekers 25.9 M to 32.0 M. Construction is the largest sector (44.4 M employed in 2030).
* Two 90% ranges per series and month: "usual" (calibrated on validation and test) and "wide" (also the stress window); ranges always contain their own point forecast. Aggregates (district-sector, state-sector, state, sector, trade, India) have their own calibration (`rollups.py`; `reports/v4/evaluation/aggregate_interval_coverage.csv`). **Aggregate ranges are indicative:** errors of neighbouring series share the same drift, so coverage of the usual range at state and India level is low (employed 59% on the test window, 2 to 3% in the stress window; seekers 5 to 8% on the test window), while district-sector ranges behave like series ranges (86 to 87% for employed and vacancies on test). Show the wide range for aggregates; the India wide range is very wide (employed up to +57% at 60 months).
* Demand Index (0 to 100, `demand_index.py`, method written in the file header): cross-district standardised openings per worker over the vacancy, job-portal and NCS channels (V only in forecast months) plus a national level shift against 2018-2019; 50 is the median district of the trade at the 2018-2019 level. In history the vacancy-only index tracks the three-channel index with correlation 0.92 to 0.94 (`reports/v4/forecast/demand_index_check.json`); roll-ups are employed-weighted.
* Capacity gap (`capacity.py`): forecast average vacancies of the year against seats sanctioned in 2025-26, **held flat at the December 2025 stock (an assumption: no seat plans are forecast)**, and expected certified (seats x median certification rate 2023-2025). Absolute measures: openings per seat and certified per opening; relative measure (as in v3): log of seat share over vacancy share within the trade, thresholds +-0.5. Nationally only Construction has fewer certified trainees than openings (0.57 per opening in 2026, 0.51 in 2030); 7.5% of district-trades are classed "Seats fall short of demand", 34% "Seats exceed demand". Most stretched: construction labourers (CON-9313), Uttar Pradesh and West Bengal.
* Exports (`exports.py`, in `data/v4/exports/`): `forecast_rollups.csv.gz`, `capacity_gap_*.csv`, `flag_alerts.csv` (alerts at 12, 36 and 60 months), `rankings.csv` are tracked; the series-level parquet files and the 10 per-state JSON shards (28 MB) are git-ignored and rebuilt by the pipeline. `data/v4/FORECAST_MANIFEST.json` records row counts, sizes and SHA-256 of every file and of the inputs (models, tuned settings, calibration tables, data manifest). All data are simulated and labelled so in the manifest.
* Flags: 10% of series fall in each alert tail by construction (relative to the other districts of the trade); confidence labels as in Phase 5 (seeker labels are not reliable in order).
* Check: `tests/test_v4_forecast.py` (reconciliation, Demand Index, capacity measures on synthetic data; complete forecast without missing values, ranges contain the point, trades add up to district-sectors and continue from December 2025, roll-ups add up to India, Demand Index in range and close to the three-channel index, manifest checksums, 10 shards).
* Commit: `v4 phase 6: 2026-2030 forecasts, demand index and capacity gap`

### Phase 7: dashboard
* Data delivery split into a small core file (roll-ups, flags, rankings) and per-state shards loaded on demand; filters for state, district, sector and trade; trade forecast charts with 90% ranges; Demand Index page; capacity-gap page; trade rankings; CSV and JSON exports.
* Check: loads on a phone-sized screen with acceptable file sizes; every figure traced to the exports; tests updated.
* Commit: `v4 phase 7: dashboard with trade forecasts, demand index and capacity gap`

### Phase 8: public website, map and assistant
* Map of all 317 districts (LGD boundaries); home, about and resources pages updated to the new scope and numbers; Hindi text for new content; assistant engine updated to the new data (trades, five-year horizon).
* Check: the build produces the site from the exports only; English and Hindi both complete; assistant tests pass.
* Commit: `v4 phase 8: website, 317-district map and assistant for v4`

### Phase 9: API, accessibility, tests, documentation, deployment check
* Read-only API on Vercel (`/api/forecast`, `/api/flags`, `/api/demand-index`, filters for state, district, sector and trade) with the chat endpoint's protections; API documentation page.
* Accessibility audit and fixes; full test run; README, architecture and lifecycle diagrams updated; deployment size and speed check.
* Commit: `v4 phase 9: forecast API, accessibility, documentation and deployment checks`

## Risks and how they are handled
* **Long-horizon accuracy.** Five-year forecasts of simulated data will be less accurate than 12-month ones. Accuracy is reported per horizon and confidence labels say so; the documents state that results show the method, not the real labour market.
* **Size.** 1.4 million forecast rows cannot ship in one file: sharded delivery and compressed exports (phase 6 and 7). Raw data and models are git-ignored when large; checksums are tracked.
* **Run time.** Five times more series and five times more horizons. Origins and horizons are sampled in training; run times are measured in phase 3 before committing to the tuning budget.
* **Small trades in small districts.** Noisier series: the confidence labels and low-volume flag from v3 are kept.
* **Data source honesty.** District populations and any figure copied from a public source are listed with the source; assumptions are labelled as assumptions.
