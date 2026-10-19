"""Phase 8 - shared helpers: folds that use only train + validation data, XGBoost construction with a free objective, ensemble scoring at tree-count checkpoints.

Folds (all targets are scored the same way as in Phase 7):
    three rolling-origin folds inside the train split (cut-offs 2016-12, 2017-12, 2018-12, scoring the next 12 target months), and
    the validation split (train on the whole train split, score 2022-03 to 2022-12) as the fourth, most recent fold.
The test split is never loaded by anything in this module.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402

CUTOFFS = {"2016-12": 71, "2017-12": 83, "2018-12": 95}
TRAIN_END = 133
CHECKPOINTS = [10, 20, 30, 40, 50, 60, 80, 100, 125, 150, 200, 250, 300, 400, 500, 600]
BASE_FIXED = dict(tree_method="hist", grow_policy="lossguide", max_depth=0, verbosity=0)
INT_KEYS = ("max_leaves", "min_child_weight", "max_bin")


def columns(k):
    sk = ld.spec()[k]
    ids = ["split", "Series_ID", "sector", "origin_idx", "target_idx", "origin_date", "target_date", "horizon", "shock_EV", "shock_S", "target_in_shock_EV", "target_in_shock_S"]
    return ids + sorted((set(sk["features"]) | {f"{sk['base']}_{k}", f"target_{k}", f"last_{k}", f"{k}_sf_shift", f"{k}_yadrift_h"}) - set(ids))


def model_params(cfg):
    """cfg may hold: the searched XGBoost parameters, objective ('squarederror'|'pseudohuber'|'absoluteerror'), huber_slope, recency_halflife (months, 0 = off)."""
    p = {k: v for k, v in cfg.items() if k not in ("objective", "huber_slope", "recency_halflife", "n_trees")}
    obj = cfg.get("objective", "squarederror")
    p["objective"] = {"squarederror": "reg:squarederror", "pseudohuber": "reg:pseudohubererror", "absoluteerror": "reg:absoluteerror"}[obj]
    if obj == "pseudohuber":
        p["huber_slope"] = float(cfg["huber_slope"])
    for k in INT_KEYS:
        if k in p:
            p[k] = int(p[k])
    return p


def make_model(cfg, n_trees, jobs, seed):
    return xgb.XGBRegressor(**BASE_FIXED, **model_params(cfg), n_estimators=int(n_trees), n_jobs=jobs, random_state=int(seed))


def recency_weights(target_idx, end_idx, halflife):
    if not halflife:
        return None
    return 0.5 ** ((end_idx - np.asarray(target_idx)) / float(halflife))


def build_folds(k, train_df, val_df):
    """List of fold dicts.  Preprocessing is fitted on each fold's own training rows."""
    sk = ld.spec()[k]
    specs = [(name, c, train_df[train_df.target_idx <= c], train_df[(train_df.origin_idx >= c) & (train_df.target_idx > c) & (train_df.target_idx <= c + 12)], True)
             for name, c in CUTOFFS.items()]
    specs.append(("validation", TRAIN_END, train_df, val_df, k != "S"))
    folds = []
    for name, c, trn, vl, mask in specs:
        tr = ld.train_rows(trn, k, sk)
        va = ld.eval_rows(vl, k, mask_shock=mask)
        X, y = ld.xy(tr, k, sk)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        Xv, _ = ld.xy(va, k, sk)
        folds.append(dict(name=name, end=c, X=pre.transform(X), y=y, tidx=tr.target_idx.to_numpy(), Xv=pre.transform(Xv), va=va,
                          base_v=ld.base_log(va, k, sk), act=va[f"target_{k}"].to_numpy()))
    return folds


def fold_curve(cfg, fold, n_max, jobs, seeds):
    """Seed-averaged predictions at every checkpoint <= n_max.  Returns {n: mean-horizon WAPE}."""
    pts = [n for n in CHECKPOINTS if n <= n_max]
    w = recency_weights(fold["tidx"], fold["end"], cfg.get("recency_halflife", 0))
    preds = {n: [] for n in pts}
    for sd in seeds:
        m = make_model(cfg, n_max, jobs, sd).fit(fold["X"], fold["y"], sample_weight=w)
        for n in pts:
            preds[n].append(m.predict(fold["Xv"], iteration_range=(0, n)))
    return {n: ld.mean_horizon_wape(fold["va"], fold["act"], fold["base_v"] + np.mean(p, axis=0))[0] for n, p in preds.items()}


def fit_ensemble(cfg, n_trees, X, y, tidx, end_idx, jobs, seeds):
    w = recency_weights(tidx, end_idx, cfg.get("recency_halflife", 0))
    return [make_model(cfg, n_trees, jobs, sd).fit(X, y, sample_weight=w) for sd in seeds]


def predict_ensemble(models, X):
    return np.mean([m.predict(X) for m in models], axis=0)


def incumbent_config(k):
    """The Phase 7 (xgboost_v1) configuration of target k as a Phase 8 cfg."""
    import json
    p = json.load(open(ROOT / "models" / "xgboost_v1" / "params.json"))[k]["xgboost_params"]
    keep = ("learning_rate", "max_leaves", "min_child_weight", "reg_lambda", "reg_alpha", "gamma", "subsample", "colsample_bytree", "colsample_bynode", "max_bin")
    cfg = {a: p[a] for a in keep}
    cfg.update(objective="squarederror", recency_halflife=0)
    return cfg, int(p["n_estimators"])
