# Phase 6 – Model Selection

Status: **Complete pending your sign-off (Section 9).** Revised after the XGBoost benchmark you requested.
Reproduce: `python src/models/compare_models.py` (about 8 minutes), `python src/models/tune_lightgbm.py lightgbm`, `... hist_gbm` and `... xgboost` (about 15 minutes each), `python src/models/analyze_models.py`, then `python tests/test_models.py`.
Outputs: `reports/models/` (tables `m01`–`m08`, two charts, tuning results), `data/processed/models/model_selection.json`, `data/interim/phase6_predictions.parquet` (every validation prediction).

---

## 1. Goal and exit criteria
Choose the model family to train in Phase 7, using the Phase 5 inputs, with evidence and an honest view of how much better it is than simple alternatives. Phase 6 is complete when:
1. A range of model types was compared fairly on the same data, folds and features. ✔ (12 candidates, including XGBoost)
2. Differences were tested for statistical reliability, not only read off a table. ✔ (paired bootstrap over series)
3. Accuracy, stability, speed and practical fit were all weighed. ✔ (Sections 4–5)
4. A primary model and a challenger are named, with hyper-parameter ranges for later tuning. ✔
5. Nothing outside train and validation data was used. ✔ (a test checks every prediction)

## 2. Candidates
| Model | Type | Why it is here |
|---|---|---|
| Last value; seasonal naive + drift | Baselines | The Phase 4 reference points |
| Last value + seasonal shift; 3-month mean + seasonal shift | Baselines | A fair stronger baseline: today's level adjusted for the expected month-to-month seasonal change, taken from the Phase 5 seasonal profile |
| Holt-Winters (damped trend, additive seasonality, log scale) | Statistical | The classical per-series forecaster; parameters shared within each sector, fitted on training months only, shocks skipped |
| LightGBM; LightGBM per horizon | Gradient-boosted trees | The Phase 5 probe model; one model across horizons vs one per horizon |
| HistGradientBoosting (scikit-learn) | Gradient-boosted trees | A second boosted-tree implementation |
| **XGBoost** | Gradient-boosted trees | **Added at the project owner's request** and run through the identical protocol; settings mirror the two models above (leaf-wise trees, 31 leaves, learning rate 0.08, at least 100 samples per leaf, 80% row and column sampling, L2 penalty 5) |
| Random forest | Bagged trees | A different tree ensemble |
| Ridge regression | Linear | Tests whether the features make the problem nearly linear |
| Neural network (64-32) | Neural | A small MLP |

All learned models receive the same Phase 5 features, base and training policy per target. Missing values are imputed with training medians and features standardised for ridge and the network only.

## 3. Protocol
Same folds as Phase 5: **F1** train targets ≤ 2017-12 and validate 2018; **F2** ≤ 2018-12 and 2019; **F3** ≤ 2023-12 and 2024. Horizons 1, 3, 6, 12. Score: WAPE on counts. Differences use a paired bootstrap over the 280 series (500 resamples; the 95% interval must exclude zero). The 2025–26 test period is never loaded.

## 4. Results
**Mean WAPE % over the three folds** (`m02`):
| Model | Employment | Vacancies | Seekers | Mean of 3 |
|---|---|---|---|---|
| HistGradientBoosting | 1.29 | 6.34 | 5.20 | **4.28** |
| XGBoost | 1.28 | 6.36 | 5.20 | **4.28** |
| LightGBM | 1.28 | 6.46 | 5.23 | 4.32 |
| LightGBM per horizon | 1.32 | 6.51 | 5.17 | 4.33 |
| Random forest | 1.29 | 6.31 | 5.47 | 4.36 |
| Ridge | 1.30 | 6.58 | 5.85 | 4.58 |
| Neural network | 1.44 | 6.66 | 6.42 | 4.84 |
| Last value + seasonal shift (best baseline) | 1.72 | 7.00 | 5.82 | 4.85 |
| 3-month mean + seasonal shift | 2.26 | 7.12 | 5.87 | 5.08 |
| Holt-Winters | 1.46 | 6.96 | 7.83 | 5.42 |
| Last value | 3.40 | 7.23 | 6.48 | 5.70 |
| Seasonal naive + drift | 1.89 | 9.63 | 8.27 | 6.60 |

* **The boosted and bagged trees cluster at the top** (4.28–4.36). All beat the best baseline: pooled over targets by 0.59 WAPE points for XGBoost and for HistGradientBoosting (95% intervals 0.51–0.66 for HistGradientBoosting and 0.51–0.67 for XGBoost). Per target against the best baseline, XGBoost improves employment by 0.47 points (about a quarter), vacancies by 0.62 (9%) and seekers by 0.68 (12%); every interval excludes zero.
* **Ridge is competitive for employment** (1.30) because the seasonal-shift features carry most of the signal, but falls behind for seekers (5.85) and vacancies (6.58). The network is worse than the trees everywhere.
* **Holt-Winters** beats the plain baselines for employment but fails for seekers (7.83; 10.9 in the 2024 fold) because it cannot follow the e-Shram registry break.
* **Blends add nothing:** averaging LightGBM, HistGradientBoosting and XGBoost gives 4.26, 0.02 points better than XGBoost alone, which is within noise; blending with Holt-Winters is worse (4.57) (`m07`).
* **Speed** (`m08`): average fit time 1.3 s for LightGBM, 3.8 s for HistGradientBoosting, 3.8 s for XGBoost, 21.0 s for the random forest, 16.1 s for the network, 0.4 s for ridge.

### 4.1 The XGBoost benchmark (requested before sign-off)
Same three folds, same features and policy, same bootstrap; horizons 1, 3, 6 and 12.

* **XGBoost vs HistGradientBoosting: a statistical tie.** Pooled difference −0.002 WAPE points (95% interval −0.022 to 0.018). XGBoost is ahead in 4 of the 9 target-and-fold cells and level or behind in the other 5, and no cell differs by more than 0.08 points (the largest is vacancies in 2024: 6.82 vs 6.74).
* **XGBoost vs LightGBM: XGBoost is better by 0.059 points pooled (interval 0.034–0.089, about 1.3% relative), the same margin HistGradientBoosting has over LightGBM (0.056, interval 0.024–0.094).** By target: vacancies 0.120 points (0.049–0.201), seekers 0.058 (0.020–0.098), employment no difference (0.003, interval −0.004 to 0.010). As with HistGradientBoosting, the gap comes mostly from 2024 vacancies and IT-ITeS (XGBoost 7.70, HistGradientBoosting 7.54, LightGBM 8.46).
* **By horizon** (mean WAPE %, three folds):

| Target | Horizon | HistGradientBoosting | XGBoost | LightGBM |
|---|---|---|---|---|
| Employment | 1 / 3 / 6 / 12 | 1.04 / 1.32 / 1.58 / 1.66 | 1.03 / 1.32 / 1.57 / 1.69 | 1.02 / 1.31 / 1.57 / 1.74 |
| Vacancies | 1 / 3 / 6 / 12 | 5.08 / 6.50 / 8.09 / 8.75 | 5.11 / 6.49 / 8.16 / 8.80 | 5.20 / 6.68 / 8.25 / 8.71 |
| Seekers | 1 / 3 / 6 / 12 | 4.13 / 4.88 / 5.96 / 9.63 | 4.13 / 4.88 / 5.87 / 9.59 | 4.16 / 4.85 / 6.04 / 10.05 |

  XGBoost and HistGradientBoosting are within 0.09 points of each other at every horizon. LightGBM trails them by 0.1–0.5 points at several vacancy and seeker horizons (largest for seekers at twelve months: 10.05 vs about 9.6).
* **Equity** (six-month horizon, XGBoost): the worst economic tier errs 1.18–1.30× the overall error; counting only tiers with at least four districts, 1.01–1.09×, inside the Phase 1 limit of 1.5×.
* **The same weak spots remain:** for seekers twelve months ahead XGBoost (9.59) is worse than the baseline (8.36), and IT-ITeS vacancies are the hardest case.
* **Tuning evens the three boosted models out.** With the same budget (24 random configurations plus the default, all three folds), mean WAPE goes from 4.281 to 4.263 for XGBoost, 4.278 to 4.248 for HistGradientBoosting and 4.323 to 4.273 for LightGBM. After tuning the three are within 0.025 points (0.6%), below the 0.77% run-to-run noise measured in Phase 5. The 1.3% gap to LightGBM at default settings is therefore mostly a tuning effect, not a lasting accuracy difference. These tuned scores are the best of 25 tries on the same folds, so they are slightly optimistic.

## 5. Decision
**Primary: XGBoost. Challenger: HistGradientBoosting.** The rule: the leader is the learned model with the lowest mean WAPE over the three targets and folds; another model is tied with it only if its pooled bootstrap interval against the leader includes zero; among tied models the project owner's preference decides. (The pooled table existed when the rule was written, so it is a judgement, not a pre-registered test.)

HistGradientBoosting has the lowest mean (4.278 against 4.281) and XGBoost is tied with it, so the owner's preference for XGBoost decides, and the evidence says the choice is safe: XGBoost is no worse than any other model, handles missing values natively, supports a quantile loss for the prediction intervals needed in Phase 7, and fits in under 10 seconds. HistGradientBoosting is kept as the challenger because it is equally accurate and needs no extra package. LightGBM is no longer carried forward: at default settings it is about 1.3% behind both; tuning closes most of that, but it offers no accuracy advantage, only speed.

| Rejected | Reason |
|---|---|
| LightGBM | Behind XGBoost and HistGradientBoosting at default settings (0.06 points, interval excludes zero); no remaining advantage once tuning narrows the gap |
| Random forest | 0.064 points behind HistGradientBoosting (interval 0.029–0.097), about five times slower, weaker for seekers |
| Per-horizon LightGBM | No gain over one model across horizons, three times the models to maintain |
| Ridge | Clearly worse for seekers and vacancies; kept as a sanity check only |
| Neural network | Worst learned model; no accuracy case |
| Holt-Winters | Fails for seekers; the seasonal-shift baseline is as good for vacancies |
| Blends | No measurable gain over the best single model |

## 6. Limits
* Selection and testing use the same three folds, so margins are slightly optimistic; Phase 8 re-tunes with nested validation.
* XGBoost and HistGradientBoosting are tied, not ordered. The final choice between them is open until Phase 8, and either result would be acceptable.
* The gain over the best baseline is modest for vacancies and seekers (9–12%) and nearly absent for IT-ITeS vacancies and for seekers at twelve months.
* The simulator drives parts of the result: persistent district effects and sector-wide cycles are why simple shift baselines already do well.
* Data from 2025–26 has not been seen by any model here. The earlier prototype exposure is described in Phase 5, Section 9.

## 7. Hand-off to Phase 7
Train XGBoost (primary) and HistGradientBoosting (challenger) for each target with the Phase 5 feature sets, base and policy, on all 12 horizons and on all data up to 2024-12 for the final fit, using the default settings (tuning is Phase 8; the search ranges are in `model_selection.json`). Add 90% prediction intervals (XGBoost quantile loss or residual quantiles by horizon). Decide how to treat seekers beyond about nine months, where the seasonal-shift baseline is better, for example by blending the two or by capping the horizon. Keep the Phase 4 and Phase 6 baselines in every later comparison. Pin `xgboost==3.4.1` (already installed and listed in `requirements.txt`).

## 8. Decisions
| # | Decision | Recommendation |
|---|---|---|
| D1 | Primary model XGBoost, challenger HistGradientBoosting, both trained in Phase 7; LightGBM dropped | Yes |
| D2 | Keep "last value + seasonal shift" as the reference baseline for all later phases | Yes |
| D3 | Use default settings in Phase 7; tune once, with nested validation, in Phase 8 | Yes |
| D4 | Treat seekers beyond about nine months as a special case to resolve in Phase 7 | Yes |
| D5 | Report IT-ITeS vacancies and low-volume series separately in Phase 8 (carried from Phase 4) | Yes |

## 9. Sign-off
- [ ] Candidates, protocol and results (Sections 2–4, including the XGBoost benchmark) accepted
- [ ] Decision and limits (Sections 5–6) accepted
- [ ] Decisions D1–D5 accepted

Phase 7 (Model Training) starts only after sign-off.
