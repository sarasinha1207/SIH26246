#!/usr/bin/env python3
"""
Phase 7 - hyper-parameter search for the XGBoost model of one target, with rolling-origin (expanding-window) validation inside the TRAIN split.

Folds (cut-off = last month of the fold's training targets; the fold is scored on rows whose targets fall in the next 12 months and whose origin is on or
after the cut-off, shock months excluded): 2016-12 / 2017, 2017-12 / 2018, 2018-12 / 2019.  The validation split is not used for the search.
Preprocessing is re-fitted on each fold's training rows.

Round 1: random search over the regularisation space (+ the Phase 6 default as reference).  Round 2: local search around the three best round-1 configs.
For each config one model is grown to n_max trees and scored at checkpoints (10, 20, ... up to n_max), so the number of trees is tuned too (this is the
early-stopping rule: the checkpoint with the lowest mean-fold WAPE).  Score = WAPE on counts, mean over horizons 1-12, mean over folds.

Final stage (also runnable alone with --final-only): configs within 1% of the best cross-validation score (at most 5) are refitted on the whole train split and scored once on the validation split;
for employed workers and vacancies the best of them on validation is kept (each is scored as a 5-seed averaged ensemble, because a single fit moves by about 2% with the seed or thread count), for seekers the best by cross-validation is kept (the whole validation window
lies inside the e-Shram registration ramp, so it says little about model skill).

Run: python src/training/tune.py E|V|S [--jobs 4] [--random 28] [--local 14]
Writes reports/training/tune_<k>_trials.csv and tune_<k>_best.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402

OUT = ROOT / "reports" / "training"
CUTOFFS = {"2016-12": 71, "2017-12": 83, "2018-12": 95}                  # month index since 2011-01
N_MAX = {0.01: 600, 0.02: 400, 0.03: 300, 0.05: 200, 0.08: 150}
CHECKPOINTS = [10, 20, 30, 40, 50, 60, 80, 100, 125, 150, 200, 250, 300, 400, 500, 600]
SPACE = dict(learning_rate=[0.01, 0.02, 0.03, 0.05, 0.08], max_leaves=[7, 15, 31, 63], min_child_weight=[50, 100, 200, 400, 800], reg_lambda=[1.0, 5.0, 20.0, 50.0, 200.0],
             reg_alpha=[0.0, 0.01, 0.1, 1.0], gamma=[0.0, 0.001, 0.01, 0.05], subsample=[0.5, 0.7, 0.9], colsample_bytree=[0.4, 0.6, 0.8, 1.0],
             colsample_bynode=[0.6, 0.8, 1.0], max_bin=[64, 128, 256])
FIXED = dict(tree_method="hist", grow_policy="lossguide", max_depth=0, random_state=42, verbosity=0, objective="reg:squarederror")
PHASE6_DEFAULT = dict(learning_rate=0.08, max_leaves=31, min_child_weight=100, reg_lambda=5.0, reg_alpha=0.0, gamma=0.0, subsample=0.8, colsample_bytree=0.8,
                      colsample_bynode=1.0, max_bin=256)       # Phase 6 setting; it used 250 trees


def make_model(cfg, n_trees, jobs):
    p = {k: v for k, v in cfg.items() if k not in ("n_trees",)}
    return xgb.XGBRegressor(**FIXED, **p, n_estimators=n_trees, n_jobs=jobs)


SEEDS = (42, 43, 44, 45, 46)


def fit_bag(cfg, n_trees, X, y, jobs, seeds=SEEDS):
    """Seed-averaged ensemble: the same configuration fitted with several random seeds (row / column sampling differs), predictions averaged."""
    models = []
    for sd in seeds:
        m = make_model(cfg, n_trees, jobs)
        m.set_params(random_state=sd)
        models.append(m.fit(X, y))
    return models


def predict_bag(models, X):
    return np.mean([m.predict(X) for m in models], axis=0)


def build_folds(df, k):
    folds = []
    for name, c in CUTOFFS.items():
        tr = ld.train_rows(df[df.target_idx <= c], k)
        va = df[(df.origin_idx >= c) & (df.target_idx > c) & (df.target_idx <= c + 12)]
        va = ld.eval_rows(va, k)
        X, y = ld.xy(tr, k)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
        Xv, yv = ld.xy(va, k)
        folds.append(dict(name=name, X=pre.transform(X), y=y, Xv=pre.transform(Xv), va=va, base_v=ld.base_log(va, k), act=va[f"target_{k}"].to_numpy()))
    return folds


def score_config(cfg, folds, jobs, k):
    lr = cfg["learning_rate"]
    n_max = N_MAX[lr]
    pts = [n for n in CHECKPOINTS if n <= n_max]
    per = {n: [] for n in pts}
    for f in folds:
        m = make_model(cfg, n_max, jobs).fit(f["X"], f["y"])
        for n in pts:
            pred = f["base_v"] + m.predict(f["Xv"], iteration_range=(0, n))
            per[n].append(ld.mean_horizon_wape(f["va"], f["act"], pred)[0])
    mean = {n: float(np.mean(v)) for n, v in per.items()}
    best_n = min(mean, key=mean.get)
    return best_n, mean[best_n], per[best_n], mean


def local_variants(cfg, rng, n):
    """Neighbouring values on the grid for 1-3 parameters of `cfg`."""
    out = []
    keys = list(SPACE)
    for _ in range(n):
        c = dict(cfg)
        for key in rng.choice(keys, size=int(rng.integers(1, 4)), replace=False):
            grid = SPACE[key]
            i = grid.index(c[key])
            c[key] = grid[int(np.clip(i + rng.choice([-1, 1]), 0, len(grid) - 1))]
        out.append(c)
    return out


def recent_stage(k, df, spec, cols, jobs, n_candidates=12, seeds=SEEDS[:3]):
    """Stage 2.  Stage 1 chose by three pre-COVID folds only (2017-2019).  Here the best `n_candidates` configs by cross-validation, the Phase 6 default at its
    cross-validated tree count and the default at 250 trees (its Phase 6 setting) are also scored on the validation split (post-COVID, the most recent data),
    which acts as a fourth rolling-origin fold.  Each fold's WAPE is divided by the same fold's WAPE for the Phase 6 default (250 trees), and the four ratios are
    averaged: below 1 means better than the default across eras.  The lowest average wins.  Seekers: the validation fold lies in the e-Shram ramp (unmasked), so
    it carries a quarter of the weight for a one-off structural change; it is reported separately in the model card."""
    t0 = time.time()
    T = pd.read_csv(OUT / f"tune_{k}_trials.csv")
    fold_cols = [f"fold_{n}" for n in CUTOFFS]
    int_keys = ("max_leaves", "min_child_weight", "max_bin")
    cand = []
    for _, r in T.nsmallest(n_candidates, "cv_wape").iterrows():
        cand.append(dict(name=f"trial {int(r.trial)}", cfg={c: (int(r[c]) if c in int_keys else float(r[c])) for c in SPACE}, trees=int(r.best_trees), cv_folds=[float(r[c]) for c in fold_cols]))
    d = T.iloc[0]
    default_cfg = {c: (int(d[c]) if c in int_keys else float(d[c])) for c in SPACE}
    folds = build_folds(df, k)
    cand.append(dict(name="phase 6 default, CV trees", cfg=default_cfg, trees=int(d.best_trees), cv_folds=[float(d[c]) for c in fold_cols]))
    sc = [ld.mean_horizon_wape(f["va"], f["act"], f["base_v"] + predict_bag(fit_bag(default_cfg, 250, f["X"], f["y"], jobs, seeds[:1]), f["Xv"]))[0] for f in folds]
    cand.append(dict(name="phase 6 default, 250 trees", cfg=default_cfg, trees=250, cv_folds=sc))
    tr = ld.train_rows(df, k)
    X, y = ld.xy(tr, k)
    pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
    Xt = pre.transform(X)
    dvs = ld.eval_rows(sp.load_split("validation", columns=cols), k, mask_shock=(k != "S"))
    Xv = pre.transform(ld.xy(dvs, k)[0])
    act, base_v = dvs[f"target_{k}"].to_numpy(), ld.base_log(dvs, k)
    for c in cand:
        c["val"] = ld.mean_horizon_wape(dvs, act, base_v + predict_bag(fit_bag(c["cfg"], c["trees"], Xt, y, jobs, seeds), Xv))[0]
        print(f"[{k} {time.time() - t0:5.0f}s] {c['name']:27s} trees {c['trees']:3d}  cv {np.mean(c['cv_folds']):.4f}  validation {c['val']:.4f}", flush=True)
    ref = cand[-1]
    ref_folds = list(ref["cv_folds"]) + [ref["val"]]
    for c in cand:
        folds4 = list(c["cv_folds"]) + [c["val"]]
        c["ratios"] = [a / b for a, b in zip(folds4, ref_folds)]
        c["score"] = float(np.mean(c["ratios"]))
    pick = min(cand, key=lambda c: c["score"])
    out = dict(target=k, selection_rule="lowest mean of fold WAPE / Phase 6 default (250 trees) fold WAPE over four rolling-origin folds: 2016-12, 2017-12, 2018-12 and the validation split",
               candidates=cand, seeds_for_validation=list(seeds),
               chosen=dict(name=pick["name"], cfg=pick["cfg"], best_trees=pick["trees"], cv_wape=float(np.mean(pick["cv_folds"])), val_wape=pick["val"], relative_score=pick["score"]),
               seconds=round(time.time() - t0))
    json.dump(out, open(OUT / f"tune_{k}_best.json", "w"), indent=1, default=float)
    print(f"[{k}] chosen: {pick['name']}  score {pick['score']:.4f} (default 250 trees = 1.0000)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=list("EVS"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--random", type=int, default=40)
    ap.add_argument("--local", type=int, default=18)
    ap.add_argument("--final-only", action="store_true", help="skip the search; redo the shortlist stage from the saved trials csv")
    ap.add_argument("--recent", action="store_true", help="stage 2: re-rank the best configs with the validation split as a fourth, most recent fold")
    a = ap.parse_args()
    k, jobs = a.target, a.jobs
    OUT.mkdir(parents=True, exist_ok=True)
    spec = ld.spec()[k]
    ids = ["split", "Series_ID", "origin_idx", "target_idx", "horizon", "shock_EV", "shock_S", "target_in_shock_EV", "target_in_shock_S"]
    cols = ids + sorted((set(spec["features"]) | {f"{spec['base']}_{k}", f"target_{k}", f"last_{k}", f"{k}_sf_shift"}) - set(ids))
    df = sp.load_split("train", columns=cols)
    if a.recent:
        return recent_stage(k, df, spec, cols, jobs)
    rng = np.random.default_rng(100 + "EVS".index(k))
    trials, t0 = [], time.time()
    folds = [] if a.final_only else build_folds(df, k)
    if folds:
        print(f"[{k}] folds: " + ", ".join(f"{f['name']} train {len(f['X']):,} / score {len(f['Xv']):,}" for f in folds), flush=True)

    def run(cfg, rnd):
        n, s, folds_s, curve = score_config(cfg, folds, jobs, k)
        row = dict(trial=len(trials), round=rnd, best_trees=n, cv_wape=s, **{f"fold_{f['name']}": v for f, v in zip(folds, folds_s)}, **cfg)
        trials.append(row)
        print(f"[{k} {time.time() - t0:6.0f}s] trial {row['trial']:2d} ({rnd}) trees {n:3d}  cv WAPE {s:.4f}  " + " ".join(f"{c}={cfg[c]}" for c in ("learning_rate", "max_leaves", "min_child_weight", "reg_lambda")), flush=True)
        pd.DataFrame(trials).to_csv(OUT / f"tune_{k}_trials.csv", index=False)
        return row

    if a.final_only:
        trials = pd.read_csv(OUT / f"tune_{k}_trials.csv").to_dict("records")
    else:
        run({kk: v for kk, v in PHASE6_DEFAULT.items() if kk != "n_trees"}, "phase6_default")
        for _ in range(a.random):
            run({key: grid[int(rng.integers(len(grid)))] for key, grid in SPACE.items()}, "random")
        T = pd.DataFrame(trials)
        top = T[T["round"] != "local"].nsmallest(3, "cv_wape")
        for _, r in top.iterrows():
            base = {key: SPACE[key][int(np.argmin([abs(g - r[key]) for g in SPACE[key]]))] for key in SPACE}
            for c in local_variants(base, rng, max(1, a.local // 3)):
                run(c, "local")
    T = pd.DataFrame(trials)
    # ---- shortlist -> refit on the full train split -> one look at the validation split
    best = T.cv_wape.min()
    short = T[T.cv_wape <= best * 1.01].sort_values("cv_wape").head(5)
    tr = ld.train_rows(df, k)
    X, y = ld.xy(tr, k)
    pre = FeaturePreprocessor(X.columns).fit(X, tr["split"])
    Xt = pre.transform(X)
    dv = sp.load_split("validation", columns=cols)
    dvs = ld.eval_rows(dv, k, mask_shock=(k != "S"))
    Xv = pre.transform(ld.xy(dvs, k)[0])
    act, base_v = dvs[f"target_{k}"].to_numpy(), ld.base_log(dvs, k)
    bl = ld.baseline_log(dvs, k)
    base_score = ld.mean_horizon_wape(dvs, act, bl)[0]
    rows = []
    for _, r in short.iterrows():
        cfg = {key: r[key] for key in SPACE}
        for key in ("max_leaves", "min_child_weight", "max_bin"):
            cfg[key] = int(cfg[key])
        s = ld.mean_horizon_wape(dvs, act, base_v + predict_bag(fit_bag(cfg, int(r.best_trees), Xt, y, jobs), Xv))[0]
        rows.append(dict(trial=int(r.trial), cv_wape=float(r.cv_wape), best_trees=int(r.best_trees), val_wape=float(s), val_baseline_wape=float(base_score), cfg=cfg))
        print(f"[{k}] shortlist trial {int(r.trial)}: cv {r.cv_wape:.4f}  validation {s:.4f}  (baseline {base_score:.4f})", flush=True)
    pick = min(rows, key=lambda x: x["cv_wape"]) if k == "S" else min(rows, key=lambda x: x["val_wape"])
    out = dict(target=k, selection_rule=("lowest cross-validation WAPE" if k == "S" else "lowest validation WAPE among configs within 1% of the best cross-validation WAPE"),
               folds=list(CUTOFFS), search={"random": a.random, "local": a.local, "total_trials": len(T)}, chosen=pick, shortlist=rows,
               phase6_default=T.iloc[0][["cv_wape", "best_trees"]].to_dict(), best_cv=float(best), seconds=round(time.time() - t0))
    json.dump(out, open(OUT / f"tune_{k}_best.json", "w"), indent=1, default=float)
    print(f"[{k}] chosen trial {pick['trial']}: cv {pick['cv_wape']:.4f}, validation {pick['val_wape']:.4f}; Phase 6 default cv {T.iloc[0].cv_wape:.4f}", flush=True)


if __name__ == "__main__":
    main()
