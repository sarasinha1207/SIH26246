#!/usr/bin/env python3
"""
Phase 6 - compare model families on the Phase 5 inputs (train + validation periods only; the test period is locked).

Folds (same as Phase 5): F1 train targets <= 2017-12 / validate 2018, F2 <= 2018-12 / 2019, F3 <= 2023-12 / 2024.  Horizons 1, 3, 6, 12.
Each model sees the selected features, base and training policy from data/processed/features/feature_sets.json.
Outputs: data/interim/phase6_predictions.parquet (one row per model x fold x validation example), reports/models/compare_timings.csv

Run: python src/models/compare_models.py [--models lightgbm,ridge,...]
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "features"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
import model_zoo as zoo  # noqa: E402

FOLDS = {"F1_2018": "2017-12-01", "F2_2019": "2018-12-01", "F3_2024": "2023-12-01"}
HORIZONS = (1, 3, 6, 12)
ALL = zoo.BASELINES + ["holt_winters", "lightgbm", "lightgbm_per_horizon", "hist_gbm", "xgboost", "ridge", "mlp", "random_forest"]
OUT_PRED = ROOT / "data" / "interim" / "phase6_predictions.parquet"
OUT_TIME = ROOT / "reports" / "models" / "compare_timings.csv"


def main():
    wanted = ALL
    if "--models" in sys.argv:
        wanted = sys.argv[sys.argv.index("--models") + 1].split(",")
    D, ex = pl._examples()
    spec = pl.spec()
    shock = {"E": D.covid | D.policy, "V": D.covid | D.policy, "S": D.covid | D.policy | D.ramp}
    recs, times = [], []
    t_start = time.time()
    for k in "EVS":
        sp = spec[k]
        for fold, te in FOLDS.items():
            X, y, w, meta = pl.training_frame(k, te)
            keep = meta.horizon.isin(HORIZONS).to_numpy()
            X, y, meta = X[keep], y[keep], meta[keep]
            Xv, yv, _, mv = pl.validation_frame(k, te, 12)
            kv = mv.horizon.isin(HORIZONS).to_numpy()
            Xv, yv, mv = Xv[kv], yv[kv], mv[kv]
            base_v = mv[f"{sp['base']}_{k}"].to_numpy()
            actual = mv[f"target_{k}"].to_numpy()
            exv = ex.loc[mv.index]
            te_idx = int(np.where(D.dates == pd.Timestamp(te))[0][0])
            common = dict(target=k, fold=fold, row=mv.index.to_numpy(), horizon=mv.horizon.to_numpy(), series=mv.Series_ID.to_numpy(),
                          actual_log=actual)
            for name in wanted:
                t0 = time.time()
                if name in zoo.BASELINES:
                    pred = zoo.baseline_log_level(exv, k, name)
                elif name == "holt_winters":
                    rows = exv[["series_row", "origin_idx", "horizon"]]
                    pred = zoo.HoltWinters().fit_predict(D.L[k], D.sector, shock[k], te_idx, rows)
                else:
                    m = zoo.make_model(name).fit(X, y, w)
                    pred = base_v + m.predict(Xv)
                recs.append(pd.DataFrame(dict(model=name, pred_log=pred, **common)))
                times.append(dict(target=k, fold=fold, model=name, seconds=time.time() - t0, n_train=len(X), n_valid=len(Xv)))
                print(f"[{time.time() - t_start:6.0f}s] {k} {fold} {name} done ({times[-1]['seconds']:.1f}s)", flush=True)
    new = pd.concat(recs, ignore_index=True)
    if OUT_PRED.exists() and "--models" in sys.argv:
        old = pd.read_parquet(OUT_PRED)
        old = old[~old.model.isin(new.model.unique())]
        new = pd.concat([old, new], ignore_index=True)
    OUT_PRED.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(OUT_PRED, index=False)
    t = pd.DataFrame(times)
    if OUT_TIME.exists() and "--models" in sys.argv:
        o = pd.read_csv(OUT_TIME)
        t = pd.concat([o[~o.model.isin(t.model.unique())], t], ignore_index=True)
    t.round(2).to_csv(OUT_TIME, index=False)
    print("saved", OUT_PRED, new.shape)


if __name__ == "__main__":
    main()
