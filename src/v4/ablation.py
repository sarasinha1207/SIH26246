#!/usr/bin/env python3
"""
v4 phase 4 - which inputs help on the validation window?  Fits on the training window (targets 2000-2009) and scores validation (targets 2010-2014) for four input sets
with fixed settings.  Writes reports/v4/evaluation/ablation_validation.csv.   Run: python src/v4/ablation.py   (about 15 minutes)

    all_candidates   every candidate feature except the time proxies (group aggregates and all identities included)
    no_groups        without the sector / trade / state-sector growth aggregates
    chosen           no_groups and without cat_district and cat_tier (the inputs the models use)
    no_identity      no_groups and no identity columns at all
"""
import time

import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import model_lib as M
import splits as SP

SETS = ["all_candidates", "no_groups", "chosen", "no_identity"]
PARAMS = dict(M.BASE_PARAMS, max_depth=4, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=50)
ROUNDS = (30, 100, 250)


def main():
    out_dir = C.REPORTS / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    D, OF, SF = M.load_world()
    t, h = SP.fit_pairs(SP.CUT["train"])
    Xf, mf = M.build(D, OF, SF, t, h, feature_set=None, rows=(0.3, 0))
    vt, vh = SP.eval_pairs("validation")
    Xv, mv = M.build(D, OF, SF, vt, vh, feature_set=None, rows=(0.3, 1))
    allcols = list(Xf.columns)
    rows = []
    for k in "EVS":
        y, yv, base = M.target(D, mf, k), M.target(D, mv, k), M.base_log(D, mv, k)
        for name, pr in M.baselines(Xv, mv, k).items():
            rows.append({"target": k, "inputs": f"baseline: {name}", "trees": 0, **M.band_wapes(pr, yv, base, mv.horizon.to_numpy())})
        for s in SETS:
            cols = M.input_columns(allcols, s)
            t0 = time.time()
            b = xgb.train(dict(PARAMS), M.dtrain(Xf[cols], y), max(ROUNDS))
            dv = M.ddata(Xv[cols])
            for n in ROUNDS:
                pr = b.predict(dv, iteration_range=(0, n))
                rows.append({"target": k, "inputs": s, "trees": n, "n_inputs": len(cols), **M.band_wapes(pr, yv, base, mv.horizon.to_numpy())})
            print(k, s, f"{time.time() - t0:.0f} s", flush=True)
    res = pd.DataFrame(rows)
    res["mean_band"] = res[M.BAND_LABELS].mean(axis=1)
    res.round(3).to_csv(out_dir / "ablation_validation.csv", index=False)
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
