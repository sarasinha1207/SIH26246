# Phase 9 – Deployment

Status: **Built and tested, awaiting your sign-off (Section 10).** Started while Phase 8 was still awaiting its sign-off, at your request; Phase 9 uses the Phase 8 `xgboost_v3` declaration unchanged.
Deliverables: `src/deployment/` (features, refit, forecast), `models/deployed/origin_2026-10/` (the models used), `outputs/forecasts/origin_2026-10/` (forecast and flag files), `docs/RUNBOOK.md`, `tests/test_deployment.py`, `reports/deployment/`.
Reproduce: `python src/deployment/refit.py --origin 2026-10` (about 6 minutes), `python src/deployment/forecast.py --origin 2026-10` (about 1 minute), `python tests/test_deployment.py`.

---

## 1. Goal and exit criteria
Turn the declared model into a repeatable monthly run that writes a forecast and early-warning file for **every one of the 280 series**, with intervals and honest labels, and a test that fails if anything is missing. Phase 9 is complete when:
1. A single command produces the forecasts and flags for a stated origin. ✔
2. The output covers 280 series × 3 targets × 12 horizons with no gaps, and a test enforces it. ✔ (Section 3)
3. Nothing after the origin month can influence a forecast. ✔ (test)
4. The run is reproducible, and the models and data are fingerprinted. ✔
5. Limits are visible in the files, not only in the documents. ✔ (confidence labels, baseline column)
6. A runbook covers the monthly run, retraining triggers and rollback. ✔ (`docs/RUNBOOK.md`)

## 2. Choices I made (all open to change)
| Choice | What I did | Why |
|---|---|---|
| Forecast origin | **2026-10**, horizons 1–12 (2026-11 to 2027-10) | 2026-10 is the last month not later than today (2026-10-19). The panel's 2026-11 and 2026-12 are simulated months after today; they are cut off before any feature is built |
| Models | Declared `xgboost_v3` settings, **refitted on all history to the origin** (nothing re-tuned) | The newest years are the post-COVID, post-ramp regime. Backtest in Section 4 |
| Delivery | Batch files, one folder per origin | The dashboard reads files and the data changes monthly |
| Intervals | The Phase 8 policy: employed static, vacancies recalibrated, seekers adaptive conformal | Evidence in Phase 8, Section 11 |

## 3. Output and 100% coverage check
`outputs/forecasts/origin_2026-10/`:
* `forecast_long.csv` – **10,080 rows** = 280 series × 3 targets × 12 horizons. Columns: series, district name and LGD code, state, tier, sector, target variable, horizon, origin and target month, `forecast`, `lo90`, `hi90`, `interval_method`, `baseline_forecast` and its name, `last_observed`, `confidence`, `typical_test_error_pct` (the test WAPE of that target and horizon), `low_volume_series`.
* `flags.csv` – **3,360 rows** = 280 series × 12 horizons: forecast coverage ratio (vacancies / seekers), percentile among the 56 districts of the sector in the target month, relative status (Tightest decile, Tight, Typical, Loose, Loosest decile), today's status, change ("entering / leaving" a decile), the absolute context (openings exceed seekers, moderate, oversupplied, deep surplus), and `historical_precision` for flagged rows.
* `manifest.json` – counts, SHA-256 of both files, model and panel fingerprints.

| Check | Result |
|---|---|
| Series | 280 (56 districts, 4 states, 16 tiers, 5 sectors); every series has 12 horizons for each of the 3 targets |
| Missing, non-finite or inverted values | none (`lo90 < forecast < hi90`, all positive) |
| Largest move from the last observation | within ±50% (a test checks it) |
| Flag classes | each sector-horizon has 56 districts; about 10% in each extreme decile |
| Reproducibility | a second run gives byte-identical files |
| Look-ahead | features for the origin are identical whether or not the later simulated months are in the panel |

## 4. Does refitting on newer data help? (`refit.py --backtest 2025-12`)
Refit through 2025-12 with the declared settings and score the 2026 months (origins 2025-12 to 2026-09, horizons up to 10) against the declared v3 models (fitted to 2022-12) and the baseline on the same rows. WAPE %:

| Target | Refit to 2025-12 | v3 (fitted to 2022-12) | Best simple baseline |
|---|---|---|---|
| Employed | 1.55 | 1.58 | 2.37 |
| Vacancies | 7.90 | 7.80 | 7.62 |
| Seekers | 4.78 | 5.00 | 5.39 |

Refitting helps employed workers (2%) and seekers (4.5%) and is neutral for vacancies (1.3% worse, inside the 1–2% noise). **In 2026 neither vacancy model beats the simple baseline**, which matches the 2025–26 finding of Phase 8. This is a pseudo-holdout, not an unbiased test: the blend and interval policy were chosen with 2023–2026 in view.

## 5. Labels and flags
* **Confidence:** employed *high*; seekers *medium*; vacancies *low* (the model barely beats the baseline); any IT-ITeS vacancy or seeker forecast *low*. The baseline forecast sits next to every forecast so a user can see how little the model adds for vacancies.
* **Intervals:** vacancies use the recalibrated static intervals (12-month coverage 90.7–90.8% on the two fresh draws); seekers use adaptive conformal intervals whose error stream is the declared v3 model's out-of-sample forecasts for 2022-12 to 2026-10 (the deployed refit has no out-of-sample history yet); employed use the static intervals.
* **Flags:** the Phase 5 relative classes applied to the forecast single-month ratio (the Phase 5 definition uses 3-month sums; the single-month form is what Phase 8 tested). `historical_precision` is the share of such flags that were right in the Phase 8 test at that horizon (0.67 to 0.81). Phase 8 showed forecast flags beat persistence significantly only for saturation at 12 months, so the flags are labelled *low* confidence.
* **Sanity check against the simulated months after today** (`reports/deployment/synthetic_check_2026-10.json`): the horizon-1 and horizon-2 forecasts for 2026-11 and 2026-12 score WAPE 1.0% and 1.2% (employed), 5.6% and 5.1% (vacancies), 4.3% and 4.3% (seekers), in line with the test results. Those months are synthetic.

## 6. Limits
* The deployed refit has **no unbiased test**; the safeguards are the declared settings, the backtest, the two fresh-draw checks and Phase 10 monitoring.
* Vacancies have little skill over the baseline in the latest years; flags rest on vacancy forecasts.
* The data are synthetic; accuracy says how the method works on this simulator.
* The flag precision figures come from a spent test split and a single data set.
* Seekers' adaptive intervals borrow the v3 model's error history; they will be re-based on the deployed model's own errors once it has a year of out-of-sample forecasts.

## 7. Hand-off to Phase 10 (monitoring)
Each month: add the new actuals, score the previous forecasts (`forecast_long.csv` of earlier origins) against them, track WAPE by target and horizon against the baseline and against the noise-floor ratios of Phase 8, interval coverage and the flag precision, and apply the retraining triggers in `docs/RUNBOOK.md`.

## 8. Decisions for you
| # | Decision | Recommendation |
|---|---|---|
| D1 | Forecast origin 2026-10 (not 2026-12) | Yes |
| D2 | Deploy the refit on all history | Yes (backtest above) |
| D3 | Ship vacancies with the *low* label and the baseline column, and label flags *low* | Yes |
| D4 | Treat the dashboard as the consumer: add the two files to the dashboard data pack in Phase 10 | Yes |

## 9. What I did not do
No live API, no scheduler, no dashboard changes, and no real data connection. The runbook describes the monthly steps; automation is a later choice.

## 10. Sign-off
- [ ] Output files and 100% coverage (Section 3) accepted
- [ ] Refit backtest and choices (Sections 2, 4) accepted
- [ ] Labels, flags and limits (Sections 5, 6) accepted
- [ ] Decisions D1–D4 (Section 8) accepted

Phase 10 (Monitoring & Maintenance) starts only after sign-off.
