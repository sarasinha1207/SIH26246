#!/usr/bin/env python3
"""
Phase 8 - apply the validation veto to the horizon blend and recompute the intervals for the final weights.  Train + validation data only.

finalize.py chose blend weights from the three rolling-origin folds.  The validation split was then used as a veto: if the blend makes validation WAPE more than 5%
worse than the model alone, the blend for that target is dropped (all weights 1).  This was added after seeing the validation numbers (seekers: 8.40 model alone vs
11.89 blended, because the whole validation window is inside the e-Shram ramp, where the baseline cannot follow); the weights from the folds are still
evaluated on the test split as the comparison model `cv_blend`.  Intervals are recomputed (same method as finalize.py) for the final weights.

Run: python src/evaluation/recalibrate.py E|V|S [--jobs 12]      Updates reports/evaluation/finalize_<k>.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import opt_lib as ol  # noqa: E402
import splits as sp  # noqa: E402
from finalize import SEEDS5, fold_pred  # noqa: E402
import lmis_data as ld  # noqa: E402

OUT = ROOT / "reports" / "evaluation"
VETO = 1.05


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=list("EVS"))
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    k = a.target
    path = OUT / f"finalize_{k}.json"
    fin = json.load(open(path))
    chk = fin["validation_check_of_blend"]
    veto = chk["blended"] > VETO * chk["model_only"]
    fin["blend_weights_cv"] = fin["blend_weights"]
    fin["blend_veto"] = dict(applied=bool(veto), rule=f"drop the blend if validation WAPE with blend > {VETO} x model alone", model_only=chk["model_only"], blended=chk["blended"])
    fin["blend_weights_final"] = {str(h): 1.0 for h in range(1, 13)} if veto else fin["blend_weights"]
    if veto:
        cols = ol.columns(k)
        folds = ol.build_folds(k, sp.load_split("train", columns=cols), sp.load_split("validation", columns=cols))
        cfg, n = fin["chosen"]["cfg"], fin["chosen"]["n_trees"]
        preds = {f["name"]: fold_pred(cfg, n, f, a.jobs, SEEDS5) for f in folds}
        cv = [f for f in folds if f["name"] != "validation"]
        val_f = folds[-1]
        q = lambda e: [float(np.quantile(e, 0.05)), float(np.quantile(e, 0.95))]  # noqa: E731
        cv_q, val_q = {}, {}
        for h in range(1, 13):
            e = np.concatenate([f["act"][(f["va"]["horizon"] == h).to_numpy()] - preds[f["name"]][(f["va"]["horizon"] == h).to_numpy()] for f in cv])
            cv_q[h] = q(e)
            mv = (val_f["va"]["horizon"] == h).to_numpy()
            if mv.any():
                val_q[h] = q(val_f["act"][mv] - preds["validation"][mv])
        scale = float(np.median([(val_q[h][1] - val_q[h][0]) / (cv_q[h][1] - cv_q[h][0]) for h in val_q]))
        fin["intervals_with_cv_blend"] = fin["intervals"]
        fin["interval_scale_with_cv_blend"] = fin["interval_scale"]
        fin["interval_scale"] = scale
        fin["intervals"] = {str(h): [cv_q[h][0] * scale, cv_q[h][1] * scale] for h in range(1, 13)}
        fin["validation_check_final"] = dict(model_only=ld.mean_horizon_wape(val_f["va"], val_f["act"], preds["validation"])[0])
    json.dump(fin, open(path, "w"), indent=1, default=float)
    print(k, "veto applied" if veto else "no veto", "scale", round(fin["interval_scale"], 3))


if __name__ == "__main__":
    main()
