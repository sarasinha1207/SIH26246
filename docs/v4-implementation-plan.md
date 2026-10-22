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
* `src/v4/splits.py`, `src/v4/features.py`: leak-safe features (re-using the v3 design, extended for 60 months and the new channels), sampled origins and horizons to keep training size manageable, hierarchical context (trade, sector, district, state).
* Proposed splits by target month: train to 2015-12, validation 2016-01 to 2018-12, test 2019-01 to 2025-12 (includes COVID). Test is opened once.
* Check: no feature uses data after its origin; splits are disjoint and time-ordered; row counts and memory use recorded.
* Commit: `v4 phase 3: leak-safe splits and features for 60-month forecasting`

### Phase 4: training, tuning and the one-shot test
* `src/v4/train.py`: XGBoost per target (employed, vacancies, seekers) with horizon as a feature, Optuna tuning on validation only, 5 seeds each, baselines (seasonal naive, drift) for every horizon.
* Test: one pass; WAPE by horizon (12, 24, 36, 48, 60), by sector, trade and state; noise floor; no re-tuning afterwards.
* Check: the model beats the baseline where claimed; results written to `reports/v4/` with the exact numbers.
* Commit: `v4 phase 4: trained models and one-shot test results`

### Phase 5: intervals, flags, confidence labels
* Calibrated 90% intervals per horizon, confidence labels per target/sector/trade, early-warning flags at trade level (shortage and oversupply alerts and watches), flag precision from the validation and test periods.
* Check: interval coverage near 90% on the test; flag precision reported honestly.
* Commit: `v4 phase 5: calibrated intervals, flags and confidence labels`

### Phase 6: forecast 2026 to 2030, Demand Index, capacity gap, exports
* `src/v4/forecast.py`: refit on all history, forecast 60 months for all 7,925 series; trade forecasts reconciled to sector totals.
* Demand Index (0 to 100) from the normalised signal channels, with a written method; capacity-gap measure (forecast openings against seats sanctioned); rankings of trades and districts.
* Exports: compressed forecast and flag tables, per-state JSON shards, a manifest with checksums.
* Check: row counts, no missing values, intervals contain the forecast, trades add up to sectors, hashes recorded.
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
