#!/usr/bin/env python3
"""
Phase 8 - fit and save every model that the one-shot test evaluation will compare, then freeze.  Reads only the train and validation splits.

Variants written to models/xgboost_v2/:
    primary/       tuned configuration (finalize_<k>.json) + horizon blend with the baseline + recalibrated intervals, fitted on train + validation.
                   Declared as the Phase 8 candidate BEFORE the test split is opened (it is what Phase 9 would deploy: the newest labels, as agreed in D1 of Phase 7).
    train_only/    same configuration fitted on the train split alone (shows what the extra 10 months of labels are worth)
    v1_refit/      the Phase 7 configuration, no blend, Phase 7 intervals, fitted on train + validation (shows what Phase 8 tuning is worth)
    challenger_hgb/ scikit-learn HistGradientBoosting with the Phase 6 settings, fitted on train + validation
frozen_config.json records SHA-256 of every file and that the test split had not been opened.

Run: python src/evaluation/build_models.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import opt_lib as ol  # noqa: E402
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402

OUT = ROOT / "reports" / "evaluation"
V2 = ROOT / "models" / "xgboost_v2"
V1 = ROOT / "models" / "xgboost_v1"
SEEDS = (42, 43, 44, 45, 46)
HGB = dict(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=100, l2_regularization=5.0, random_state=42)


def fit_variant(name, cfgs, trees, blend, intervals, frames, with_validation, note, extra_blend=None):
    d = V2 / name
    d.mkdir(parents=True, exist_ok=True)
    params, pres, files = {}, {}, {}
    for k in "EVS":
        sk = ld.spec()[k]
        tr_all, va_all = frames[k]
        df = pd.concat([tr_all, va_all]) if with_validation else tr_all
        tr = ld.train_rows(df, k, sk)
        X, y = ld.xy(tr, k, sk)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"], allowed=("train", "validation") if with_validation else ("train",))
        end = 143 if with_validation else 133
        models = ol.fit_ensemble(cfgs[k], trees[k], pre.transform(X), y, tr.target_idx.to_numpy(), end, -1, SEEDS)
        for sd, m in zip(SEEDS, models):
            m.save_model(d / f"{k}_seed{sd}.ubj")
        pres[k] = pre.to_dict()
        params[k] = dict(xgboost_params={**ol.BASE_FIXED, **ol.model_params(cfgs[k]), "n_estimators": int(trees[k]), "n_jobs": -1}, config=cfgs[k], seeds=list(SEEDS),
                         features=sk["features"], base=sk["base"], mask_shock_windows=sk["mask_shock_windows"], training_rows=int(len(tr)), rows_added_by_validation=int(len(tr) - len(ld.train_rows(tr_all, k, sk))) if with_validation else 0,
                         ensemble="mean of the seed models' predicted log changes")
        print(f"  {name} {k}: {len(tr):,} rows ({params[k]['rows_added_by_validation']:,} from validation), {trees[k]} trees", flush=True)
    json.dump(params, open(d / "params.json", "w"), indent=1, default=float)
    json.dump(pres, open(d / "preprocessor.json", "w"), indent=1)
    json.dump({"level": [0.05, 0.95], "unit": "log error; add to the predicted log level", "by_target_horizon": intervals}, open(d / "intervals.json", "w"), indent=1)
    if blend:
        json.dump({"model_weight_by_target_horizon": blend, "rule": "pred_log = w * model + (1 - w) * (last value + seasonal shift), per horizon"}, open(d / "blend.json", "w"), indent=1)
    if extra_blend:
        json.dump({"model_weight_by_target_horizon": extra_blend, "rule": "weights chosen on the rolling-origin folds before the validation veto; evaluated as the comparison model cv_blend"}, open(d / "blend_cv.json", "w"), indent=1)
    for f in sorted(d.iterdir()):
        files[f.name] = sp.sha256(f)
    json.dump({"variant": name, "note": note, "files_sha256": files, "trained_on_validation_too": with_validation, "test_split_opened": False,
               "environment": {"xgboost": xgb.__version__, "numpy": np.__version__, "pandas": pd.__version__}}, open(d / "checkpoint_manifest.json", "w"), indent=1)
    return files


def main():
    t0 = time.time()
    fin = {k: json.load(open(OUT / f"finalize_{k}.json")) for k in "EVS"}
    frames = {k: (sp.load_split("train", columns=ol.columns(k)), sp.load_split("validation", columns=ol.columns(k))) for k in "EVS"}
    cfgs = {k: fin[k]["chosen"]["cfg"] for k in "EVS"}
    trees = {k: fin[k]["chosen"]["n_trees"] for k in "EVS"}
    blend = {k: fin[k]["blend_weights_final"] for k in "EVS"}
    blend_cv = {k: fin[k]["blend_weights_cv"] for k in "EVS"}
    itv = {k: fin[k]["intervals"] for k in "EVS"}
    allfiles = {}
    allfiles["primary"] = fit_variant("primary", cfgs, trees, blend, itv, frames, True, "Phase 8 candidate: tuned, blended where the validation veto allows, recalibrated; fitted on train + validation", extra_blend=blend_cv)
    allfiles["train_only"] = fit_variant("train_only", cfgs, trees, blend, itv, frames, False, "same configuration fitted on the train split only")
    inc = {k: ol.incumbent_config(k) for k in "EVS"}
    v1itv = json.load(open(V1 / "intervals.json"))["by_target_horizon"]
    one = {k: {str(h): 1.0 for h in range(1, 13)} for k in "EVS"}
    allfiles["v1_refit"] = fit_variant("v1_refit", {k: inc[k][0] for k in "EVS"}, {k: inc[k][1] for k in "EVS"}, None, v1itv, frames, True,
                                       "Phase 7 configuration, no blend, Phase 7 intervals; fitted on train + validation")
    # challenger
    d = V2 / "challenger_hgb"
    d.mkdir(parents=True, exist_ok=True)
    for k in "EVS":
        sk = ld.spec()[k]
        tr = ld.train_rows(pd.concat(frames[k]), k, sk)
        X, y = ld.xy(tr, k, sk)
        joblib.dump(HistGradientBoostingRegressor(**HGB).fit(X, y), d / f"{k}.joblib")
    allfiles["challenger_hgb"] = {f.name: sp.sha256(f) for f in sorted(d.iterdir())}
    json.dump({"settings": HGB, "note": "Phase 6 HistGradientBoosting settings, raw features (missing values handled natively), fitted on train + validation"}, open(d / "settings.json", "w"), indent=1)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    frozen = dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), git_head_at_freeze=head, test_split_opened=False,
                  test_file_sha256=json.load(open(sp.MANIFEST))["files"]["test"]["sha256"],
                  declared_primary="primary", declared_comparisons=["train_only", "v1_refit", "challenger_hgb", "baselines"],
                  chosen={k: dict(name=fin[k]["chosen"]["name"], n_trees=trees[k], config=cfgs[k]) for k in "EVS"},
                  finalize_sha256={k: sp.sha256(OUT / f"finalize_{k}.json") for k in "EVS"}, files_sha256=allfiles,
                  rule="No setting, weight or interval is changed after the test split is opened; the evaluation reports everything it computes.")
    json.dump(frozen, open(V2 / "frozen_config.json", "w"), indent=1)
    print(f"frozen in {time.time() - t0:.0f}s -> {V2 / 'frozen_config.json'}")


if __name__ == "__main__":
    main()
