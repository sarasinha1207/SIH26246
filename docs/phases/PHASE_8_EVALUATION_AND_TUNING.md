# Phase 8 – Evaluation & Tuning

Status: **Complete pending your sign-off (Section 10).** The test split was evaluated once; it is now spent.
Deliverables: `models/xgboost_v2/` (frozen models, `frozen_config.json`, `model_card.md`), `reports/evaluation/` (Optuna trials, re-ranking, test tables in `test/`, figures in `figures/`, `test_access_log.json`), `src/evaluation/`, `tests/test_evaluation.py`.
Reproduce: `tune_optuna.py E|V|S` → `finalize.py E|V|S` → `recalibrate.py E|V|S` → `build_models.py` (freezes) → `it_experiment.py V` → `evaluate.py` (once) → `diagnostics.py` → `make_report.py`.

---

## 1. Short answer
**The final model is not at "peak accuracy" and I cannot show that it is.** What the evidence supports:
* **Employed workers: good.** 1.75% WAPE on the test split, inside the Phase 1 limit (2%), 29% better than the best simple baseline, and tuning improved on Phase 7 by 2.5% (interval excludes zero).
* **Vacancies: close to a floor.** 9.16%, only 3% better than the best simple baseline; the Phase 7 settings could not be improved (no Optuna trial beat them by the 1% required). In 2025–26 alone the model (8.92%) is no better than last value plus seasonal shift (8.82%).
* **Seekers: the declared model failed; one pre-declared variant works.** The tuned model scores 7.36%, **worse than the simple baseline (6.69%) and worse than Phase 7 (7.12%)**. The same model with the horizon blend chosen on the training folds scores **5.69%**, better than the baseline by 1.0 point (interval 0.81 to 1.17). I had switched that blend off after it looked bad on the validation split; the test split showed that was the wrong call (Section 6).

## 2. Protocol (fixed before the test split was opened)
1. **Tuning on train + validation only.** Optuna (TPE) searched learning rate, leaves, `min_child_weight`, L2, L1, `gamma`, row and column sampling, bins, loss (squared error, pseudo-Huber, absolute error) and recency weighting: 104 trials for employed, 72 for vacancies, 45 for seekers (time-limited; the Phase 7 settings and the Phase 6 default were trials 0 and 1). Objective: mean over four folds (rolling origins 2016-12, 2017-12, 2018-12 and the validation split) of fold WAPE relative to the Phase 7 settings.
2. **Acceptance rule:** the five best trials, the Phase 7 settings and the Phase 6 default were re-scored with three seeds; the Phase 7 settings were replaced only by a candidate at least 1% better (noise is about 1%). Employed and seekers were replaced; vacancies were not.
3. **Seekers beyond about 9 months (D4):** a per-horizon blend with last value + seasonal shift, weights chosen on the three rolling-origin folds (used only where it gains 1%); a validation veto (drop the blend if validation gets more than 5% worse) was added after seeing validation numbers.
4. **IT-ITeS vacancies:** a sector-only model was tested on the same folds with a rule fixed beforehand (adopt only if at least 3% better on the folds and on validation). It was 1.9% better in one fold and 2–6% worse in the others and on validation, so it was **not adopted**.
5. **Interval recalibration** from the folds, scaled by the validation-to-fold error ratio (D3 of Phase 7).
6. **Freeze:** models were refitted on train + validation (the model Phase 9 would deploy) and every file was checksummed in `frozen_config.json` (test split not opened). Declared comparisons: the same configuration fitted on train only, the Phase 7 settings refitted, HistGradientBoosting (challenger, D4 of Phase 7) and three baselines.
7. **One test run** (`test_access_log.json` records one run). Nothing was changed afterwards; the post-test files only summarise.

## 3. Test results (2023-01 to 2026-12, horizons 1–12; WAPE %, equal weight per horizon)
| Target | Phase 8 model (declared) | + fold-chosen blend | Phase 7 settings | HistGradientBoosting | Best simple baseline |
|---|---|---|---|---|---|
| Employed workers | 1.75 | 1.75 | 1.79 | 1.84 | 2.46 (seasonal naive + drift) |
| Job vacancies | 9.16 | 9.16 | 9.16 | 9.19 | 9.44 (last value + seasonal shift) |
| Registered seekers | 7.36 | 5.69 | 7.12 | 7.32 | 6.69 (last value + seasonal shift) |

Paired bootstrap over the 280 series (500 resamples), difference in WAPE points (negative = first is better):
* Employed, model minus seasonal naive + drift: −0.71 (−0.80 to −0.64). Model minus Phase 7 settings: −0.05 (−0.05 to −0.03). Model minus HistGradientBoosting: −0.09 (−0.10 to −0.08).
* Vacancies, model minus last value + seasonal shift: −0.29 (−0.59 to −0.04). Model minus HistGradientBoosting: −0.03 (−0.10 to +0.06), a tie.
* Seekers, declared model minus baseline: +0.67 (+0.23 to +1.06). Fold-chosen blend minus baseline: −0.99 (−1.17 to −0.81); minus declared model: −1.66 (−1.94 to −1.37); minus Phase 7 settings: −1.43 (−1.67 to −1.21).

**What tuning and refitting were worth on the test split:** employed +2.5% (real, small); vacancies 0; seekers negative for the declared model (the tuned configuration, with pseudo-Huber loss and a 24-month recency weight, over-forecasts at long horizons after the registry ramp, and its search saw a ramp-contaminated validation fold). Refitting on train + validation changed nothing for employed (the validation rows are all removed by the COVID-window rule) or vacancies, and helped seekers by 0.38 points.

**By horizon** (declared model; `by_horizon.csv`): employed 1.07% at 1 month rising to 2.07% at 12; vacancies 5.4% to 12.0%; seekers 4.2% to 11.0% (blend: 4.0% to 6.4%).
**By year of target:** 2023 is the worst year for every target (employed 2.47%, seekers 13.6%), the transition out of COVID and the e-Shram ramp. **2025–26 only** (the months least exposed to earlier selection): employed 1.55% vs 2.30% baseline; vacancies 8.92% vs 8.82% baseline; seekers 5.88% declared, 5.23% with the blend, vs 5.85% baseline.
**Months after today** (2026-11 and 2026-12, synthetic): excluding them changes no score by more than 0.07 points.

## 4. Phase 1 acceptance scorecard (declared model)
| Check | Employed | Vacancies | Seekers |
|---|---|---|---|
| WAPE limit (2% / 7% / 6%) | **1.75 – met** | 9.16 – not met | 7.36 – not met (5.69 with the blend: met) |
| At least 20% better than the Phase 1 baseline | 29% – met | 7% – not met | 7% – not met (blend: 28% – met) |
| Horizon 12 error at most 1.5× horizon 1 | 1.92 – not met | 2.25 – not met | 2.64 – not met (blend 1.60) |
| Worst tier at most 1.5× overall (horizon 6) | 1.06 – met | 1.17 – met | 1.12 – met |

The Phase 1 baseline here is the better of seasonal naive + drift and last value. The vacancy and horizon-ratio limits were set from the v1 simulator's noise floor and were flagged for revision in Phase 1; the evidence supports revising them (D2), but this is a judgement for you.

## 5. Diagnostics (`reports/evaluation/figures/`)
* **d01** WAPE by horizon, all models. **d02** residual histograms and spread by horizon. **d03** predicted vs actual. **d05** WAPE by sector and year. **d08** bias by horizon.
* **Feature importance (SHAP, `d04`, `shap_importance.csv`):** employed – the seasonal shift (24%), sector 12-month momentum (16%), year-ago anchor (11%), horizon (10%). Vacancies – employed seasonal shift (15%), sector seeker and employment momentum (13%, 11%). Seekers – sector seeker deviation (16%), horizon (12%), unemployment rate (7%). Sector-level quantities matter more than own-series history.
* **Bias:** the declared seekers model over-forecasts, increasingly with the horizon (mean log error −0.011 at 1 month, −0.082 at 12 months); the blend cuts the 12-month bias to −0.012 (d07, d08). Employed and vacancy bias is within 0.004.
* **Intervals (`d06`):** observed 90% coverage is 93% (employed), 88% (vacancies), 96% (seekers), against 85%, 83% and 91% with the Phase 7 intervals. Seekers' intervals are wide (mean width 45%); vacancies fall to 85% coverage at 12 months.
* **Equity:** the worst tier at horizon 6 is at most 1.17× the overall error (1.15× counting tiers with at least four districts).

## 6. Weak spots
| Slice | Result | Verdict |
|---|---|---|
| Seekers, 12 months ahead | declared 11.03%, Phase 7 10.21%, baseline 8.35%, **blend 6.44%** | fixed by the blend, which the validation veto had removed |
| IT-ITeS vacancies | 13.42% (others 7.5–8.8%); baseline 15.04%; HistGradientBoosting 13.06% | **not improved**: the model beats the baseline by 11%, a sector-only model did not help |
| IT-ITeS seekers | declared 8.30%, blend 6.41%, baseline 6.72% | blend helps |
| Vacancies, 2025–26 | 8.92% vs baseline 8.82% | no gain over the simple baseline |
| Low-volume series (7% of rows) | 1.78% / 8.47% / 6.59% (employed / vacancies / seekers), not worse than the rest | no problem |
| States | Tamil Nadu vacancies 10.6% (16% above the overall 9.2%); every other state and target within 8% of its overall error | minor |

**Why I think the vacancy and IT-ITeS floors are real:** the generator injects 5–6% noise into vacancies and the IT-ITeS sector has the largest district disparity; the best model and every baseline sit within a few percent of each other at all horizons. Phase 1 noted a perfect-level floor of about 3.9% for vacancies.

## 7. Integrity notes
* **Selection of the blend after seeing the test split.** `primary` (no seekers blend) was declared before the test; `cv_blend` was also declared as a comparison. Recommending `cv_blend` for seekers is a choice made after seeing the test, so its 5.69% carries a small selection bias (one of two variants). The evidence for it does not come from the test alone: the training folds chose it before any test result, and the Phase 6 finding D4 pointed the same way.
* **Selection exposure:** features, bases and model family were chosen in Phases 5–6 with folds that included 2024; the test window contains 2023 and 2024. 2025–26 was scored once by the quarantined prototype. Section 3 gives the 2025–26-only scores.
* **Validation scores are optimistic** because validation was a tuning fold; only the test scores are unbiased (apart from the blend choice above).
* The test split is now spent. Further tuning needs new data; Phase 10 monitoring is the next honest test.
* The git state at the freeze was the Phase 7 commit plus uncommitted Phase 8 code.

## 8. Decisions for you
| # | Decision | Recommendation |
|---|---|---|
| D1 | Use the fold-chosen blend (`cv_blend`) for seekers in deployment, with the selection-bias caveat | Yes |
| D2 | Revise Phase 1 limits to what the data supports: vacancies about 9–10% and ≥3% better than the best simple baseline; seekers 6% (blend); horizon-12/horizon-1 ratio about 2.6 | Yes, but your call |
| D3 | Show vacancy and IT-ITeS forecasts as low-confidence on the dashboard (intervals, separate reporting) | Yes |
| D4 | Deploy refitted models (`primary`, refitted on train + validation) with the seekers blend; retrain when the monitoring in Phase 10 shows drift | Yes |
| D5 | Stop tuning on this data; do not re-run the test evaluation | Yes |

## 9. Limits
Synthetic data; the test window mixes the post-COVID transition (2023) with steadier years; horizons are scored with equal weight; tuning was time-limited (seekers' best trials hit the 600-tree ceiling); one seed per Optuna trial, so trial scores carry about 1% noise.

## 10. Sign-off
- [ ] Protocol and tuning (Sections 2, 9) accepted
- [ ] Test results, scorecard and diagnostics (Sections 3–5) accepted
- [ ] Weak spots and integrity notes (Sections 6–7) accepted
- [ ] Decisions D1–D5 (Section 8) accepted

Phase 9 (Deployment) starts only after sign-off.
