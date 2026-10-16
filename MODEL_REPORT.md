# LMIS Forecasting Model – Method, Results, Limitations

Script: `lmis_forecast_model.py` (about 30 s to run). Data: `lmis_district_monthly_2011_2026.csv` only. Nothing under `Archived/` is read, and the script asserts this.

## What it does
A global LightGBM model forecasts, for each of 280 district × sector series, three quantities 1–12 months ahead:

| Target | Role |
|---|---|
| `Total_Employed_Workers` | employment / demand outlook |
| `Active_Job_Vacancies` | demand signal |
| `eShram_Registered_Seekers` | supply proxy (the dataset has no training-seat/outturn column) |

* One model per target, direct multi-horizon (horizon is a feature). Target is the log-change `log y[t+h] − log y[t]`.
* The model learns a correction on top of a seasonal + drift baseline (`y[t+h−12] − y[t−12]`).
* Features: lagged changes (1/3/6/12 m), 12-month relative level and volatility, sector-wide momentum, wage, unemployment, vacancy/seeker rates, demographics, population, district, sector, calendar month.
* Training windows that touch the COVID shock (2020-03..2022-02) are dropped. For seekers, windows touching the e-Shram roll-out ramp (2020-12..2022-01) are dropped too. Both are exogenous breaks the model cannot anticipate.
* The two options were chosen on the validation fold (2024), not the test fold.
* Prediction intervals (90%) come from empirical residual quantiles per target and horizon.

## Validation design (no leakage)
| Fold | Train targets | Evaluate on |
|---|---|---|
| A (early stopping) | ≤ 2023-12 | 2024-01..12 |
| B (test) | ≤ 2024-12 | origins 2024-12..2026-11, targets 2025-01..2026-12 |
| Final | ≤ 2026-12 | forecast 2027-01..12 |

## Test-fold results (WAPE %, all horizons, lower is better)
| Target | LightGBM | Seasonal naive + drift | Seasonal naive | Last value |
|---|---|---|---|---|
| Employed | **0.92** | 1.23 | 3.76 | 3.41 |
| Vacancies | **5.51** | 10.28 | 8.22 | 8.03 |
| Seekers | **4.55** | 8.54 | 6.70 | 7.45 |

* Accuracy is flat across horizons (employed 0.73% at h=1, 1.16% at h=12), as expected for smooth trend × season data.
* The 90% intervals cover 91.3% (employed), 90.5% (vacancies) and 91.9% (seekers) on the held-out fold.
* Vacancies and seekers are simulated with i.i.d. noise of about 6% and 5% (see the generator). That puts the irreducible WAPE near 4–5%. The model is at the noise floor, so a lower number should not be expected from it.

## Outputs (`model_outputs/`)
| File | Content |
|---|---|
| `forecast_2027_monthly.csv` / `_quarterly.csv` | point forecasts + P05/P95 for the three targets, net gap, coverage |
| `gap_ranking_2027.csv` | per district × sector: net gap (persons), coverage (openings per registered seeker), status flag, trend flag, surplus/shortage ranks (overall and in-sector) |
| `backtest_metrics.csv`, `interval_coverage.csv`, `feature_importance.csv`, `model_metadata.json` | evaluation and audit trail |
| `models/lgbm_*.txt` | saved LightGBM boosters |

Flag thresholds (`COVERAGE_*`, `TREND_ALERT` at the top of the script) are placeholders: Acute Shortage if coverage ≥ 1.0, Oversupply Watch below 0.20, Saturation Risk below 0.10, and a trend alert at ±8% change.

## Limitations to know before presenting
1. **Supply is a proxy.** The problem statement asks for gaps against training capacity and seat allocation. This dataset has none, so supply = e-Shram registered seekers. Replace it with real seat/outturn data when you have it. The pipeline is target-agnostic.
2. **Gap ranks are driven by sector and size, not by district behaviour.** In the generator, vacancies and seekers are fixed ratios of employment. Coverage therefore varies only ±10% within a sector, and every district in a sector gets the same status flag (all 56 Construction rows are "Saturation Risk", and so on). Persons-level ranking is meaningful (big districts have bigger gaps); relative ranking between districts of the same sector is mostly noise. Every trend flag comes out "Stable" for the same reason. Real data would behave differently.
3. **Trade-level granularity is not available.** There is one NCO family code per sector, so the forecasts are sector × district.
4. **Data runs past today.** The CSV extends to 2026-12 (today is 2026-10-18), so the last two months of "actuals" are themselves simulated. The 2027 forecast is therefore a forecast from simulated history.
5. **Shocks can't be forecast.** Windows touching COVID are excluded from training, so the model gives no protection against a new shock; the intervals only reflect normal-regime error.

## Observations on the dataset (not the model)
* `file_reference_and_sources.md` reports check 8 (Pune IT ÷ Gadchiroli IT = 60.48×) as PASS against a 4–8× requirement. The actual 2026 ratio is about 53×. A 4–8× disparity requirement would fail this check.
* The generator clips the employment rate at 0.42 of the labour force. That clip binds on 25% of all rows (64% of Manufacturing, 31% of IT-ITeS). It mutes the COVID shock: April 2020 vs February 2020 aggregate Manufacturing employment is −9%, not the documented −38% (Construction −51%, Textiles −37% and Healthcare +43% are close to spec). This is a flaw in the generator, so check 7 passes only in the unclipped sectors.
* Nandurbar's LGD code `497A` is not a real LGD code.
* `lmis_employment_monthly_2016_2025.csv` in the repo root is a byte-identical copy of the archived dataset (same size and timestamp). It is tracked in git and was not used.
