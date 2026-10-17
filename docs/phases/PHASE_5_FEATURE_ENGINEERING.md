# Phase 5 – Feature Engineering & Selection

Status: **Complete pending your sign-off (Section 9).**
Reproduce: `python src/features/select_features.py` (about 20 minutes), `regime_check.py`, `verify_horizons.py`, `design_flags.py`, `catalog.py`, then `python tests/test_features.py`.
Outputs: `data/processed/features/feature_sets.json` and `feature_catalog.csv`, `reports/features/` (all experiment tables, a pass-1 archive and `time_proxy_audit.csv`).

---

## 1. Goal and exit criteria
Turn the clean panel into model inputs, using the Phase 4 decisions, and pick a feature set per target with evidence. Phase 5 is complete when:
1. Every feature is built from information available at the forecast origin only, and a test proves it. ✔
2. Candidate features are documented in a catalog. ✔ (85 features)
3. Selection used only train and validation data, with a stated protocol and noise level. ✔
4. A final feature set, base and training policy exist for each target, with results against the baselines. ✔
5. The next phase has a ready interface. ✔ (`src/features/pipeline.py`; re-fitting through it reproduces the reported F3 scores exactly)
6. The Phase 4 decisions that fall to this phase are closed: D6 (wages, demographics, seat levels), D7 (relative flags), D8 (shares not counts). ✔ (Sections 6, 10)

## 2. How an example is built
One training example is a **(series, forecast origin t, horizon h)** triple, h = 1…12, direct multi-horizon (one model per target, horizon as a feature).
* **Target:** `log x[t+h] − base[t]`, where the base is chosen per target (Section 5). Predictions are converted back to counts for scoring.
* **Origins:** from 2014-01 (36 months of history needed for the 36-month momentum and seasonal profile).
* **Time rule:** every feature uses data at or before t, using trailing windows and expanding statistics. The seasonal profile at origin t uses only same-month observations up to t, from months whose 13-month window touches no shock.
* **Test lock:** the panel is loaded through `load_panel`; the test period is not reachable.

## 3. Feature families (85 candidates; 77 after excluding time proxies)
| Family | Examples | Why (Phase 4) |
|---|---|---|
| Level deviation | log level minus its 3-, 12-month mean; 3-vs-12 and 6-vs-12 month means | Signal is where a series sits against its smoothed level (F10) |
| Momentum, volatility | log change over 1, 3, 6, 12, 36 months; 12-month std of monthly change | Persistence and noise (F8) |
| Seasonal anchors | same month last year minus now; last year's growth over the same span | Strong seasonality in two sectors (F3) |
| Seasonal profile | expanding month factor at origin, and target-month minus origin-month shift | Strong seasonality (F3); employment's profile is a clean estimate |
| Cross rates | log vacancies/employed, seekers/employed, vacancies/seekers, with 12-month deviation and change | Gap definition (Phase 1) |
| Unemployment | rate and its 3-, 12-month change | Signal for seekers (F10) |
| Sector aggregates | sector-wide log totals: 3- and 12-month change, deviation from 12-month mean | Shared cycles (F2, F4) |
| Size and context | population, size relative to the sector, relative wage | District effects (F6, F7) |
| Training | seats per 1,000 residents relative to sector, certified/vacancies | Supply side |
| Demographics | female share relative to sector, graduate share, youth share | Candidates (D6) |
| Calendar | origin month, target month and its sine/cosine, horizon | Seasonality |
| Identity | sector, tier, state, district (categorical) | Persistent differences (F7) |

Full list with definitions and selection flags: `feature_catalog.csv`.

## 4. Leakage controls
* **Truncation test:** for four origins, the panel is cut at the origin, every feature is rebuilt, and the values must equal those from the full panel. All 85 candidate feature columns pass at horizons 1, 6 and 12. A deliberate look-ahead feature (a centred moving average) fails the same comparison, so the test can catch leaks.
* **Time-proxy audit:** pass 1 of the selection ranked `wage_log` second for vacancies. In this data wage is a smooth rising trend, so it lets a model learn the calendar year rather than economics, and trees cannot extrapolate it into 2025–26. The audit (`time_proxy_audit.csv`) found eight features that move with calendar time (median |Spearman| with time ≥ 0.69 within a series): `log_pop`, `wage_log`, `seats_per_kpop`, `seek_rate`, `coverage`, `female_pct`, `post_covid`, `eshram_progress`. They are excluded; detrended versions (`wage_rel`, `seats_rel`, `female_rel`, the 12-month deviations and changes of the rates, `rel_size_E`) stay. The first pass is kept in `reports/features/pass1_with_time_proxies/`.
* **Flags are not features** (Phase 3 rule): shock-window flags are used only to mask training rows.

## 5. Selection protocol
A fixed LightGBM probe (250 trees; not the final model, which is Phase 6) is trained on three expanding-window folds and scored by WAPE on counts, horizons 1, 3, 6, 12: **F1** train targets ≤ 2017-12, validate 2018; **F2** ≤ 2018-12, validate 2019; **F3** ≤ 2023-12, validate 2024 (the Phase 1 validation fold). Validation rows whose target month lies in a shock window are excluded; 2025–26 never enters.

**Noise level:** re-fitting with three seeds gives a relative standard deviation of 0.77% (rounded in the saved table to 0.76%), so a group counts only if it changes error by at least **1.53%** (2 × noise), in at least two folds.

Steps: A base · B training policy · C group ablation (drop each group from the full set; add each to a core set) · D choice by the rule above, a backward pass removing any group whose removal helps, and pruning of pairs with |r| > 0.97 · E permutation importance on F3 · F final vs full vs core vs baselines · G all 12 horizons · H regime-flag check.

## 6. Results
**A. Base** (mean WAPE %, three folds): employment last value 1.28 (3-month mean 1.30); vacancies last value 6.60 and 3-month mean 6.60 (tie, 3-month mean kept); seekers 6-month mean 5.35 (last value 5.50). Differences between bases are small.

**B. Training policy.** Masking shock windows helps employment (1.28 vs 1.37 unmasked). For vacancies and seekers the difference is within noise (6.57 vs 6.60 and 5.31 vs 5.35, unmasked marginally ahead). For seekers masking would also remove almost all rows after the e-Shram ramp, so rows are not masked. Recency weights (half-lives of 18 and 36 months) help no target, so no weights are used.

**C/D. Final feature sets** (`feature_sets.json`):
| Target | Base | Mask shocks | Features | Groups kept |
|---|---|---|---|---|
| Employment | last value | yes | 36 | own level deviation, momentum, volatility, seasonal anchors and profile; other series' seasonal anchors and profile; sector aggregates; calendar; horizon |
| Vacancies | 3-month mean | no | 29 | own level deviation, momentum, seasonal profile; other series' seasonal anchors and profile; sector aggregates; horizon |
| Seekers | 6-month mean | no | 68 | 16 groups, including cross rates, unemployment, sector aggregates, training and demographics (the backward pass removed identity) |

**Not selected for any target:** the identity features (sector, tier, state, district), wages, size/context and regime features.

**Phase 4 decision D6 (wages, demographics, seat levels):** confirmed for employment and vacancies, where none of them is selected. Not confirmed for seekers, where the `demographics` and `training` groups are kept. The training features help partly because the simulator adds certified trainees to the seeker count, so this is a simulator effect and not evidence about real registrations.

**Phase 4 decision D8 (shares not counts):** no demographic count is a candidate feature. Only shares (female relative to sector, graduate, youth) and ratios are used, so the 16 near-duplicate level pairs found in Phase 4 never enter a model.

**Scaling and missing values:** the features are left unscaled and unimputed. Tree models handle both. A non-tree model in Phase 6 (a linear model, for example) needs its own imputation and scaling step, added there and fitted on training rows only.

**F. Final vs alternatives** (WAPE %, mean of three folds):
| Target | Core set | Full set | **Final set** | Last value | Seasonal naive + drift | Final vs last value |
|---|---|---|---|---|---|---|
| Employment | 1.81 | 1.28 | **1.28** | 3.40 | 1.89 | −62% |
| Vacancies | 6.86 | 6.57 | **6.46** | 7.23 | 9.63 | −11% |
| Seekers | 6.72 | 5.31 | **5.23** | 6.47 | 8.27 | −19% |

The final set matches the full set with 36, 29 and 68 features against 77. On the latest fold (F3) the vacancy final set is 3% worse than the full set (7.12 vs 6.89) while better in F1 and F2.

**G. All 12 horizons** (F3, mean WAPE): employment 1.41 vs last value 4.42; seekers 5.93 vs 7.43; vacancies 8.27 vs 8.74. Employment beats both baselines at every horizon. Seekers beat last value at horizons 1–11 but not at 12 (9.1 vs 8.6). Vacancies beat last value at every horizon, but by only 2–7% beyond 3 months.

**E. What matters most** (permutation importance on F3): the employment seasonal shift (target-month minus origin-month profile) is the top feature for employment (1.79 points) and also a leading feature for vacancies (0.58) and seekers (1.43), so employment's cleaner seasonal profile helps the noisier series. Next: last year's growth and level anchors for employment; the series' own 3-month deviation and sector-wide momentum for vacancies; sector-wide seeker deviation for seekers.

**H. Regime flags** (decision D2 from Phase 4): adding `post_covid` changes F3 error by +0.4% (employment), −2.9% (vacancies, one fold) and +2.3% (seekers); adding `eshram_progress` as well helps seekers slightly and hurts vacancies. No robust gain, and the flags are constant after 2022, so they stay excluded. Vacancies is a candidate to re-test in Phase 6.

## 7. Limits
* Selection and the final comparison use the same three folds; F3 (2024) is also the validation year, so the results are slightly optimistic.
* The probe is one model with fixed settings; a different learner could prefer other features.
* Groups are tested as blocks; interactions between groups are only partly explored.
* The simulator drives some results: sector aggregates and the employment seasonal profile are useful partly because the generator links the series to sector cycles and common seasonality. The vacancy gain over last value is modest (about 11%), which matches the noise floor found in Phase 4.
* Vacancy and seeker training choices (unmasked) rest on differences within noise.

## 8. Early-warning flag design (Phase 4 decision D7)
Phase 4 showed the absolute coverage thresholds collapse into one status per sector. `src/features/flags.py` defines **relative** flags instead: a district's coverage percentile among the districts of its own sector in the same month (3-month vacancies over 3-month seekers, trailing windows only), with classes Tightest decile (≥ 90), Tight (70–90), Typical, Loose (10–30) and Loosest decile (≤ 10). The absolute coverage level is kept as a separate context field (`absolute_context`: openings exceed seekers, moderate, oversupplied, deep surplus), because a relative class says nothing about absolute shortage: the tightest Construction districts are still in deep surplus.

What the data says (`design_flags.py`, 2011–2024, COVID and policy windows excluded):
* The classes hold about 11 / 20 / 39 / 20 / 11% of districts in every sector and year. That is **by construction**, so it shows the flags are not degenerate, not that they are informative.
* **Persistence is high:** the percentile rank correlates 0.90 with the rank 12 months later. Today's percentile identifies the top and bottom decile 12 months ahead with AUC 0.97 (saturation) and 0.96 (shortage). As a persistence benchmark, flagging today's extreme decile gives precision and recall of 0.74 for saturation and 0.73 for shortage; flagging the outer 20% gives precision 0.51 / 0.49 and recall 0.93 / 0.90.
* **The trailing trend is rejected.** Among districts not yet in an extreme decile, a faster-than-sector fall in coverage predicts the *opposite* of an early warning: AUC 0.445 (saturation) and 0.471 (shortage), below 0.5, meaning those districts are more likely to recover. This is the mean reversion found in Phase 4 (F10). So no "approaching" class is built from the past trend.
* **Consequence for Phase 8:** forward-looking flags ("entering the loosest decile within 6 or 12 months") must come from model **forecasts**, and a forecast-based flag has to beat the persistence benchmark above, which is already strong in this simulated data.
* **Seat mismatch** (log of a district's share of the sector's seats over its share of vacancies; |x| > 0.5 flags over- or under-allocation): in 2012, 2016, 2019 and 2024, 12–22% of districts are over-allocated in Construction, Healthcare and Textiles, about 31–35% in Manufacturing and 45–49% in IT-ITeS, while 2–13% are under-allocated. The EDA noted that the simulator spreads half of the seats evenly, so this indicator illustrates the method and should not be read as a real finding.

Outputs: `reports/features/flags_class_shares.csv`, `flags_forward_value.csv`, `flags_persistence_benchmark.csv`, `flags_seat_mismatch.csv`, `flags_summary.json`.

## 9. Test-period exposure (integrity note)
The provisional prototype in `src/modeling/` predates the test lock and scored 2025–2026 once. Its aggregate scores (WAPE ≈ 1.6%, 9.0% and 5.4%) are quoted in Phase 1 (Section 13), Phase 2 (Section 8) and Phase 4 (Section 4). Nothing in Phases 3–5 used them: features, folds, thresholds and settings were chosen on data up to 2024-12 only, and the feature code cannot load the test rows. The 2025–26 period is therefore **not pristine**: one earlier model has been scored on it and the headline numbers were seen. Phase 8 should say so when it reports test results. A stricter option is to delete the quoted numbers from those approved documents and quarantine `outputs/provisional/`; that edits approved text, so it is your decision.

## 10. Hand-off to Phase 6
`src/features/pipeline.py` provides `training_frame(target, train_end)` and `validation_frame(target, origin, months)` with the selected features, base and masks; the test period stays locked. Phase 6 should compare model families on these inputs and report against the Phase 4 baselines (last value, seasonal naive with drift, seasonally adjusted level).

## 11. Decisions and sign-off
| # | Decision | Recommendation |
|---|---|---|
| D1 | One model per target, direct multi-horizon with horizon as a feature | Yes |
| D2 | Predict relative to a base: last value (employment), 3-month mean (vacancies), 6-month mean (seekers) | Yes |
| D3 | Mask shock windows for employment only; no recency weights | Yes |
| D4 | Exclude the eight calendar-time proxies; keep detrended versions | Yes |
| D5 | Use the final sets in `feature_sets.json` (36 / 29 / 68 features); drop identity, wage, size and regime features | Yes |
| D6 | Re-test the `post_covid` flag for vacancies in Phase 6 with the longer training history | Yes |
| D7 | Use the relative percentile flags with an absolute-context field; build "approaching" flags from forecasts in Phase 8, not from the past trend | Yes |
| D8 | Disclose in Phase 8 that 2025–26 was scored once by the provisional prototype; choose whether to remove the quoted numbers (Section 9) | Your decision |

Sign-off checklist:
- [ ] Feature design and leakage controls (Sections 2–4) accepted
- [ ] Selection protocol and results (Sections 5–7) accepted
- [ ] Early-warning flag design and test-period note (Sections 8, 9) accepted
- [ ] Decisions D1–D8 accepted

Phase 6 (Model Selection) starts only after sign-off.
