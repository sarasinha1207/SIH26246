"""Phase 7 tests: preprocessing is train-only, the checkpoint reloads and reproduces its predictions, the test split was never opened, the card matches the files.
Runs under pytest or standalone: python tests/test_training.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for sub in ("common", "training"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from predict import Forecaster  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402

from _guard import read_doc, skip_module_unless  # noqa: E402
skip_module_unless(ROOT / "models" / "xgboost_v1", ROOT / "docs" / "phases" / "PHASE_7_MODEL_TRAINING.md", why="checks the Phase 7 models and write-up, which are kept locally")
M = ROOT / "models" / "xgboost_v1"
R = ROOT / "reports" / "training"
PARAMS, MAN = json.load(open(M / "params.json")), json.load(open(M / "checkpoint_manifest.json"))
CARD = (M / "model_card.md").read_text(encoding="utf-8")
SPEC = ld.spec()


def _cols(k):
    return ["split", "Series_ID", "origin_idx", "horizon"] + sorted((set(SPEC[k]["features"]) | {f"{SPEC[k]['base']}_{k}"}) - {"horizon"})


def test_preprocessor_is_fitted_on_train_only():
    k = "V"
    tr, va = sp.load_split("train", columns=_cols(k)), sp.load_split("validation", columns=_cols(k))
    X = tr[SPEC[k]["features"]]
    try:
        FeaturePreprocessor(X.columns).fit(va[SPEC[k]["features"]], va["split"])
    except ValueError:
        pass
    else:
        raise AssertionError("fit accepted validation rows")
    pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
    before = json.dumps(pre.to_dict(), sort_keys=True)
    Z = pre.transform(va[SPEC[k]["features"]])
    assert json.dumps(pre.to_dict(), sort_keys=True) == before, "transform changed the fitted statistics"
    for c in pre.continuous[:5]:
        assert abs(X[c].mean() - pre.mean[c]) < 1e-9 and abs(X[c].std(ddof=0) - pre.std[c]) < 1e-9
    Zt = pre.transform(X)
    assert np.allclose(Zt[pre.continuous].mean(), 0, atol=1e-8) and np.allclose(Zt[pre.continuous].std(ddof=0), 1, atol=1e-8)
    assert not np.allclose(Z[pre.continuous].mean(), 0, atol=1e-3), "validation was standardised with its own statistics"
    saved = json.load(open(M / "preprocessor.json"))[k]
    assert saved["n_rows"] == len(X) and saved["fitted_on"] == "train split only"


def test_missing_values_are_imputed_with_training_medians():
    k = "V"
    tr = sp.load_split("train", columns=_cols(k))
    pre = FeaturePreprocessor.from_dict(json.load(open(M / "preprocessor.json"))[k])
    row = tr[SPEC[k]["features"]].head(3).copy()
    row.iloc[0, 0] = np.nan
    out = pre.transform(row)
    c0 = row.columns[0]
    expect = (pre.median[c0] - pre.mean[c0]) / pre.std[c0] if c0 in pre.continuous else pre.median[c0]
    assert abs(out.iloc[0, 0] - expect) < 1e-9


def test_scaling_does_not_materially_change_the_trees():
    chk = json.load(open(R / "preprocessing_check.json"))
    for k in "EVS":
        assert abs(chk[k]["difference_points"]) < 0.1, (k, chk[k]["difference_points"])


def test_checkpoint_files_match_the_manifest():
    for name, digest in MAN["files_sha256"].items():
        assert sp.sha256(M / name) == digest, name
    assert MAN["test_split_opened"] is False
    assert len(list(M.glob("*.ubj"))) == 15


def test_split_files_used_for_training_are_the_recorded_ones():
    sm = json.load(open(sp.MANIFEST))
    assert MAN["trained_on"]["sha256"] == sm["files"]["train"]["sha256"] and MAN["reported_on"]["sha256"] == sm["files"]["validation"]["sha256"]


def test_training_code_never_opens_the_test_split():
    for p in (ROOT / "src" / "training").glob("*.py"):
        src = p.read_text(encoding="utf-8")
        if p.name != "predict.py":
            assert "unlock_test" not in src, p.name
        assert 'load_split("test"' not in src and "load_split('test'" not in src, p.name


def test_checkpoint_reload_reproduces_the_saved_validation_predictions():
    fc = Forecaster.load(M)
    va = sp.load_split("validation")
    out = fc.predict(va)
    saved = pd.read_parquet(R / "validation_predictions.parquet")
    key = ["Series_ID", "origin_idx", "horizon"]
    m = out.assign(origin_idx=va.origin_idx.to_numpy()).merge(saved, on=key, suffixes=("", "_saved"))
    for k in "EVS":
        s = m.dropna(subset=[f"pred_log_{k}_saved"])
        assert len(s) == saved[f"pred_log_{k}"].notna().sum()
        assert np.abs(s[f"pred_log_{k}"] - s[f"pred_log_{k}_saved"]).max() < 1e-9, k


def test_prediction_script_runs_in_a_fresh_process_and_refuses_test():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.parquet"
        r = subprocess.run([sys.executable, str(ROOT / "src" / "training" / "predict.py"), "--split", "validation", "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-500:]
        f = pd.read_parquet(out)
        assert len(f) == 15400 and {"pred_E", "lo90_E", "hi90_E", "pred_V", "pred_S"} <= set(f.columns)
        assert (f.lo90_E < f.pred_E).all() and (f.pred_E < f.hi90_E).all() and (f.pred_V > 0).all()
        r = subprocess.run([sys.executable, str(ROOT / "src" / "training" / "predict.py"), "--split", "test", "--out", str(Path(d) / "t.parquet")], capture_output=True, text=True)
        assert r.returncode != 0 and "locked" in r.stderr


def test_regularisation_and_multicore_settings():
    for k in "EVS":
        p = PARAMS[k]["xgboost_params"]
        assert p["tree_method"] == "hist" and p["n_jobs"] == -1
        assert p["reg_lambda"] > 0 and p["min_child_weight"] >= 50 and p["subsample"] < 1 and (p["colsample_bytree"] < 1 or p["colsample_bynode"] < 1)
        assert p["learning_rate"] <= 0.08 and p["max_leaves"] <= 63 and p["n_estimators"] <= 400
        assert len(PARAMS[k]["seeds"]) == 5
        feats = PARAMS[k]["features"]
        calendar = {"target_month", "target_month_sin", "target_month_cos"}          # known in advance, not the target value
        assert not [f for f in feats if f.startswith(("target_", "last_", "sm3_", "sm6_")) and f not in calendar], "base or target columns used as features"


def test_intervals_are_ordered_and_cover_all_horizons():
    itv = json.load(open(M / "intervals.json"))["by_target_horizon"]
    for k in "EVS":
        assert sorted(map(int, itv[k])) == list(range(1, 13))
        assert all(lo < 0 < hi for lo, hi in itv[k].values())


def test_validation_model_beats_the_best_baseline_in_aggregate():
    met = json.load(open(R / "validation_metrics.json"))
    for k in "EVS":
        assert met[k]["validation_wape_mean_horizon"] < met[k]["baselines"]["last_plus_seasonal_shift"]["mean_horizon"], k


def test_model_card_lists_every_hyperparameter_and_the_reported_scores():
    for key in ("learning_rate", "max_leaves", "min_child_weight", "reg_lambda", "reg_alpha", "gamma", "subsample", "colsample_bytree", "colsample_bynode", "max_bin", "n_estimators"):
        row = [ln for ln in CARD.splitlines() if ln.startswith(f"| `{key}`")]
        assert row, key
        cells = [c.strip() for c in row[0].split("|")[2:5]]
        for k, cell in zip("EVS", cells):
            assert float(cell) == float(PARAMS[k]["xgboost_params"][key]), (key, k, cell)
    for k, v in MAN["validation_wape_mean_horizon"].items():
        assert f"{v:.2f}" in CARD, k
    assert "Seed averaging" in CARD and "train split only" in CARD


def test_phase7_document_quotes_the_saved_scores():
    doc = read_doc(ROOT / "docs" / "phases" / "PHASE_7_MODEL_TRAINING.md")
    met = json.load(open(R / "validation_metrics.json"))
    for k in "EVS":
        assert f"{met[k]['validation_wape_mean_horizon']:.2f}" in doc and f"{met[k]['baselines']['last_plus_seasonal_shift']['mean_horizon']:.2f}" in doc, k
        assert f"{100 * met[k]['interval_90_validation_coverage']:.0f}%" in doc, k
    sm = json.load(open(sp.MANIFEST))["files"]
    for n in sp.NAMES:
        assert f"{sm[n]['rows']:,}" in doc, n


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
