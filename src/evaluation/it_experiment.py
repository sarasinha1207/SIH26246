#!/usr/bin/env python3
"""
Phase 8 - pre-test experiment for the IT-ITeS weak spot: would a model trained on IT-ITeS rows only beat the global model on IT-ITeS rows?

Uses only train + validation data (the three rolling-origin folds and the validation split).  Decision rule fixed in advance: adopt a sector-specific model only if it
lowers the IT-ITeS WAPE by at least 3% on the mean of the three rolling-origin folds AND on the validation fold.  Otherwise the global model stays.
Run after finalize.py:  python src/evaluation/it_experiment.py [E|V|S]   (default V).   Writes reports/evaluation/it_experiment_<k>.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import opt_lib as ol  # noqa: E402
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402

OUT = ROOT / "reports" / "evaluation"
SEEDS = (42, 43, 44)
SECTOR = "IT-ITeS"


def main():
    k = sys.argv[1] if len(sys.argv) > 1 else "V"
    fin = json.load(open(OUT / f"finalize_{k}.json"))["chosen"]
    cfg, n = fin["cfg"], fin["n_trees"]
    cols = ol.columns(k)
    tr_df, va_df = sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols)
    full = ol.build_folds(k, tr_df, va_df)
    only = ol.build_folds(k, tr_df[tr_df.sector == SECTOR], va_df[va_df.sector == SECTOR])
    res = {}
    for f_all, f_it in zip(full, only):
        pg = ol.predict_ensemble(ol.fit_ensemble(cfg, n, f_all["X"], f_all["y"], f_all["tidx"], f_all["end"], 4, SEEDS), f_all["Xv"])
        m = (f_all["va"]["sector"] == SECTOR).to_numpy()
        w_global = ld.mean_horizon_wape(f_all["va"][m], f_all["act"][m], (f_all["base_v"] + pg)[m])[0]
        ps = ol.predict_ensemble(ol.fit_ensemble(cfg, n, f_it["X"], f_it["y"], f_it["tidx"], f_it["end"], 4, SEEDS), f_it["Xv"])
        w_spec = ld.mean_horizon_wape(f_it["va"], f_it["act"], f_it["base_v"] + ps)[0]
        res[f_all["name"]] = dict(global_model=w_global, sector_model=w_spec, change_pct=100 * (w_spec / w_global - 1), rows=int(m.sum()))
        print(k, f_all["name"], res[f_all["name"]], flush=True)
    cv = np.mean([res[n_]["change_pct"] for n_ in res if n_ != "validation"])
    adopt = bool(cv <= -3 and res["validation"]["change_pct"] <= -3)
    out = dict(target=k, sector=SECTOR, folds=res, mean_cv_change_pct=float(cv), validation_change_pct=res["validation"]["change_pct"], adopt=adopt,
               rule="adopt only if the sector model is at least 3% better on the mean of the rolling-origin folds and on the validation split")
    json.dump(out, open(OUT / f"it_experiment_{k}.json", "w"), indent=1, default=float)
    print("adopt sector-specific model:", adopt)


if __name__ == "__main__":
    main()
