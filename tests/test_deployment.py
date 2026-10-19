"""Phase 9 tests: the forecast file covers every series, horizon and target; values are valid; flags are well formed; the run is reproducible; no look-ahead; models match their manifest.
Runs under pytest or standalone: python tests/test_deployment.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for sub in ("common", "deployment", "features", "splits"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import splits as sp  # noqa: E402

ORIGIN = "2026-10"
OUT = ROOT / "outputs" / "forecasts" / f"origin_{ORIGIN}"
MODELS = ROOT / "models" / "deployed" / f"origin_{ORIGIN}"
L = pd.read_csv(OUT / "forecast_long.csv", dtype={"district_lgd_code": str})
W = pd.read_csv(OUT / "flags.csv", dtype={"district_lgd_code": str})
DIM = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str})
VARS = ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"]


def test_every_series_target_and_horizon_is_forecast_exactly_once():
    assert len(L) == 280 * 3 * 12 == 10080 and len(W) == 280 * 12
    assert not L.duplicated(["Series_ID", "target_variable", "horizon"]).any() and not W.duplicated(["Series_ID", "horizon"]).any()
    assert set(L.Series_ID) == set(DIM.Series_ID) == set(W.Series_ID)
    assert sorted(L.target_variable.unique()) == sorted(VARS) and sorted(L.horizon.unique()) == list(range(1, 13))
    assert (L.groupby(["Series_ID", "target_variable"]).size() == 12).all()
    assert L.district_lgd_code.nunique() == 56 and L.state.nunique() == 4 and L.district_tier.nunique() == 16 and L.sector.nunique() == 5
    assert set(L.district_lgd_code) == set(DIM.District_LGD_Code)
    assert (L.origin_month == ORIGIN).all() and L.target_month.min() == "2026-11" and L.target_month.max() == "2027-10"
    per = L.groupby("district_lgd_code").sector.nunique()
    assert (per == 5).all()


def test_forecasts_and_intervals_are_valid():
    cols = ["forecast", "lo90", "hi90", "baseline_forecast", "last_observed"]
    assert L[cols].notna().all().all() and np.isfinite(L[cols].to_numpy()).all()
    assert (L.lo90 > 0).all() and (L.lo90 < L.forecast).all() and (L.forecast < L.hi90).all()
    r = L.forecast / L.last_observed
    assert r.between(0.5, 1.5).all(), "a forecast moved by more than 50% from the last observation"
    w = (L.hi90 - L.lo90) / L.forecast
    m = L.groupby(["target_variable", "horizon"]).apply(lambda g: ((g.hi90 - g.lo90) / g.forecast).mean(), include_groups=False)
    for v in VARS:
        assert m.loc[(v, 12)] > m.loc[(v, 1)], v                       # uncertainty grows with the horizon
    assert set(L.groupby("target_variable").interval_method.first()) == {"static (fold-based)", "static (recalibrated)", "adaptive conformal"}
    assert set(L.confidence) == {"high", "medium", "low"} and (L[L.target_variable == VARS[0]].confidence == "high").all()
    assert (L[(L.target_variable == VARS[1])].confidence == "low").all() and (L[(L.sector == "IT-ITeS") & (L.target_variable != VARS[0])].confidence == "low").all()


def test_flags_are_well_formed():
    assert set(W.forecast_status) <= {"Tightest decile", "Tight", "Typical", "Loose", "Loosest decile"}
    assert set(W.absolute_context) <= {"openings exceed seekers", "moderate", "oversupplied", "deep surplus"}
    assert W.forecast_percentile.between(0, 100).all() and (W.forecast_coverage_ratio > 0).all()
    for (sec, h), g in W.groupby(["sector", "horizon"]):
        assert len(g) == 56, (sec, h)
        share = (g.forecast_status == "Tightest decile").mean()
        assert 0.07 <= share <= 0.14, (sec, h, share)                   # about a tenth of a sector's districts, by construction
        assert (g.change == "entering tightest decile").sum() == (g.change == "leaving tightest decile").sum()
        assert (g.change == "entering loosest decile").sum() == (g.change == "leaving loosest decile").sum()
    flagged = W[W.forecast_status.isin(["Tightest decile", "Loosest decile"])]
    assert flagged.historical_precision.between(0.6, 0.85).all() and W[~W.index.isin(flagged.index)].historical_precision.isna().all()
    assert (W.confidence == "low").all()


def test_models_match_their_manifest_and_were_refitted_on_history_to_the_origin():
    man = json.load(open(MODELS / "manifest.json"))
    for name, digest in man["files_sha256"].items():
        assert sp.sha256(MODELS / name) == digest, name
    assert man["history"][1] == f"{ORIGIN}-01" and man["panel_sha256"] == sp.sha256(ROOT / "data" / "processed" / "panel_monthly.parquet")
    assert man["source_declaration_sha256"] == sp.sha256(ROOT / "models" / "xgboost_v3" / "declaration.json")
    prm = json.load(open(MODELS / "params.json"))
    v3 = json.load(open(ROOT / "models" / "xgboost_v3" / "primary" / "params.json"))
    for k in "EVS":
        assert prm[k]["xgboost_params"] == v3[k]["xgboost_params"] and prm[k]["config"] == v3[k]["config"], k       # nothing re-tuned
        assert prm[k]["n_series"] == 280 and prm[k]["last_target_index"] == 189
    assert len(list(MODELS.glob("*.ubj"))) == 15


def test_no_forecast_feature_uses_months_after_the_origin():
    import engineering as en
    import features as ft
    short, full = ft.load_history(ORIGIN), ft.load_history("2026-12")
    rows, _ = ft.forecast_rows(short)
    Df = en.PanelData(full)
    OF, SF = en.origin_features(Df)
    ex = en.make_categorical(en.build_examples(Df, OF, SF, horizons=[1, 2], origin_min=Df.T - 3, origin_max=Df.T - 3), Df)
    a = rows[rows.horizon.isin([1, 2])].sort_values(["Series_ID", "horizon"]).reset_index(drop=True)
    b = ex[ex.origin_idx == Df.T - 3].sort_values(["Series_ID", "horizon"]).reset_index(drop=True)
    cols = [c for c in a.columns if c in b.columns and a[c].dtype.kind in "fi" and not c.startswith("target_") and c not in ("origin_idx", "series_row")]
    assert len(cols) > 80 and all(np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), equal_nan=True) for c in cols)
    assert short.Date.max() == pd.Timestamp("2026-10-01") and pd.Timestamp("2026-10-01") <= pd.Timestamp("2026-10-19")


def test_the_forecast_run_is_reproducible():
    import forecast
    before = json.load(open(OUT / "manifest.json"))["files_sha256"]
    forecast.main(ORIGIN)
    after = json.load(open(OUT / "manifest.json"))["files_sha256"]
    assert before == after, "a second run produced different files"


def test_refit_backtest_shows_more_data_does_not_hurt():
    b = json.load(open(ROOT / "reports" / "deployment" / "refit_backtest.json"))["wape_mean_horizon"]
    new = {k: v["refit_to_2025-12"] for k, v in b.items()}
    old = {k: v["v3_fitted_to_2022-12"] for k, v in b.items()}
    assert new["E"] < old["E"] and new["S"] < old["S"] and new["V"] < 1.03 * old["V"]
    assert b["V"]["baseline"] < new["V"], "documented: in 2026 the vacancy model is not better than the baseline"


def test_synthetic_months_check_is_in_range_and_the_document_matches():
    syn = json.load(open(ROOT / "reports" / "deployment" / f"synthetic_check_{ORIGIN}.json"))["checks"]
    assert len(syn) == 6 and all(v["wape_pct"] < 8 for v in syn.values())
    doc = (ROOT / "docs" / "phases" / "PHASE_9_DEPLOYMENT.md").read_text(encoding="utf-8")
    man = json.load(open(OUT / "manifest.json"))
    assert f"{man['coverage']['forecast_rows']:,}" in doc and f"{man['coverage']['flag_rows']:,}" in doc
    b = json.load(open(ROOT / "reports" / "deployment" / "refit_backtest.json"))["wape_mean_horizon"]
    for k in "EVS":
        assert f"{b[k]['refit_to_2025-12']:.2f}" in doc and f"{b[k]['v3_fitted_to_2022-12']:.2f}" in doc, k


if __name__ == "__main__":
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"[PASS] {n}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {n}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
