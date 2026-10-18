#!/usr/bin/env python3
"""
Phase 6 - coarse hyper-parameter exploration (random search, 24 configurations + the default) on the three validation folds, for LightGBM,
scikit-learn's HistGradientBoosting and XGBoost, with the same budget so the three are compared fairly.

The aim is to set sensible ranges and see how much tuning matters, not to produce the final model (Phase 8 does the final nested tuning).
Scores: WAPE on counts, mean over folds F1-F3, horizons 1/3/6/12.  Output: reports/models/tune_<family>.csv, tune_<family>_summary.json   (family = lightgbm | hist_gbm | xgboost)
Run: python src/models/tune_lightgbm.py [lightgbm|hist_gbm|xgboost]
"""
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "features"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
import model_zoo as zoo  # noqa: E402

FOLDS = {"F1_2018": "2017-12-01", "F2_2019": "2018-12-01", "F3_2024": "2023-12-01"}
HORIZONS = (1, 3, 6, 12)
N_CONFIG = 24
FAMILY = sys.argv[1] if len(sys.argv) > 1 else "lightgbm"
SPACES = {"lightgbm": dict(num_leaves=[15, 31, 63, 127], learning_rate=[0.03, 0.05, 0.08], n_estimators=[200, 400, 700], min_child_samples=[30, 100, 300],
                           feature_fraction=[0.5, 0.7, 0.9], lambda_l2=[0.0, 5.0, 20.0], bagging_fraction=[0.7, 0.9]),
          "hist_gbm": dict(max_leaf_nodes=[15, 31, 63, 127], learning_rate=[0.03, 0.05, 0.08], max_iter=[200, 400, 700], min_samples_leaf=[30, 100, 300],
                           max_features=[0.5, 0.7, 0.9], l2_regularization=[0.0, 5.0, 20.0]),
          "xgboost": dict(max_leaves=[15, 31, 63, 127], learning_rate=[0.03, 0.05, 0.08], n_estimators=[200, 400, 700], min_child_weight=[30, 100, 300],
                          colsample_bytree=[0.5, 0.7, 0.9], reg_lambda=[0.0, 5.0, 20.0], subsample=[0.7, 0.9])}
SPACE = SPACES[FAMILY]
HGB_DEFAULT = dict(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=100, l2_regularization=5.0, max_features=1.0, random_state=42)


def make(cfg):
    if FAMILY == "lightgbm":
        return lgb.LGBMRegressor(**cfg)
    if FAMILY == "xgboost":
        import xgboost as xgb
        return xgb.XGBRegressor(**cfg)
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(**cfg)


def main():
    rng = np.random.default_rng(7)
    base_cfg = {"lightgbm": zoo.LGB_DEFAULT, "hist_gbm": HGB_DEFAULT, "xgboost": zoo.XGB_DEFAULT}[FAMILY]
    base_cfg = dict(base_cfg)
    configs = [dict(base_cfg)]
    for _ in range(N_CONFIG):
        c = dict(base_cfg)
        c.update({k: v[rng.integers(len(v))] for k, v in SPACE.items()})
        configs.append(c)
    spec = pl.spec()
    data = {}
    for k in "EVS":
        for fold, te in FOLDS.items():
            X, y, w, meta = pl.training_frame(k, te)
            kt = meta.horizon.isin(HORIZONS).to_numpy()
            Xv, yv, _, mv = pl.validation_frame(k, te, 12)
            kv = mv.horizon.isin(HORIZONS).to_numpy()
            data[(k, fold)] = (X[kt], y[kt], Xv[kv], mv[kv])
    rows, t0 = [], time.time()
    for ci, cfg in enumerate(configs):
        for k in "EVS":
            sp = spec[k]
            sc = []
            for fold in FOLDS:
                X, y, Xv, mv = data[(k, fold)]
                m = make(cfg).fit(X, y)
                p = np.exp(mv[f"{sp['base']}_{k}"].to_numpy() + m.predict(Xv))
                a = np.exp(mv[f"target_{k}"].to_numpy())
                sc.append(100 * np.abs(a - p).sum() / a.sum())
            rows.append(dict(config=ci, target=k, mean_wape=float(np.mean(sc)), f1=sc[0], f2=sc[1], f3=sc[2],
                             **{c: cfg[c] for c in SPACE}))
        print(f"[{time.time() - t0:6.0f}s] config {ci} done", flush=True)
    df = pd.DataFrame(rows)
    df.round(3).to_csv(ROOT / "reports" / "models" / f"tune_{FAMILY}.csv", index=False)
    summ = {}
    for k in "EVS":
        d = df[df.target == k].sort_values("mean_wape")
        default = float(d[d.config == 0].mean_wape.iloc[0])
        summ[k] = dict(default_mean_wape=round(default, 3), best_mean_wape=round(float(d.mean_wape.iloc[0]), 3),
                       gain_pct=round(100 * (1 - float(d.mean_wape.iloc[0]) / default), 2), median_config_wape=round(float(d.mean_wape.median()), 3),
                       worst_config_wape=round(float(d.mean_wape.max()), 3), best_config={c: (d.iloc[0][c].item() if hasattr(d.iloc[0][c], "item") else d.iloc[0][c]) for c in SPACE},
                       top5_param_ranges={c: sorted({(x.item() if hasattr(x, "item") else x) for x in d.head(5)[c]}) for c in SPACE})
    json.dump(summ, open(ROOT / "reports" / "models" / f"tune_{FAMILY}_summary.json", "w"), indent=2)
    print(json.dumps({k: {x: v[x] for x in ("default_mean_wape", "best_mean_wape", "gain_pct")} for k, v in summ.items()}, indent=1))


if __name__ == "__main__":
    main()
