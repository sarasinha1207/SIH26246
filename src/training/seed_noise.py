#!/usr/bin/env python3
"""
Phase 7 - how much does one fit move with the random seed or the thread count?  For the final configuration of each target: 8 single-model fits with
different seeds (4 threads) and fits with 1, 4 and all threads (seed 42), scored on the validation split.  The spread is why the saved model is an
average of five seeds and why differences below about 2% between single-fit validation scores are treated as ties.
Output: reports/training/seed_noise.json.   Run: python src/training/seed_noise.py
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
    params = json.load(open(ROOT / "models" / "xgboost_v1" / "params.json"))
    for k in "EVS":
        cfg = {a: params[k]["xgboost_params"][a] for a in tune.SPACE}
        n = params[k]["xgboost_params"]["n_estimators"]
        cols = columns(k, spec[k])
        tr = ld.train_rows(sp.load_split("train", columns=cols), k)
        va = ld.eval_rows(sp.load_split("validation", columns=cols), k, mask_shock=(k != "S"))
        X, y = ld.xy(tr, k)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        Xt, Xv = pre.transform(X), pre.transform(ld.xy(va, k)[0])
        act, base = va[f"target_{k}"].to_numpy(), ld.base_log(va, k)

        def score(models):
            return ld.mean_horizon_wape(va, act, base + tune.predict_bag(models, Xv))[0]
        by_seed = [score(tune.fit_bag(cfg, n, Xt, y, 4, (sd,))) for sd in range(1, 9)]
        by_threads = {str(j): score(tune.fit_bag(cfg, n, Xt, y, j, (42,))) for j in (1, 4, -1)}
        res[k] = {"single_fit_wape_by_seed": by_seed, "seed_min": min(by_seed), "seed_max": max(by_seed), "seed_std": float(np.std(by_seed)),
                  "seed_std_pct_of_mean": float(100 * np.std(by_seed) / np.mean(by_seed)), "single_fit_wape_by_threads_seed42": by_threads}
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in res[k].items() if a != "single_fit_wape_by_seed"}, flush=True)
    json.dump(res, open(REPORT / "seed_noise.json", "w"), indent=1)


if __name__ == "__main__":
    main()
