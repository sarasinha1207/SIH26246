#!/usr/bin/env python3
"""
Phase 7 - fit the final XGBoost models (one per target) on the TRAIN split with the tuned settings and write the checkpoint folder.

Reads reports/training/tune_<k>_best.json (written by tune.py).  Reads only the train and validation splits; the test split is never opened.
Writes to models/xgboost_v1/:  <E|V|S>_seed<42..46>.ubj (XGBoost native format; the five seeds are averaged), preprocessor.json, params.json, intervals.json, checkpoint_manifest.json,
logs/train.log, and reports/training/{validation_metrics.json, validation_predictions.parquet, learning_curves.json}.

Prediction intervals: 5% and 95% quantiles of the log error of the same configuration in the rolling-origin folds (out-of-sample), by target and horizon.
The validation split is used to report; it is not used to fit the preprocessor or the model (the trees are not early-stopped on it).

Run: python src/training/train.py
"""
import json
import logging
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
import tune  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402

MODEL_DIR = ROOT / "models" / "xgboost_v1"
REPORT = ROOT / "reports" / "training"
LEVELS = (0.05, 0.95)
SEED = 42


def columns(k, spec):
    ids = ["split", "Series_ID", "origin_idx", "target_idx", "origin_date", "target_date", "horizon", "shock_EV", "shock_S", "target_in_shock_EV", "target_in_shock_S"]
    return ids + sorted((set(spec["features"]) | {f"{spec['base']}_{k}", f"target_{k}", f"last_{k}", f"{k}_sf_shift", f"{k}_yadrift_h"}) - set(ids))


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (MODEL_DIR / "logs").mkdir(exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=[logging.FileHandler(MODEL_DIR / "logs" / "train.log", mode="w"), logging.StreamHandler()])
    log = logging.info
    spec = ld.spec()
    t_all = time.time()
    log("Phase 7 training: XGBoost %s, pandas %s, numpy %s, python %s", xgb.__version__, pd.__version__, np.__version__, platform.python_version())
    log("splits: %s", json.dumps({k: v["rows"] for k, v in json.load(open(sp.MANIFEST))["files"].items()}))
    sp.load_split("train", columns=["split"], verify=True)
    sp.load_split("validation", columns=["split"], verify=True)
    log("train and validation files match the checksums in split_manifest.json; the test file is not opened")
    params, metrics, curves, preds, intervals, files = {}, {}, {}, {}, {}, {}
    pre_all = {}
    for k in "EVS":
        t0 = time.time()
        best = json.load(open(REPORT / f"tune_{k}_best.json"))["chosen"]
        cfg = {key: (int(v) if key in ("max_leaves", "min_child_weight", "max_bin") else float(v)) for key, v in best["cfg"].items()}
        n_trees = int(best["best_trees"])
        sk = spec[k]
        cols = columns(k, sk)
        tr_all, va_all = sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols)
        tr = ld.train_rows(tr_all, k)
        X, y = ld.xy(tr, k)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        Xt = pre.transform(X)
        va = ld.eval_rows(va_all, k, mask_shock=(k != "S"))
        Xv = pre.transform(ld.xy(va, k)[0])
        yv = ld.xy(va, k)[1]
        log("[%s] fitting %d seeds x %d trees on %d rows (%d of %d train rows after the shock-window policy, %d features)", k, len(tune.SEEDS), n_trees, len(Xt), len(tr),
            len(tr_all), Xt.shape[1])
        models = []
        for sd in tune.SEEDS:
            m = tune.make_model(cfg, n_trees, jobs=-1)
            m.set_params(random_state=sd, eval_metric="rmse")
            m.fit(Xt, y, eval_set=[(Xt, y), (Xv, yv)], verbose=False)         # eval_set only records learning curves; no early stopping
            if sd == tune.SEEDS[0]:
                ev = m.evals_result()
                curves[k] = {"train_rmse": [float(v) for v in ev["validation_0"]["rmse"]], "validation_rmse": [float(v) for v in ev["validation_1"]["rmse"]],
                             "note": f"seed {sd} only"}
            m.save_model(MODEL_DIR / f"{k}_seed{sd}.ubj")
            files[f"{k}_seed{sd}.ubj"] = sp.sha256(MODEL_DIR / f"{k}_seed{sd}.ubj")
            models.append(m)
        model = type("Bag", (), {"predict": staticmethod(lambda X, models=models: tune.predict_bag(models, X))})
        pre_all[k] = pre.to_dict()
        params[k] = {"xgboost_params": {**tune.FIXED, **cfg, "n_estimators": n_trees, "n_jobs": -1}, "seeds": list(tune.SEEDS), "ensemble": "mean of the seed models' predicted log changes", "selected_by": json.load(open(REPORT / f"tune_{k}_best.json"))["selection_rule"],
                     "features": sk["features"], "base": sk["base"], "mask_shock_windows": sk["mask_shock_windows"],
                     "cv_wape_mean_of_folds": best["cv_wape"], "validation_wape_at_selection": best["val_wape"]}
        # ---- scores
        pv = ld.base_log(va, k) + model.predict(Xv)
        act = va[f"target_{k}"].to_numpy()
        tr_eval = ld.eval_rows(tr_all, k)
        ptr = ld.base_log(tr_eval, k) + model.predict(pre.transform(ld.xy(tr_eval, k)[0]))
        mv, bh = ld.mean_horizon_wape(va, act, pv)
        out = {"validation_rows": int(len(va)), "validation_wape_mean_horizon": mv, "validation_wape_by_horizon": bh,
               "validation_wape_pooled": ld.wape(act, pv),
               "train_wape_mean_horizon_in_sample": ld.mean_horizon_wape(tr_eval, tr_eval[f"target_{k}"].to_numpy(), ptr)[0], "baselines": {}}
        for b in ("last_value", "last_plus_seasonal_shift", "seasonal_naive_drift"):
            pb = ld.baseline_log(va, k, b)
            out["baselines"][b] = {"mean_horizon": ld.mean_horizon_wape(va, act, pb)[0], "by_horizon": ld.mean_horizon_wape(va, act, pb)[1]}
        out["shock_masked_validation"] = k != "S"
        metrics[k] = out
        preds[k] = pd.DataFrame({"Series_ID": va.Series_ID.to_numpy(), "origin_idx": va.origin_idx.to_numpy(), "horizon": va.horizon.to_numpy(), f"pred_log_{k}": pv,
                                 f"actual_log_{k}": act})
        log("[%s] validation WAPE (mean over horizons) %.3f vs last value + seasonal shift %.3f; in-sample %.3f; %.0fs", k, mv,
            out["baselines"]["last_plus_seasonal_shift"]["mean_horizon"], out["train_wape_mean_horizon_in_sample"], time.time() - t0)
        # ---- interval widths from out-of-sample rolling-origin folds
        resid = {h: [] for h in range(1, 13)}
        for f in tune.build_folds(tr_all, k):
            e = f["act"] - (f["base_v"] + tune.predict_bag(tune.fit_bag(cfg, n_trees, f["X"], f["y"], jobs=-1), f["Xv"]))
            for h, grp in pd.Series(e).groupby(f["va"]["horizon"].to_numpy()):
                resid[int(h)].extend(grp.tolist())
        intervals[k] = {str(h): [float(np.quantile(v, LEVELS[0])), float(np.quantile(v, LEVELS[1]))] for h, v in resid.items()}
        lo = np.array([intervals[k][str(h)][0] for h in va.horizon])
        hi = np.array([intervals[k][str(h)][1] for h in va.horizon])
        metrics[k]["interval_90_validation_coverage"] = float(np.mean((act >= pv + lo) & (act <= pv + hi)))
        log("[%s] 90%% interval coverage on validation: %.3f (nominal 0.90)", k, metrics[k]["interval_90_validation_coverage"])
    pre_json = {k: v for k, v in pre_all.items()}
    json.dump(pre_json, open(MODEL_DIR / "preprocessor.json", "w"), indent=1)
    json.dump(params, open(MODEL_DIR / "params.json", "w"), indent=1)
    json.dump({"level": [LEVELS[0], LEVELS[1]], "unit": "log error (actual - predicted log level); add to the predicted log level",
               "source": "rolling-origin folds 2016-12, 2017-12, 2018-12 inside the train split, same configuration", "by_target_horizon": intervals},
              open(MODEL_DIR / "intervals.json", "w"), indent=1)
    for fn in ("preprocessor.json", "params.json", "intervals.json"):
        files[fn] = sp.sha256(MODEL_DIR / fn)
    p = preds["E"].merge(preds["V"], on=["Series_ID", "origin_idx", "horizon"], how="outer").merge(preds["S"], on=["Series_ID", "origin_idx", "horizon"], how="outer")
    p.to_parquet(REPORT / "validation_predictions.parquet", index=False)
    json.dump(metrics, open(REPORT / "validation_metrics.json", "w"), indent=1)
    json.dump(curves, open(REPORT / "learning_curves.json", "w"))
    sm = json.load(open(sp.MANIFEST))
    manifest = {"model": "xgboost_v1", "targets": {k: ld.NAMES[k] for k in "EVS"}, "files_sha256": files,
                "trained_on": {"split": "train", "sha256": sm["files"]["train"]["sha256"], "rows": sm["files"]["train"]["rows"], "target_range": sm["files"]["train"]["target_range"]},
                "reported_on": {"split": "validation", "sha256": sm["files"]["validation"]["sha256"]},
                "test_split_opened": False,
                "environment": {"python": platform.python_version(), "xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
                "seed": SEED, "training_seconds": round(time.time() - t_all), "validation_wape_mean_horizon": {k: metrics[k]["validation_wape_mean_horizon"] for k in "EVS"}}
    json.dump(manifest, open(MODEL_DIR / "checkpoint_manifest.json", "w"), indent=1)
    log("done in %.0fs; checkpoint folder %s", time.time() - t_all, MODEL_DIR)


if __name__ == "__main__":
    main()
