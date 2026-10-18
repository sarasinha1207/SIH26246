#!/usr/bin/env python3
"""
Phase 7 - does the train-fitted scaling / imputation change what the trees learn?  Fits each target twice with the tuned configuration, once on raw
features and once on preprocessed features, and compares validation predictions.  Output: reports/training/preprocessing_check.json.
Run after tune.py: python src/training/check_preprocessing.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
import tune  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402
from train import columns  # noqa: E402

REPORT = ROOT / "reports" / "training"


def main():
    spec, res = ld.spec(), {}
    for k in "EVS":
        best = json.load(open(REPORT / f"tune_{k}_best.json"))["chosen"]
        cfg = {key: (int(v) if key in ("max_leaves", "min_child_weight", "max_bin") else float(v)) for key, v in best["cfg"].items()}
        n = int(best["best_trees"])
        cols = columns(k, spec[k])
        tr = ld.train_rows(sp.load_split("train", columns=cols), k)
        va = ld.eval_rows(sp.load_split("validation", columns=cols), k, mask_shock=(k != "S"))
        X, y = ld.xy(tr, k)
        Xv, _ = ld.xy(va, k)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        raw = tune.make_model(cfg, n, -1).fit(X, y).predict(Xv)
        scaled = tune.make_model(cfg, n, -1).fit(pre.transform(X), y).predict(pre.transform(Xv))
        act, base = va[f"target_{k}"].to_numpy(), ld.base_log(va, k)
        w_raw, w_sc = ld.mean_horizon_wape(va, act, base + raw)[0], ld.mean_horizon_wape(va, act, base + scaled)[0]
        res[k] = {"validation_wape_raw": w_raw, "validation_wape_preprocessed": w_sc, "difference_points": w_sc - w_raw,
                  "max_abs_prediction_difference_log": float(np.abs(raw - scaled).max()), "mean_abs_prediction_difference_log": float(np.abs(raw - scaled).mean()),
                  "missing_values_in_train_features": int(X.isna().sum().sum())}
        print(k, res[k], flush=True)
    json.dump(res, open(REPORT / "preprocessing_check.json", "w"), indent=1)


if __name__ == "__main__":
    main()
