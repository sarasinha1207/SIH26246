#!/usr/bin/env python3
"""
Phase 8 - turn the Optuna search into frozen decisions for one target, using only train + validation data.

1. Re-rank: the 5 best Optuna trials, the Phase 7 configuration (incumbent) and the Phase 6 default are re-scored on the four folds with 3 seeds each.
   The incumbent is replaced only if a candidate is at least 1% better on the mean fold ratio (the noise level is about 1%).
2. Blend with the baseline (resolves Phase 6 item D4): for each horizon, the weight w on the model in  w * model + (1 - w) * baseline  (baseline = last value +
   seasonal shift, log scale) is chosen from {0, .25, .5, .75, 1} on out-of-sample predictions of the three rolling-origin folds.  A weight below 1 is used only if it
   lowers that horizon's WAPE by at least 1%.  The validation fold is not used to choose weights.
3. Interval calibration: 5% / 95% quantiles of the blended model's log errors, per horizon, from the three rolling-origin folds, then scaled by the median ratio of
   the validation split's error spread to the folds' spread (horizons 1-10), because errors after COVID are wider than before it.

Run: python src/evaluation/finalize.py E|V|S [--jobs 4]       Writes reports/evaluation/finalize_<k>.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import opt_lib as ol  # noqa: E402
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from tune_optuna import PHASE6_DEFAULT  # noqa: E402

OUT = ROOT / "reports" / "evaluation"
SEEDS3, SEEDS5 = (42, 43, 44), (42, 43, 44, 45, 46)
GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
ACCEPT = 0.99
PARAM_KEYS = ("learning_rate", "max_leaves", "min_child_weight", "reg_lambda", "reg_alpha", "gamma", "subsample", "colsample_bytree", "colsample_bynode", "max_bin",
              "objective", "recency_halflife", "huber_slope")


def cfg_from_row(r):
    cfg = {}
    for key in PARAM_KEYS:
        v = r.get(f"params_{key}")
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        cfg[key] = int(v) if key in ol.INT_KEYS or key == "recency_halflife" else (v if key == "objective" else float(v))
    return cfg


def fold_pred(cfg, n_trees, fold, jobs, seeds):
    models = ol.fit_ensemble(cfg, n_trees, fold["X"], fold["y"], fold["tidx"], fold["end"], jobs, seeds)
    return fold["base_v"] + ol.predict_ensemble(models, fold["Xv"])


def score(cfg, n_trees, folds, ref, jobs, seeds):
    w = {}
    for f in folds:
        p = fold_pred(cfg, n_trees, f, jobs, seeds)
        w[f["name"]] = ld.mean_horizon_wape(f["va"], f["act"], p)[0]
    return w, float(np.mean([w[n] / ref[n] for n in w]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=list("EVS"))
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    k, jobs, t0 = a.target, a.jobs, time.time()
    cols = ol.columns(k)
    folds = ol.build_folds(k, sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols))
    ref = json.load(open(OUT / f"optuna_{k}_reference.json"))
    T = pd.read_csv(OUT / f"optuna_{k}_trials.csv")
    T = T[T.state == "COMPLETE"]
    inc_cfg, inc_trees = ol.incumbent_config(k)
    p6_trees = int(T[T.number == 1]["user_attrs_n_trees"].iloc[0]) if (T.number == 1).any() else 250
    cand = [dict(name="phase7_incumbent", cfg=inc_cfg, trees=inc_trees), dict(name="phase6_default", cfg=PHASE6_DEFAULT, trees=p6_trees)]
    for _, r in T[T.number > 1].nsmallest(5, "value").iterrows():
        cand.append(dict(name=f"optuna_trial_{int(r.number)}", cfg=cfg_from_row(r), trees=int(r.user_attrs_n_trees), search_value=float(r.value)))
    for c in cand:
        c["fold_wape"], c["score"] = score(c["cfg"], c["trees"], folds, ref, jobs, SEEDS3)
        print(f"[{k} {time.time() - t0:5.0f}s] {c['name']:22s} trees {c['trees']:3d} score {c['score']:.4f}  " + " ".join(f"{n} {v:.3f}" for n, v in c["fold_wape"].items()), flush=True)
    best = min(cand, key=lambda c: c["score"])
    inc = cand[0]
    chosen = best if best["score"] <= ACCEPT * inc["score"] else inc
    print(f"[{k}] best candidate {best['name']} ({best['score']:.4f}) vs incumbent {inc['score']:.4f}: keep {chosen['name']}", flush=True)
    cfg, n_trees = chosen["cfg"], chosen["trees"]
    # ---- out-of-sample predictions of the final configuration (5 seeds) on every fold
    preds = {f["name"]: fold_pred(cfg, n_trees, f, jobs, SEEDS5) for f in folds}
    base = {f["name"]: ld.baseline_log(f["va"], k) for f in folds}
    cv = [f for f in folds if f["name"] != "validation"]
    # ---- blend weights from the rolling-origin folds
    w_h, rows = {}, []
    for h in range(1, 13):
        scores = {}
        for w in GRID:
            per = []
            for f in cv:
                m = (f["va"]["horizon"] == h).to_numpy()
                per.append(ld.wape(f["act"][m], w * preds[f["name"]][m] + (1 - w) * base[f["name"]][m]))
            scores[w] = float(np.mean(per))
        best_w = min(scores, key=scores.get)
        use = best_w if scores[best_w] <= 0.99 * scores[1.0] else 1.0
        w_h[h] = use
        rows.append(dict(horizon=h, model_weight=use, cv_wape_model_only=scores[1.0], cv_wape_blend=scores[use], cv_wape_baseline_only=scores[0.0]))
    blend = lambda name, h: (lambda w: w * preds[name] + (1 - w) * base[name])(np.array([w_h[int(x)] for x in folds[[f['name'] for f in folds].index(name)]["va"]["horizon"]]))  # noqa: E731
    final = {f["name"]: blend(f["name"], None) for f in folds}
    val_f = folds[-1]
    gain_val = dict(model_only=ld.mean_horizon_wape(val_f["va"], val_f["act"], preds["validation"])[0], blended=ld.mean_horizon_wape(val_f["va"], val_f["act"], final["validation"])[0],
                    baseline=ld.mean_horizon_wape(val_f["va"], val_f["act"], base["validation"])[0])
    # ---- interval calibration
    q = lambda e: [float(np.quantile(e, 0.05)), float(np.quantile(e, 0.95))]  # noqa: E731
    cv_q, val_q = {}, {}
    for h in range(1, 13):
        e = np.concatenate([f["act"][(f["va"]["horizon"] == h).to_numpy()] - final[f["name"]][(f["va"]["horizon"] == h).to_numpy()] for f in cv])
        cv_q[h] = q(e)
        mv = (val_f["va"]["horizon"] == h).to_numpy()
        if mv.any():
            val_q[h] = q(val_f["act"][mv] - final["validation"][mv])
    ratios = [(val_q[h][1] - val_q[h][0]) / (cv_q[h][1] - cv_q[h][0]) for h in val_q]
    scale = float(np.median(ratios))
    intervals = {str(h): [cv_q[h][0] * scale, cv_q[h][1] * scale] for h in range(1, 13)}
    res = dict(target=k, chosen=dict(name=chosen["name"], cfg=cfg, n_trees=n_trees, score=chosen["score"]), candidates=cand, accept_rule=f"replace the incumbent only if score <= {ACCEPT} x incumbent",
               blend_weights={str(h): w for h, w in w_h.items()}, blend_table=rows, validation_check_of_blend=gain_val, interval_scale=scale, interval_scale_ratios=ratios,
               intervals_cv=cv_q, intervals_validation={str(h): v for h, v in val_q.items()}, intervals=intervals, seeds=list(SEEDS5), seconds=round(time.time() - t0))
    json.dump(res, open(OUT / f"finalize_{k}.json", "w"), indent=1, default=float)
    print(f"[{k}] blend weights {w_h}  validation (model / blend / baseline): {gain_val}  interval scale {scale:.2f}", flush=True)


if __name__ == "__main__":
    main()
