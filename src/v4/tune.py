#!/usr/bin/env python3
"""
v4 phase 4 - hyperparameter tuning with Optuna, on the validation window only.

For each target the models are fitted on a random 30% of the training-window rows (targets 2000-2009) and scored on a random 30% of the validation rows
(targets 2010-2014, origins 2009-12 or later).  A trial draws the settings, grows 400 trees at eta 0.05 and is scored at 50, 100, 150, 200, 300 and 400 trees;
its score is the best of these.  Score = mean of the five horizon-band WAPEs (1-12, 13-24, ..., 49-60 months), so the long horizons count as much as the short ones.
The test and stress windows are not read here.

Writes reports/v4/evaluation/best_params.json and tuning_trials.csv.   Run: python src/v4/tune.py [trials per target, default 20]   (about 15 minutes per target)
"""
import json
import sys
import time

import numpy as np
import optuna
import pandas as pd
import xgboost as xgb

import config as C
import model_lib as M
import splits as SP

CHECK = (50, 100, 150, 200, 300, 400)
FIT_FRAC, VAL_FRAC = 0.30, 0.30


def sample(trial):
    return dict(max_depth=trial.suggest_int("max_depth", 3, 7), min_child_weight=trial.suggest_float("min_child_weight", 50, 2000, log=True),
                subsample=trial.suggest_float("subsample", 0.5, 0.9), colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 0.8),
                reg_lambda=trial.suggest_float("reg_lambda", 1, 200, log=True), reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
                gamma=trial.suggest_float("gamma", 0.0, 0.05))


def main(n_trials=20):
    out = C.REPORTS / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    D, OF, SF = M.load_world()
    t, h = SP.fit_pairs(SP.CUT["train"])
    Xf, mf = M.build(D, OF, SF, t, h, rows=(FIT_FRAC, 0))
    vt, vh = SP.eval_pairs("validation")
    Xv, mv = M.build(D, OF, SF, vt, vh, rows=(VAL_FRAC, 1))
    dv = M.ddata(Xv)
    print("tuning rows", len(Xf), "validation rows", len(Xv), "inputs", Xf.shape[1], flush=True)
    best, trials = {}, []
    for k in "EVS":
        y, yv, base = M.target(D, mf, k), M.target(D, mv, k), M.base_log(D, mv, k)
        dtr = M.dtrain(Xf, y)
        horizon = mv.horizon.to_numpy()

        def run(trial):
            p = dict(M.BASE_PARAMS, **sample(trial))
            b = xgb.train(p, dtr, max(CHECK))
            scores = {n: M.objective(b.predict(dv, iteration_range=(0, n)), yv, base, horizon) for n in CHECK}
            n_best = min(scores, key=scores.get)
            trial.set_user_attr("trees", int(n_best))
            trial.set_user_attr("scores", {int(n): round(s, 3) for n, s in scores.items()})
            return scores[n_best]

        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=C.SEED, n_startup_trials=6))
        study.enqueue_trial(dict(max_depth=4, min_child_weight=200, subsample=0.7, colsample_bytree=0.5, reg_lambda=50, reg_alpha=0.001, gamma=0.0))     # the ablation's settings
        t0 = time.time()
        for i in range(n_trials):
            study.optimize(run, n_trials=1)
            tr = study.trials[-1]
            print(f"{k} trial {i + 1}/{n_trials} score {tr.value:.3f} trees {tr.user_attrs['trees']} best {study.best_value:.3f} ({time.time() - t0:.0f} s)", flush=True)
        bt = study.best_trial
        best[k] = {"params": bt.params, "trees": bt.user_attrs["trees"], "validation_score": round(bt.value, 3), "tuning_rows": int(len(Xf)), "trials": n_trials}
        for tr in study.trials:
            trials.append({"target": k, "trial": tr.number, "score": tr.value, "trees": tr.user_attrs["trees"], **tr.params})
        (out / "best_params.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
        pd.DataFrame(trials).round(4).to_csv(out / "tuning_trials.csv", index=False)
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
