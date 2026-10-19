#!/usr/bin/env python3
"""
Phase 8 - Bayesian hyper-parameter search (Optuna TPE) for one target's XGBoost model, using only train + validation data.

Objective (minimise): the mean over four folds of  fold WAPE / the Phase 7 configuration's WAPE on that fold  (three rolling-origin folds in the train split + the
validation split).  1.00 = as good as Phase 7; 0.98 = 2% better.  The tree count is part of the trial: it is the checkpoint with the lowest four-fold score.
Search space: learning rate, leaves, min_child_weight, L2, L1, gamma, row/column sampling, bins, loss (squared error, pseudo-Huber, absolute error),
recency weighting half-life.  The Phase 7 configuration and the Phase 6 default are enqueued as the first two trials.
One seed per trial (noise is about 1%); finalize.py re-ranks the best trials with several seeds before anything is accepted.

Run: python src/evaluation/tune_optuna.py E|V|S [--jobs 4] [--trials 120] [--timeout 4200]
Writes reports/evaluation/optuna_<k>_trials.csv (study database optuna_<k>.db allows resuming).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import optuna

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import opt_lib as ol  # noqa: E402
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402

OUT = ROOT / "reports" / "evaluation"
PHASE6_DEFAULT = dict(learning_rate=0.08, max_leaves=31, min_child_weight=100, reg_lambda=5.0, reg_alpha=0.0, gamma=0.0, subsample=0.8, colsample_bytree=0.8,
                      colsample_bynode=1.0, max_bin=256, objective="squarederror", recency_halflife=0)


def suggest(trial):
    cfg = dict(learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True), max_leaves=trial.suggest_int("max_leaves", 4, 127, log=True),
               min_child_weight=trial.suggest_float("min_child_weight", 20, 1500, log=True), reg_lambda=trial.suggest_float("reg_lambda", 0.5, 500, log=True),
               reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 10, log=True), gamma=trial.suggest_float("gamma", 1e-4, 0.2, log=True),
               subsample=trial.suggest_float("subsample", 0.4, 1.0), colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 1.0),
               colsample_bynode=trial.suggest_float("colsample_bynode", 0.5, 1.0), max_bin=trial.suggest_categorical("max_bin", [64, 128, 256]),
               objective=trial.suggest_categorical("objective", ["squarederror", "pseudohuber", "absoluteerror"]),
               recency_halflife=trial.suggest_categorical("recency_halflife", [0, 24, 60]))
    if cfg["objective"] == "pseudohuber":
        cfg["huber_slope"] = trial.suggest_float("huber_slope", 0.02, 0.3, log=True)
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=list("EVS"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--trials", type=int, default=120)
    ap.add_argument("--timeout", type=int, default=4200)
    a = ap.parse_args()
    k = a.target
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ol.columns(k)
    folds = ol.build_folds(k, sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols))
    print(f"[{k}] folds: " + ", ".join(f"{f['name']} {len(f['X']):,}/{len(f['Xv']):,}" for f in folds), flush=True)
    inc_cfg, inc_trees = ol.incumbent_config(k)
    ref_path = OUT / f"optuna_{k}_reference.json"
    if ref_path.exists():
        ref = json.load(open(ref_path))
    else:
        ref = {f["name"]: ol.fold_curve(inc_cfg, f, inc_trees, a.jobs, (42, 43, 44))[inc_trees] for f in folds}
        json.dump(ref, open(ref_path, "w"), indent=1)
    print(f"[{k}] Phase 7 reference WAPE per fold: " + ", ".join(f"{n} {v:.3f}" for n, v in ref.items()), flush=True)
    t0 = time.time()

    def objective(trial):
        cfg = suggest(trial)
        n_max = int(min(600, 20 / cfg["learning_rate"]))
        curves = {f["name"]: ol.fold_curve(cfg, f, n_max, a.jobs, (42,)) for f in folds}
        pts = sorted(curves[folds[0]["name"]])
        score = {n: float(np.mean([curves[f["name"]][n] / ref[f["name"]] for f in folds])) for n in pts}
        n_best = min(score, key=score.get)
        trial.set_user_attr("n_trees", int(n_best))
        for f in folds:
            trial.set_user_attr(f"wape_{f['name']}", float(curves[f["name"]][n_best]))
        print(f"[{k} {time.time() - t0:6.0f}s] trial {trial.number:3d}  score {score[n_best]:.4f}  trees {n_best:3d}  lr {cfg['learning_rate']:.3f} leaves {cfg['max_leaves']} "
              f"mcw {cfg['min_child_weight']:.0f} loss {cfg['objective']} hl {cfg['recency_halflife']}", flush=True)
        return score[n_best]

    study = optuna.create_study(direction="minimize", study_name=f"lmis_{k}", storage=f"sqlite:///{(OUT / f'optuna_{k}.db').as_posix()}", load_if_exists=True,
                                sampler=optuna.samplers.TPESampler(seed=2026 + "EVS".index(k), multivariate=True, n_startup_trials=20))
    if len(study.trials) == 0:
        for c in (inc_cfg, PHASE6_DEFAULT):
            p = dict(c)
            p["reg_alpha"] = max(p["reg_alpha"], 1e-3)           # zero is outside the log-scale range; 0.001 is practically zero
            p["gamma"] = max(p["gamma"], 1e-4)
            study.enqueue_trial(p)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def save(study, trial):
        study.trials_dataframe().to_csv(OUT / f"optuna_{k}_trials.csv", index=False)

    study.optimize(objective, n_trials=a.trials, timeout=a.timeout, callbacks=[save])
    study.trials_dataframe().to_csv(OUT / f"optuna_{k}_trials.csv", index=False)
    print(f"[{k}] done: {len(study.trials)} trials, best {study.best_value:.4f} (trial {study.best_trial.number}), {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
