# Phase 7 – Model Training

Status: **Approved (D1–D5 accepted as written).**
Deliverables: `models/xgboost_v1/` (checkpoints, `model_card.md`, `params.json`, `preprocessor.json`, `intervals.json`, `checkpoint_manifest.json`, `logs/train.log`), `data/splits/` (train, validation, test files and `split_manifest.json`), `reports/training/` (search trials, learning curves, validation metrics, checks).
Reproduce: `python src/splits/make_splits.py`; `python src/training/tune.py E|V|S` (about 30 minutes each, run in parallel), then `... --final-only` and `... --recent`; `python src/training/train.py`; `check_preprocessing.py`; `compare_default.py`; `seed_noise.py`; `make_model_card.py`; tests `tests/test_splits.py` and `tests/test_training.py`.

---

## 1. Goal and exit criteria
Train the Phase 6 primary model, XGBoost, on a time-aware train split, tune it with a time-aware scheme, regularise it, and leave a checkpoint that can be reloaded and run later, with a model card that records every choice. Phase 7 is complete when:
1. Independent train, validation and test files exist, in a 70/5/25 split, balanced across sectors, with no look-ahead. ✔ (Section 2)
2. Preprocessing is fitted on the train split only. ✔ (Section 3)
3. XGBoost (`tree_method='hist'`, all cores) is trained with regularisation, using time-aware validation. ✔ (Sections 4–5)
4. Logs, parameters and trained binaries are saved, and the model reloads and reproduces its predictions in a fresh process. ✔ (Section 6)
5. The test split was not used. ✔ (a test checks the code and the checkpoint manifest)

## 2. Splits (your 70 / 5 / 25 requirement)
| Split | Calendar window | Months | Share | Rows |
|---|---|---|---|---|
| train | 2011-01 to 2022-02 | 134 | 69.8% | 307,440 |
| validation | 2022-03 to 2022-12 | 10 | 5.2% | 15,400 |
| test (locked) | 2023-01 to 2026-12 | 48 | 25.0% | 142,800 |

* **Time-aware.** The series are autocorrelated, so a random split would leak neighbouring months across splits. The split is by calendar time, with identical cut dates for all 280 series. Row rule: a row belongs to a split by its target month; validation (test) rows must also have their forecast origin on or after the last month of the previous window, so the model that forecasts them could have been fitted on every earlier label. The 36,680 rows that straddle a boundary are dropped. Shares of the kept rows are 66.0% / 3.3% / 30.7%, because later months have more usable horizons; the 70/5/25 shares are of calendar months.
* **"Stratified by sector".** Because every series is cut at the same dates, every sector gets exactly 134 / 10 / 48 months and the same number of rows in each file (56 series per sector). Random stratified sampling would break the time order, so the balance is built in rather than sampled.
* **Independent files.** Targets are disjoint and in time order. `tests/test_splits.py` rebuilds the train file from a panel that stops at 2022-02, and the validation file from a panel that stops at 2022-12, and gets identical features and targets: no later data was used. Checksums are in `split_manifest.json`; `load_split("test")` refuses to open the test file without an explicit unlock.
* **This replaces the Phase 3 split** (train to 2023-12, validation 2024, test 2025–26) from Phase 7 on. See Section 8, D1, for the consequences.

## 3. Preprocessing
Median imputation and standardisation, fitted on the train rows only (`preprocess.py` refuses anything not labelled `train`; a test checks that transforming validation rows leaves the fitted statistics unchanged). The train features contain no missing values, so the imputation is a safeguard. Trees are not affected by scaling: refitting without preprocessing moves validation WAPE by +0.02 (employed), 0.00 (vacancies) and 0.00 (seekers) points. The lag and rolling features are those of Phase 5 (trailing windows only, proven leak-safe by the truncation test).

## 4. Training and tuning
* **Model:** three XGBoost models (employed E, vacancies V, seekers S), horizon as a feature, target = log change from the Phase 5 base. Each is the mean of five seeds (seed noise, Section 5).
* **Time-aware validation:** rolling-origin folds inside the train split (cut-offs 2016-12, 2017-12, 2018-12; each scores the following 12 target months), plus the validation split as a fourth, most recent fold.
* **Search:** the Phase 6 default plus 40 random and 18 local configurations per target over learning rate, leaves, `min_child_weight`, L2 and L1 penalties, `gamma`, row and column sampling and bins; the number of trees is picked at checkpoints from 10 to 600.
* **Regularisation:** shrinkage with a cross-validated tree count, leaf-size limits, L2 (and searched L1) penalties, minimum split gain, row and column sampling, seed averaging, shock windows removed from the employed-worker training data.

## 5. Results
**Validation (mean WAPE over horizons 1–10, %)**

| Target | Model | Last value + seasonal shift | Improvement | Phase 6 default, same pipeline |
|---|---|---|---|---|
| Employed workers | 4.19 | 4.98 | 16% | 4.08 |
| Job vacancies | 8.56 | 9.43 | 9% | 8.49 |
| Registered seekers | 9.54 | 21.19 | 55% | 9.54 |

**What the iteration found** (details in the model card, Section 6):
* **Tuning bought very little.** Against the Phase 6 default, the best search result improved cross-validation WAPE by 2.1% (E), 0.3% (V) and 3.2% (S). None of the tuned settings beat the default clearly across eras: on the validation split the default scored 4.08 (E), 8.49 (V) and 9.54 (S) against 4.20, 8.51 and 11.28 for the stage-1 picks. After the validation split was added as a fourth fold, E and V keep a tuned configuration (0.5% and 1.3% ahead of the default, inside the noise) and **seekers keep the Phase 6 default**.
* **One fit is noisy.** Validation WAPE of a single fit moves 1–2% with the seed or the thread count (V: 8.40 to 8.77 across eight seeds). That is larger than the gaps between shortlisted configurations, so shortlisted configurations were scored as five-seed averages and the saved model is a five-seed average.
* **Validation is a harder regime than the training folds.** It is the first ten months after COVID; errors are about three times the in-sample errors for employed workers, for the model and for the baseline alike.
* **The model beats the best baseline on average**, but not at every horizon: employed workers at 1–3 months ahead are better predicted by last value plus seasonal shift.
* **Learning curves** show no late overfitting (validation error at the final tree is at most 1.4% above its minimum).

## 6. Checkpoint
`models/xgboost_v1/` holds 15 XGBoost files (`<E|V|S>_seed<42..46>.ubj`, 12 MB in total), the fitted preprocessor, all parameters, interval widths, the training log, and a manifest with SHA-256 checksums, library versions and split checksums. `src/training/predict.py` loads it (`Forecaster.load`) and forecasts any rows in the split layout; `tests/test_training.py` reloads it in a fresh process and reproduces the saved validation predictions to 1e-9. The test split stays closed (`--unlock-test` is required, Phase 8 only).

## 7. Limits and open items
* **Prediction intervals are too narrow** for the post-COVID window: the 90% intervals cover 61% (E), 83% (V) and 79% (S) of validation outcomes. They come from pre-COVID folds and need recalibration in Phase 8.
* **Seekers beyond about 9 months (D4 from Phase 6) is not resolved.** The whole validation window is inside the e-Shram ramp, so it cannot answer the question; the seasonal-naive-plus-drift baseline scores 10.79 against the model's 9.54. The post-ramp test months decide it in Phase 8.
* **Horizons 11–12 have no validation rows** (the window is 10 months).
* **The HistGradientBoosting challenger was not trained**: you asked for XGBoost. Phase 6's hand-off planned both; the challenger comparison moves to Phase 8.
* **Selection exposure.** Features, bases and the model family were chosen in Phases 5–6 on folds that included 2018, 2019 and 2024. The new test window (2023–2026) contains 2023 and 2024, and 2025–26 was scored once by the quarantined prototype. Phase 8 must report this and, if wanted, also report 2025–26 alone.
* Validation was used in the last tuning stage, so its scores are slightly optimistic.
* The data are synthetic; accuracy says how the method works on this simulator.

## 8. Decisions for you
| # | Decision | Recommendation |
|---|---|---|
| D1 | Adopt the 70/5/25 calendar split as the project split from Phase 7 on, superseding the Phase 3 split. Consequence: the model has not seen 2022-03 onward; for deployment (Phase 9) refit on train + validation (and later data), and the Phase 6 plan to fit on all data to 2024-12 is dropped | Yes, with the exposure noted in Section 7 |
| D2 | Final settings: tuned for E and V, Phase 6 default for S, five-seed average | Yes |
| D3 | Recalibrate prediction intervals in Phase 8 | Yes |
| D4 | Train the HistGradientBoosting challenger in Phase 8 and compare on the test split | Yes |
| D5 | Resolve seekers beyond about 9 months and the IT-ITeS / low-volume reporting in Phase 8 | Yes |

## 9. Sign-off
- [x] Splits and leakage controls (Sections 2–3) accepted
- [x] Training, tuning and results (Sections 4–5) accepted
- [x] Checkpoint and model card (Section 6, `models/xgboost_v1/model_card.md`) accepted
- [x] Limits and decisions D1–D5 (Sections 7–8) accepted

Phase 8 (Evaluation & Tuning) is next and has not started.
