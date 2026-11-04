#!/usr/bin/env python3
"""
v4 phase 4 - robustness on fresh simulated worlds.

The generator is run again with other seeds (same districts, trades and structure; new random district effects, shocks' noise and trade shares).  The models fitted
on targets to 2014 (the ones scored once on the test window) forecast the 2015-2019 window of each fresh world without being refitted or retuned.  If the
test score was a lucky draw of one world, it would not hold here.  Writes reports/v4/evaluation/fresh_worlds.csv.

Run after `evaluate.py test`:  python src/v4/fresh_worlds.py [seed ...]     (default seeds 101 202)
"""
import json
import sys

import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import evaluate as EV
import generate as G
import model_lib as M
import splits as SP

OUT = C.REPORTS / "evaluation"


def main(seeds):
    best = json.loads((OUT / "best_params.json").read_text(encoding="utf-8"))
    summ = json.loads((OUT / "test_summary.json").read_text(encoding="utf-8"))
    cat = pd.read_csv(C.DATA / "district_catalog.csv")
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    rows = []
    for seed in seeds:
        trade, _, dim_w = G.generate(cat, seed=seed)
        assert (dim_w.Series_ID == dim.Series_ID).all()
        D, OF, SF = M.load_world(trade, dim)
        et, eh = SP.eval_pairs("test", unlock=True)
        Xe, me = M.build(D, OF, SF, et, eh)
        assert list(Xe.columns) == summ["inputs"]
        de = M.ddata(Xe)
        for k in "EVS":
            boosters = []
            for name in summ[k]["models"]:
                b = xgb.Booster()
                b.load_model(str(C.MODELS / "test" / name))
                boosters.append(b)
            pr = EV.predict_by_horizon(boosters, de, me.horizon.to_numpy(), best[k]["trees_by_band"])
            ye, base = M.target(D, me, k), M.base_log(D, me, k)
            preds = {"model": pr, **M.baselines(Xe, me, k)}
            for lab, m in [("all horizons", np.ones(len(me), bool))] + [(b, M.band_of(me.horizon.to_numpy()) == b) for b in M.BAND_LABELS]:
                w = {nm: M.wape(p[m], ye[m], base[m]) for nm, p in preds.items()}
                best_b = min(w["naive"], w["seasonal_naive"], w["damped_trend"])
                rows.append({"world_seed": seed, "target": k, "band": lab, "rows": int(m.sum()), "wape_model": w["model"], "wape_best_baseline": best_b,
                             "improvement_vs_best_baseline_pct": (1 - w["model"] / best_b) * 100})
            print(seed, k, round(rows[-6]["wape_model"], 2), "vs best baseline", round(rows[-6]["wape_best_baseline"], 2), flush=True)
    pd.DataFrame(rows).round(4).to_csv(OUT / "fresh_worlds.csv", index=False)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [101, 202])
