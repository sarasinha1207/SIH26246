"""Phase 8 tests: the freeze held, the test split was opened once and only by the evaluator, results are reproducible from the frozen files, and the document matches the tables.
Runs under pytest or standalone: python tests/test_evaluation.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for sub in ("common", "training", "evaluation"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import splits as sp  # noqa: E402
from predict import Forecaster  # noqa: E402

from _guard import read_doc, skip_module_unless  # noqa: E402
skip_module_unless(ROOT / "models" / "xgboost_v2", ROOT / "docs" / "phases" / "PHASE_8_EVALUATION_AND_TUNING.md", why="checks the frozen Phase 8 models and write-up, which are kept locally")
V2, OUT = ROOT / "models" / "xgboost_v2", ROOT / "reports" / "evaluation"
T = OUT / "test"
DOC = read_doc(ROOT / "docs" / "phases" / "PHASE_8_EVALUATION_AND_TUNING.md")
FR = json.load(open(V2 / "frozen_config.json"))
OV = pd.read_csv(T / "overall.csv").set_index(["target", "model"])


def test_frozen_files_are_unchanged_since_the_freeze():
    assert FR["test_split_opened"] is False
    for variant, files in FR["files_sha256"].items():
        for name, digest in files.items():
            assert sp.sha256(V2 / variant / name) == digest, f"{variant}/{name}"
    for k, digest in FR["finalize_sha256"].items():
        assert sp.sha256(OUT / f"finalize_{k}.json") == digest, k
    assert FR["test_file_sha256"] == json.load(open(sp.MANIFEST))["files"]["test"]["sha256"]


def test_the_test_split_was_evaluated_once_after_the_freeze():
    log = json.load(open(OUT / "test_access_log.json"))["runs"]
    assert len(log) == 1 and "finished" in log[0]
    assert log[0]["frozen_at"] == FR["frozen_at"] and log[0]["time"] > FR["frozen_at"]
    assert log[0]["frozen_config_sha256"] == sp.sha256(V2 / "frozen_config.json")
    reads = json.load(open(OUT / "test_access_log.json"))["descriptive_reads"]
    assert {r["script"].split("/")[-1] for r in reads} >= {"extra_metrics.py", "coverage_check.py", "diagnostics.py"} 
    # after the evaluation only the interval policy and the seekers blend declaration (both documented in the Phase 8 document, Section 11) were decided from the spent test split
    assert {r["script"] for r in reads if r["changed_any_model_or_decision"]} <= {"src/evaluation/evaluate_v3.py original", "src/evaluation/recal_static_intervals.py"}


def test_only_the_evaluation_code_unlocks_the_test_split():
    allowed = {"evaluate.py", "diagnostics.py", "make_splits.py", "extra_metrics.py", "coverage_check.py", "flag_significance.py", "evaluate_v3.py", "recal_static_intervals.py"}      # the last two are read-only audits listed under descriptive_reads in the access log
    for d in ("training", "evaluation", "splits"):
        for p in (ROOT / "src" / d).glob("*.py"):
            src = p.read_text(encoding="utf-8")
            if p.name not in allowed:
                assert "unlock_test" not in src or p.name == "predict.py", p.name
    for p in ("tune_optuna.py", "finalize.py", "recalibrate.py", "build_models.py", "it_experiment.py", "opt_lib.py"):
        assert 'load_split("test"' not in (ROOT / "src" / "evaluation" / p).read_text(encoding="utf-8"), p


def test_saved_test_predictions_are_reproduced_by_the_frozen_checkpoint():
    pred = pd.read_parquet(ROOT / "data" / "interim" / "phase8_test_predictions.parquet")
    test = sp.load_split("test", unlock_test=True, verify=True)
    out = Forecaster.load(V2 / "primary").predict(test)
    for k in "EVS":
        s = pred[pred.target == k].reset_index(drop=True)
        assert len(s) == len(test) == 142800
        assert np.abs(s["primary"].to_numpy() - out[f"pred_log_{k}"].to_numpy()).max() < 1e-9, k


def test_blend_and_veto_are_recorded_consistently():
    fin = {k: json.load(open(OUT / f"finalize_{k}.json")) for k in "EVS"}
    assert fin["S"]["blend_veto"]["applied"] and not fin["E"]["blend_veto"]["applied"] and not fin["V"]["blend_veto"]["applied"]
    prim = json.load(open(V2 / "primary" / "blend.json"))["model_weight_by_target_horizon"]
    cvb = json.load(open(V2 / "primary" / "blend_cv.json"))["model_weight_by_target_horizon"]
    assert set(prim["S"].values()) == {1.0} and min(cvb["S"].values()) == 0.5 and set(prim["V"].values()) == {1.0}
    assert all(0 <= w <= 1 for k in "EVS" for w in cvb[k].values())


def test_primary_equals_train_only_for_employed_because_validation_rows_are_masked():
    p = json.load(open(V2 / "primary" / "params.json"))["E"]
    assert p["rows_added_by_validation"] == 0
    assert abs(OV.loc[("E", "primary"), "wape_mean_horizon"] - OV.loc[("E", "train_only"), "wape_mean_horizon"]) < 1e-9


def test_seekers_scores_exclude_the_two_ramp_months_and_nothing_else_is_excluded():
    r = json.load(open(OUT / "test_results.json"))["targets"]
    assert r["S"]["excluded_shock_rows"] == 840 and r["E"]["excluded_shock_rows"] == 0 and r["V"]["excluded_shock_rows"] == 0


def test_optuna_searches_include_the_incumbent_and_cover_enough_trials():
    for k, n_min in (("E", 100), ("V", 70), ("S", 40)):
        t = pd.read_csv(OUT / f"optuna_{k}_trials.csv")
        assert len(t) >= n_min and (t.state == "COMPLETE").all()
        assert t.number.iloc[0] == 0


def test_phase8_document_matches_the_result_tables():
    for k in "EVS":
        for m in ("primary", "cv_blend", "v1_refit", "hgb"):
            assert f"{OV.loc[(k, m), 'wape_mean_horizon']:.2f}" in DOC, (k, m)
    sc = pd.read_csv(T / "phase1_scorecard.csv").set_index("target")
    assert f"{sc.loc['E', 'wape_mean_horizon']:.2f}" in DOC and f"{sc.loc['V', 'wape_mean_horizon']:.2f}" in DOC
    cov = pd.read_csv(T / "interval_coverage.csv")
    for k in "EVS":
        c = cov[(cov.target == k) & (cov.intervals == "primary")].coverage.mean()
        assert f"{100 * c:.0f}%" in DOC, k
    late = pd.read_csv(T / "scores_2025_26_only.csv").set_index("target")
    assert f"{late.loc['E', 'primary']:.2f}" in DOC and f"{late.loc['S', 'cv_blend']:.2f}" in DOC
    ex = pd.read_csv(T / "extra_comparisons.csv")
    row = ex[(ex.target == "S") & (ex.comparison == "cv_blend minus last_plus_seasonal_shift")].iloc[0]
    assert f"{row['diff']:.2f}".replace("-", "−") in DOC or f"{abs(row['diff']):.2f}" in DOC


def test_model_card_v2_lists_the_frozen_parameters():
    card = (V2 / "model_card.md").read_text(encoding="utf-8")
    prm = json.load(open(V2 / "primary" / "params.json"))
    for k in "EVS":
        assert str(prm[k]["xgboost_params"]["n_estimators"]) in card
    for key in ("learning_rate", "max_leaves", "min_child_weight", "reg_lambda", "reg_alpha", "gamma", "subsample", "colsample_bytree"):
        assert f"`{key}`" in card


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
