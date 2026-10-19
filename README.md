# LMIS – Labour Market Intelligence & Skill Demand-Supply Forecasting

SIH26246 · Ministry of Skill Development and Entrepreneurship (MSDE)

## Project status (ML lifecycle)
Phases are completed strictly in order. A phase is closed only after its sign-off checklist is approved.

| # | Phase | Status | Document |
|---|---|---|---|
| 1 | Problem Definition | **Approved** | [docs/phases/PHASE_1_PROBLEM_DEFINITION.md](docs/phases/PHASE_1_PROBLEM_DEFINITION.md) |
| 2 | Data Collection | **Approved** | [docs/phases/PHASE_2_DATA_COLLECTION.md](docs/phases/PHASE_2_DATA_COLLECTION.md) |
| 3 | Data Cleaning & Preprocessing | **Approved** | [docs/phases/PHASE_3_DATA_CLEANING.md](docs/phases/PHASE_3_DATA_CLEANING.md) |
| 4 | Exploratory Data Analysis | **Approved** | [docs/phases/PHASE_4_EDA.md](docs/phases/PHASE_4_EDA.md) |
| 5 | Feature Engineering & Selection | **Approved** | [docs/phases/PHASE_5_FEATURE_ENGINEERING.md](docs/phases/PHASE_5_FEATURE_ENGINEERING.md) |
| 6 | Model Selection | **Approved** | [docs/phases/PHASE_6_MODEL_SELECTION.md](docs/phases/PHASE_6_MODEL_SELECTION.md) |
| 7 | Model Training | **Approved** | [docs/phases/PHASE_7_MODEL_TRAINING.md](docs/phases/PHASE_7_MODEL_TRAINING.md) |
| 8 | Evaluation & Tuning | **Complete – awaiting sign-off** | [docs/phases/PHASE_8_EVALUATION_AND_TUNING.md](docs/phases/PHASE_8_EVALUATION_AND_TUNING.md) |
| 9 | Deployment | **Built – awaiting sign-off** | [docs/phases/PHASE_9_DEPLOYMENT.md](docs/phases/PHASE_9_DEPLOYMENT.md), [docs/RUNBOOK.md](docs/RUNBOOK.md) |
| 10 | Monitoring & Maintenance | Not started | |

The provisional prototype and everything it produced are **quarantined** (`outputs/quarantine/`, `models/quarantine/`, `reports/quarantine/`): it scored the locked test period before the lock existed. Do not consult or run it; Phases 6–8 replace it.

## Folder structure
```
LMIS Data/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                 immutable inputs: panel CSVs, district catalog, NCO crosswalk, NCO workbook, DATA_MANIFEST.json
│   ├── interim/             scratch space (Phase 6 predictions; not in git)
│   ├── splits/              Phase 7 train / validation / test example files (parquet, not in git) + split_manifest.json (checksums)
│   ├── fresh_draws/         Phase 8 fresh synthetic evaluation draws (not in git; make_fresh_draw.py <seed>)
│   ├── dashboard/           dashboard data pack (2011-2024, no test period)
│   ├── processed/           Phase 3 base tables (parquet), dimension tables, SCHEMA.json
│   └── superseded/          v1 synthetic panel – audit trail only, do not use
├── docs/
│   ├── phases/              one document per lifecycle phase
│   ├── reference/           problem statement, data dictionary, data sources & method, NCO hierarchy
│   └── DASHBOARD_BRIEF.md   everything an AI or developer needs to build the dashboard
├── src/
│   ├── data_generation/     synthetic data generator v2 (+ legacy/ v1 for the audit trail)
│   ├── data_collection/     Phase 2 raw-data audit
│   ├── preprocessing/       Phase 3 cleaning pipeline
│   ├── common/              guarded data access (test period locked until Phase 8)
│   ├── eda/                 Phase 4 exploratory analysis (train + validation only)
│   ├── features/            Phase 5 feature engineering, selection and the training-data interface
│   ├── models/              Phase 6 model comparison and tuning
│   ├── splits/              Phase 7 builds the 70/5/25 split files
│   ├── training/            Phase 7 preprocessing, tuning, final training, prediction, model card
│   ├── evaluation/          Phase 8 Optuna tuning, freezing, one-shot test evaluation, diagnostics
│   ├── deployment/          Phase 9 latest-origin features, refit on all history, forecast + flag files
│   ├── dashboard/           builds the dashboard data pack
│   └── modeling/            quarantined prototype (do not run)
├── models/                  trained models: xgboost_v1/ (Phase 7), xgboost_v2/ (Phase 8 frozen), xgboost_v3/ (declared config), deployed/origin_<month>/ (Phase 9 refit); quarantine/ holds the prototype's
├── outputs/                 forecasts/origin_<month>/ (Phase 9 forecast and flag files); quarantine/ holds the prototype's
├── tests/                   automated data tests
├── reports/                 audit results and reports
├── backups/                 file-level snapshots (not in git; the git tags are the rollback points)
└── Archived/                previous dataset – NOT to be used anywhere
```

## Data rules
* The only modelling dataset is `data/raw/lmis_district_monthly_2011_2026.csv` (quarterly file for roll-ups). It is **synthetic**; see `docs/reference/DATA_SOURCES_AND_METHODOLOGY.md`.
* Nothing under `Archived/` or `data/superseded/` may be used. The duplicate of the archived dataset that sat in the repo root was removed in Phase 2.
* **The test split has been evaluated once (Phase 8) and is spent**; see `reports/evaluation/test_access_log.json`.
* From Phase 7 the project split is 70/5/25 of the calendar months (train 2011-01 to 2022-02, validation 2022-03 to 2022-12, test 2023-01 to 2026-12), defined in `src/common/splits.py`; the test file is locked behind `load_split` until Phase 8. This replaces the Phase 3 `Split_Role` split (test 2025–2026), which `load_panel` still enforces for the older phases.
* The test period (2025–2026) is locked behind `load_panel`. It is not pristine: the provisional prototype scored it once before the lock existed; see `docs/phases/PHASE_5_FEATURE_ENGINEERING.md`, Section 9 (its scores were removed from decision documents and the prototype quarantined).
* Raw files are never edited. `python src/data_collection/validate_raw_data.py` verifies them against the checksums in `data/raw/DATA_MANIFEST.json` and runs the acceptance checks.

## Run
```bash
pip install -r requirements.txt
python src/data_generation/generate_lmis_master_dataset.py      # regenerate data/raw (deterministic)
python src/data_collection/validate_raw_data.py                 # Phase 2 audit
python src/preprocessing/clean_panel.py                         # Phase 3 cleaning (deterministic)
python tests/test_processed_panel.py                            # Phase 3 acceptance tests
python src/eda/run_eda.py                                       # Phase 4 EDA (figures + tables in reports/eda)
python tests/test_eda_outputs.py                                # Phase 4 tests
python src/features/select_features.py                          # Phase 5 selection (~20 min)
python src/features/design_flags.py                             # Phase 5 relative early-warning flags
python tests/test_features.py                                   # Phase 5 tests (leak-safety etc.)
python src/models/compare_models.py                             # Phase 6 model comparison (~7 min)
python src/models/analyze_models.py                             # Phase 6 tables, charts, selection file
python tests/test_models.py                                     # Phase 6 tests
python src/splits/make_splits.py                                # Phase 7 train/validation/test files (~1 min)
python tests/test_splits.py                                     # Phase 7 split tests
python src/training/tune.py E                                   # Phase 7 tuning, per target E|V|S (~30 min); then --final-only and --recent
python src/training/train.py                                    # Phase 7 final models -> models/xgboost_v1 (~6 min)
python src/training/make_model_card.py                          # regenerates models/xgboost_v1/model_card.md
python tests/test_training.py                                   # Phase 7 tests
python src/training/predict.py --split validation --out f.parquet   # run the saved model
python src/evaluation/tune_optuna.py E                          # Phase 8 Optuna search per target (~70 min); then finalize.py, recalibrate.py, build_models.py (freeze)
python src/evaluation/evaluate.py                               # Phase 8 ONE-SHOT test evaluation (refuses a second run), then diagnostics.py, make_report.py
python tests/test_evaluation.py                                 # Phase 8 tests
python src/evaluation/noise_floor.py                            # Phase 8 addendum: noise floor, flag_significance.py, declare.py (xgboost_v3), make_fresh_draw.py <seed>, evaluate_v3.py original|fresh <seed>
python tests/test_phase8_addendum.py                            # Phase 8 addendum tests
python src/deployment/refit.py --origin 2026-10                 # Phase 9: refit the declared v3 settings on all history (~6 min)
python src/deployment/forecast.py --origin 2026-10              # Phase 9: forecast + flag files for all 280 series (~1 min)
python tests/test_deployment.py                                 # Phase 9 tests (coverage, validity, reproducibility, no look-ahead)
python src/dashboard/export_data_pack.py                        # dashboard data pack (see docs/DASHBOARD_BRIEF.md)
python src/dashboard/build_boundaries.py <LGD_Districts.parquet> # district map polygons (source download described in the script)
python tests/test_dashboard_pack.py                             # data pack and map tests
```
