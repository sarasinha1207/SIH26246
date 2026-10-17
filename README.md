# LMIS – Labour Market Intelligence & Skill Demand-Supply Forecasting

SIH26246 · Ministry of Skill Development and Entrepreneurship (MSDE)

## Project status (ML lifecycle)
Phases are completed strictly in order. A phase is closed only after its sign-off checklist is approved.

| # | Phase | Status | Document |
|---|---|---|---|
| 1 | Problem Definition | **Approved** | [docs/phases/PHASE_1_PROBLEM_DEFINITION.md](docs/phases/PHASE_1_PROBLEM_DEFINITION.md) |
| 2 | Data Collection | **Awaiting sign-off** | [docs/phases/PHASE_2_DATA_COLLECTION.md](docs/phases/PHASE_2_DATA_COLLECTION.md) |
| 3 | Data Cleaning & Preprocessing | Not started | |
| 4 | Exploratory Data Analysis | Not started | |
| 5 | Feature Engineering & Selection | Provisional prototype only | |
| 6 | Model Selection | Provisional prototype only | |
| 7 | Model Training | Provisional prototype only | |
| 8 | Evaluation & Tuning | Provisional prototype only | |
| 9 | Deployment | Not started | |
| 10 | Monitoring & Maintenance | Not started | |

`reports/PROVISIONAL_MODEL_REPORT.md` and everything under `outputs/provisional/` and `models/provisional/` come from a prototype built before Phases 2–4 were closed. They will be regenerated.

## Folder structure
```
LMIS Data/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                 immutable inputs + DATA_MANIFEST.json (checksums)
│   ├── interim/             Phase 3 working data (empty)
│   └── processed/           model-ready data (empty)
├── docs/
│   ├── phases/              one document per lifecycle phase
│   └── reference/           problem statement, data dictionary, source/method notes, NCO hierarchy
├── src/
│   ├── data_generation/     synthetic data generator (produces data/raw)
│   ├── data_collection/     Phase 2 raw-data audit
│   └── modeling/            provisional forecasting prototype
├── models/provisional/      saved prototype models
├── outputs/provisional/     prototype forecasts, metrics, gap rankings
├── reports/                 audit results and reports
└── Archived/                previous dataset – NOT to be used anywhere
```

## Data rules
* The only modelling dataset is `data/raw/lmis_district_monthly_2011_2026.csv` (quarterly file for roll-ups).
* Nothing under `Archived/` may be used. `lmis_employment_monthly_2016_2025.csv` in the repo root is an identical copy of an archived file and is also off limits.
* Raw files are never edited. `python src/data_collection/validate_raw_data.py` verifies them against the checksums in `data/raw/DATA_MANIFEST.json` and runs the acceptance checks.

## Run
```bash
pip install -r requirements.txt
python src/data_collection/validate_raw_data.py      # Phase 2 audit
python src/modeling/lmis_forecast_model.py           # provisional prototype
```
