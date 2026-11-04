#!/usr/bin/env python3
"""
v4 phase 5 - out-of-sample predictions of the phase 4 models, saved for the intervals and flags.

For each window (validation, test, stress) the cached seed ensembles of phase 4 (models/v4/<window>/, fitted only on targets before the window) forecast every
(origin, horizon) pair of the window for all 7,925 series.  Nothing is refitted and nothing is tuned.  Writes data/v4/interim/predictions_<window>.parquet (git-ignored):
one row per (series, origin, horizon) with, for E, V and S, the predicted and actual log change, the log level at the origin and the 12-month volatility feature.

Run: python src/v4/predictions.py [validation test stress]
"""
import json
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import evaluate as EV
import model_lib as M
import splits as SP

OUT = C.DATA / "interim"


def load_boosters(window, k):
    files = sorted((C.MODELS / window).glob(f"{k}_seed*_*.json"))
    tags = {f.stem.split("_")[-1] for f in files}
    assert len(files) == len(EV.SEEDS) and len(tags) == 1, f"{window} {k}: expected one set of {len(EV.SEEDS)} seed models, found {[f.name for f in files]}"
    out = []
    for f in files:
        b = xgb.Booster()
        b.load_model(str(f))
        out.append(b)
    return out


def main(windows):
    OUT.mkdir(parents=True, exist_ok=True)
    best = json.loads((EV.OUT / "best_params.json").read_text(encoding="utf-8"))
    D, OF, SF = M.load_world()
    for w in windows:
        t0 = time.time()
        et, eh = SP.eval_pairs(w, unlock=True)
        Xe, me = M.build(D, OF, SF, et, eh)
        de = M.ddata(Xe)
        df = pd.DataFrame({"series_row": me.series_row.to_numpy(), "origin_idx": me.origin_idx.to_numpy(), "horizon": me.horizon.to_numpy(),
                           "shock_EV": me.shock_EV.to_numpy(), "shock_S": me.shock_S.to_numpy()})
        for k in "EVS":
            df[f"pred_{k}"] = EV.predict_by_horizon(load_boosters(w, k), de, me.horizon.to_numpy(), best[k]["trees_by_band"]).astype(np.float32)
            df[f"act_{k}"] = M.target(D, me, k).astype(np.float32)
            df[f"base_{k}"] = M.base_log(D, me, k).astype(np.float32)
            df[f"vol_{k}"] = Xe[f"{k}_vol12"].to_numpy().astype(np.float32)
        df.to_parquet(OUT / f"predictions_{w}.parquet", index=False)
        print(f"{w}: {len(df):,} rows ({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["validation", "test", "stress"])
