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
| 6 | Model Selection | **Complete – awaiting sign-off** | [docs/phases/PHASE_6_MODEL_SELECTION.md](docs/phases/PHASE_6_MODEL_SELECTION.md) |
| 7 | Model Training | Not started | |
| 8 | Evaluation & Tuning | Not started | |
| 9 | Deployment | Not started | |
| 10 | Monitoring & Maintenance | Not started | |

The provisional prototype and everything it produced are **quarantined** (`outputs/quarantine/`, `models/quarantine/`, `reports/quarantine/`): it scored the locked test period before the lock existed. Do not consult or run it; Phases 6–8 replace it.

## Folder structure
```
LMIS Data/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                 immutable inputs: panel CSVs, district catalog, NCO crosswalk, NCO workbook, DATA_MANIFEST.json
│   ├── interim/             scratch space (Phase 6 predictions)
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
│   ├── dashboard/           builds the dashboard data pack
│   └── modeling/            quarantined prototype (do not run)
├── models/                  trained models (quarantine/ holds the prototype's)
├── outputs/                 forecasts and rankings (quarantine/ holds the prototype's)
├── tests/                   automated data tests
├── reports/                 audit results and reports
└── Archived/                previous dataset – NOT to be used anywhere
```

## Data rules
* The only modelling dataset is `data/raw/lmis_district_monthly_2011_2026.csv` (quarterly file for roll-ups). It is **synthetic**; see `docs/reference/DATA_SOURCES_AND_METHODOLOGY.md`.
* Nothing under `Archived/` or `data/superseded/` may be used. The duplicate of the archived dataset that sat in the repo root was removed in Phase 2.
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
python src/dashboard/export_data_pack.py                        # dashboard data pack (see docs/DASHBOARD_BRIEF.md)
python src/dashboard/build_boundaries.py <LGD_Districts.parquet> # district map polygons (source download described in the script)
python tests/test_dashboard_pack.py                             # data pack and map tests
```
