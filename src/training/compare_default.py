#!/usr/bin/env python3
"""
Phase 7 - what did tuning buy?  Fits the Phase 6 default configuration (250 trees, learning rate 0.08, 31 leaves, min_child_weight 100, lambda 5,
80% row and column sampling) as the same 5-seed ensemble on the train split and scores it on the validation split next to the tuned model.
Output: reports/training/default_vs_tuned.json.   Run after train.py: python src/training/compare_default.py
"""
import json
import sys
from pathlib import Path

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
    metrics = json.load(open(REPORT / "validation_metrics.json"))
    cfg = dict(tune.PHASE6_DEFAULT)
    for k in "EVS":
        cols = columns(k, spec[k])
        tr = ld.train_rows(sp.load_split("train", columns=cols), k)
        va = ld.eval_rows(sp.load_split("validation", columns=cols), k, mask_shock=(k != "S"))
        X, y = ld.xy(tr, k)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        models = tune.fit_bag(cfg, 250, pre.transform(X), y, jobs=-1)
        pred = ld.base_log(va, k) + tune.predict_bag(models, pre.transform(ld.xy(va, k)[0]))
        w = ld.mean_horizon_wape(va, va[f"target_{k}"].to_numpy(), pred)[0]
        res[k] = {"phase6_default_validation_wape": w, "tuned_validation_wape": metrics[k]["validation_wape_mean_horizon"]}
        print(k, res[k], flush=True)
    json.dump(res, open(REPORT / "default_vs_tuned.json", "w"), indent=1)


if __name__ == "__main__":
    main()
