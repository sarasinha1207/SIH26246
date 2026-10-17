# Phase 3 – Data Cleaning & Preprocessing

Status: **Approved** (sign-off in Section 9).
Reproduce: `python src/preprocessing/clean_panel.py` then `python tests/test_processed_panel.py` (15/15 tests pass; re-running produces an identical table).

---

## 1. Goal and exit criteria
Produce a typed, flagged, leak-safe base table from the approved raw panel, with every cleaning decision recorded. Phase 3 is complete when:
1. Integrity (missing, duplicate, impossible values) is checked and the result recorded. ✔
2. Types and keys are fixed (leading-zero LGD codes preserved, a series key and a real date added). ✔
3. Every outlier, shock and break is either removed with a reason or kept and flagged. ✔ (kept and flagged)
4. The time-ordered split is fixed before any exploration, so later phases cannot leak the hold-out. ✔
5. The output is covered by automated tests and is reproducible. ✔
6. The hold-out lock is enforced in code, not just by convention. ✔ (Section 5)
7. Every processed column is documented, with a rule on whether it may be a model input. ✔

## 2. Principles
* **No observed value is altered.** The pipeline compares all 28 retained measures with raw and fails if any differs (0 differ).
* **Real shocks are flagged, never smoothed.** A forecasting model must see COVID, policy dips and the e-Shram launch as they happened.
* **No feature engineering here.** Lags, logs, scaling, encoding and differencing belong to Phase 5.
* **Raw data is never rewritten.** Checksums from the Phase 2 manifest are re-verified by the tests.

## 3. Lineage
| Input (`data/raw/`) | Output (`data/processed/`) |
|---|---|
| `lmis_district_monthly_2011_2026.csv` (53,760 × 41) | `panel_monthly.parquet` (53,760 × 47) |
| `lmis_district_quarterly_2011_2026.csv` (17,920 × 40) | `panel_quarterly.parquet` (17,920 × 46) |
| `district_catalog.csv`, `sector_nco_crosswalk.csv` | `dim_district.csv` (56 rows), `dim_sector.csv` (5 rows: NIC, NCO anchor + 5 families, NSQF), `dim_series.csv` (280 rows: training-period volumes and a `Low_Volume` flag) |
| – | `SCHEMA.json` (dtypes, flag definitions, notes) |

Documentation: `docs/reference/PROCESSED_DATA_DICTIONARY.csv` (every column, with `usable_as_model_input` = Y / N / categorical).
Reports: `reports/phase3_cleaning_report.json` (step log), `phase3_column_profile.csv`, `phase3_anomalies.csv` (29 flagged rows).

## 4. Cleaning log
| Step | Result |
|---|---|
| Integrity gates | 0 missing · 0 duplicate keys · 0 negative values · 0 count-identity errors. The pipeline stops if any is non-zero |
| Typing and keys | Added `Series_ID` (`<district LGD>-<sector code>`, 280 series), `Date` (month start), `Quarter`, `Quarter_ID`, `Sector_Code`. LGD codes stay strings (`"07"` keeps its zero). Strings stored as categories, counts as integers |
| Dimension join | `Econ_Tier` joined from the district catalog (0 unmatched); this also enables the Phase 1 equity check |
| Dropped columns | `Timestamp_Month` (duplicate of `Timestamp`), `NIC_Code`, `NCO_Code`, `NSQF_Level` (constant within sector, now in `dim_sector.csv`). Nothing with information is dropped |
| Value preservation | 28 measures compared with raw: 0 modified |
| Quarterly file | Same keys, flags and split roles; reconciles with monthly means (max diff < 1); count identities exact; each quarter's flag equals "any month flagged" |
| Series volume | `dim_series.csv` computed from the last 24 *training* months only. 4 of 280 series have median vacancies < 50 (`Low_Volume`), mostly New Delhi district, where counts are in the single digits and noise dominates. Kept; Phase 8 reports metrics with and without them |

## 5. Flags and split policy
| Column | Definition | Rows (monthly) |
|---|---|---|
| `Is_Covid_Window` | 2020-03 to 2022-02 | 24 months × 280 |
| `Is_Policy_Shock` | Demonetisation 2016-11..2017-01 and GST roll-out 2017-07..2017-10 | 7 months × 280 |
| `Is_Eshram_Ramp` | From the Aug-2021 launch until the 3-month average growth of national seekers first drops below 2.5% a month → 2021-08 to 2023-02 | 19 months × 280 |
| `Is_Simulated_Future` | After 2026-10 (today is 2026-10-18) → Nov and Dec 2026 | 2 months × 280 |
| `Anomaly_Flag` | \|robust z\| > 6 against a centred 13-month median, per series, outside the COVID and policy windows | 29 rows (0.05%) |
| `Split_Role` | `train` ≤ 2023-12 · `validation` 2024 · `test` 2025-01 to 2026-12 | 43,680 / 3,360 / 6,720 |

**Hold-out lock:** Phase 4 exploration and Phase 5 feature decisions may use `train` and `validation` rows only. The `test` rows are touched once, in Phase 8. This matches the Phase 1 validation protocol. Note that `test` includes the two simulated months.

**Enforcement:** `src/common/data_access.py` provides `load_panel()`. It returns train and validation rows by default and raises `PermissionError` if `test` is requested without `unlock_test=True`. All later code should load data through it.

**Flags are never features.** `Anomaly_Flag` is built from a centred window and a full-sample scale, so using it as an input would leak future information. The window flags are for masking training rows and for reporting. `SCHEMA.json` lists a `model_input_blocklist`, and `load_panel(drop_blocklisted=True)` removes those columns. Masking COVID, policy and the e-Shram ramp together would leave 31,640 of 43,680 training rows (72%).

## 6. Treatment decisions
| Issue | Decision | Reason |
|---|---|---|
| Missing values | None exist. Rule if they appear: report and stop | Imputing would hide a data fault |
| Duplicates | None exist. Rule: stop | |
| Statistical outliers (29 rows) | **Keep, flag** | Isolated tails of noise, 0.05% of rows; winsorising would remove genuine volatility the forecast must reflect |
| COVID, demonetisation, GST | **Keep, flag** | Real shocks. Phase 5 decides whether to mask windows in training; the prototype did |
| e-Shram registry break | **Keep, flag** | The seeker pool shifts from an exchange-style register to a mass registry. Not a labour-market move, so models must treat it explicitly |
| Zeros (Transgender 151 rows, Edu_Below_Primary 410, Trainees_Certified 25) | Keep as true zeros | Small-count series; Phase 5 uses `log1p` for these |
| Nov–Dec 2026 | Keep, flag | Approved in Phase 2 |
| Wages | Left nominal | No price index in the data; real-wage conversion deferred (Phase 5, if a deflator is added) |
| Percentage columns | Kept alongside counts | Derived but convenient; counts remain the source of truth |
| Scaling, transforms, lags | Not done here | Phase 5 |

## 7. Skewness note for later phases
Counts are right-skewed (employment 3.2, vacancies 3.9, seekers 5.7, certified 6.9). Modelling log-changes, as the prototype did, handles this; no transformation is applied to the stored data.

## 8. Tests (`tests/test_processed_panel.py`, 15 of 15 pass)
Raw checksums unchanged · shapes, unique keys, 192/64 periods per series, sort order · leading zeros and no nulls · no value modified vs raw · gender/age/education sums exact (monthly and quarterly) · split boundaries · flag windows · quarterly flags equal "any month" · monthly/quarterly reconciliation · dimension joins · `SCHEMA.json` matches the tables · test period locked in the access helper · `dim_series.csv` uses training data only · processed dictionary covers every column.

## 9. Decisions and sign-off
| # | Decision | Recommendation |
|---|---|---|
| D1 | Keep all anomalies and shocks, flagged, with no imputation or winsorising | Yes |
| D2 | Split: train ≤ 2023-12, validation 2024, test 2025–2026 (locked until Phase 8) | Yes; it matches Phase 1 |
| D3 | Flag windows as defined in Section 5 (COVID, policy, e-Shram ramp, simulated months) | Yes |
| D4 | Keep wages nominal; no deflator available | Yes |
| D5 | Keep the quarterly table as a secondary view | Yes |

Sign-off (approved by the project owner):
- [x] Cleaning decisions D1, D4 accepted
- [x] Split policy and hold-out lock D2 accepted
- [x] Flag definitions D3 accepted
- [x] Quarterly table kept D5

Phase 4 (Exploratory Data Analysis) has started. It loads data only through `src/common/data_access.load_panel`, which excludes the test period.
