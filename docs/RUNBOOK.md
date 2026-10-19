# Runbook: monthly forecast

Everything runs from the project root. Python 3.13 with `requirements.txt` installed (xgboost 3.4.1, pandas 2.2.3, numpy 2.1.3).

## Each month
1. **Add the new month of data** to `data/raw/` and rebuild `data/processed/panel_monthly.parquet` (`python src/preprocessing/clean_panel.py`). With the synthetic data this step is a regeneration; with real data it is the ingestion job.
2. **Refit** (only when a trigger below fires, otherwise reuse the last deployed models): `python src/deployment/refit.py --origin YYYY-MM`.
3. **Forecast:** `python src/deployment/forecast.py --origin YYYY-MM` (the origin must be the newest month with real data).
4. **Verify:** `python tests/test_deployment.py` (edit `ORIGIN` at the top of the file). It fails if any of the 280 series, 12 horizons or 3 targets is missing, if any value is invalid, if the flags are malformed, or if a second run is not byte-identical.
5. **Publish** the two CSV files in `outputs/forecasts/origin_YYYY-MM/` together with `manifest.json`.
6. **Archive:** keep every origin folder; Phase 10 scores old forecasts against new actuals.

## Retraining triggers (starting values; revisit in Phase 10)
* A new calendar year of data is available (annual refit), or
* the 6-month rolling WAPE of a target at horizons 1–6 is more than 25% above its Phase 8 test value, or
* the 90% interval coverage of a target stays below 80% or above 97% for 3 months in a row, or
* a structural break is known (a registry change like e-Shram, a policy shock).
After retraining, check `reports/deployment/refit_backtest.json`-style evidence before publishing.

## Never do
* Change a hyper-parameter, blend weight or interval setting without a new declaration (`src/evaluation/declare.py`) and a fresh-draw check.
* Build features with data after the origin month (the loader cuts the panel at the origin).
* Use anything under `Archived/`, `data/superseded/` or `*/quarantine/`.

## Rollback
* Code and settings: `git checkout phase8-v3-declared` (or the latest tag), then re-run the steps above.
* Models: previous deployed models are in `models/deployed/origin_<month>/` with SHA-256 manifests; forecasts in `outputs/forecasts/origin_<month>/`.
* File-level backup: `backups/phase8_evaluation_snapshot/` (`sha256sum -c MANIFEST.sha256`).

## Reading the output
* `confidence`: employed high, seekers medium, vacancies low, IT-ITeS low. Always look at `baseline_forecast` for vacancies.
* Flags are relative to the sector in the same month and are low confidence; use `absolute_context` beside them.
* Everything is synthetic data until a real source is connected.
