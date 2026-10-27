#!/usr/bin/env python3
"""
v4 phase 6 - fit the deployed models on all of 2000-2025.

Same tuned settings, inputs, seeds and recipe as the evaluation fits of phase 4 (evaluate.fit_target, FIT_FRAC of the (origin, horizon) pairs, 3 seeds per target), on the pairs whose
target month is at or before 2025-12, EXCEPT the pairs that reach into the 2020-2023 shock and recovery from an origin before the end of 2023 (BREAK).  A first fit on all pairs learned the
recovery (employment +28% in three years, registered seekers x2.7) as the normal outcome of an ordinary month and forecast seekers x3.8 by 2030; the shock is a break, not a pattern to repeat.
Long horizons are therefore learned from 2000-2019 dynamics, horizons up to 24 months also from 2024-2025.  The number of trees per horizon is the one chosen on the validation window (best_params.json); nothing is re-tuned.  Models are written to
models/v4/deploy/ (git-ignored) and a record of what was fitted to reports/v4/forecast/deploy_fit.json.

Run: python src/v4/deploy_fit.py
"""
import hashlib
import json
import time

import xgboost as xgb

import config as C
import evaluate as EV
import model_lib as M
import splits as SP

BREAK = (242, 287)                    # 2020-03 .. 2023-12: month indices of the shock and recovery
OUT = C.REPORTS / "forecast"
MDIR = C.MODELS / "deploy"


def tag_for(best, k, n_rows, columns):
    return hashlib.sha256(json.dumps([best[k]["params"], best[k]["tuning_rows"], n_rows, EV.NMAX, list(columns)], sort_keys=True).encode()).hexdigest()[:10]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    MDIR.mkdir(parents=True, exist_ok=True)
    best = json.loads((EV.OUT / "best_params.json").read_text(encoding="utf-8"))
    D, OF, SF = M.load_world()
    t0 = time.time()
    cut = SP.CUT["stress"]
    n_all = len(SP.fit_pairs(cut, frac=EV.FIT_FRAC)[0])
    t, h = SP._pairs(lambda t, h: (t >= SP.MIN_ORIGIN) & (t + h <= cut) & ~((t <= BREAK[1]) & (t + h >= BREAK[0])), EV.FIT_FRAC)     # same thinning, applied after the break pairs are left out
    print(f"pairs {n_all:,} -> {len(t):,} after leaving out those that reach into the break from an origin up to {SP.month(BREAK[1])}", flush=True)
    Xf, mf = M.build(D, OF, SF, t, h)
    print(f"deploy: fit rows {len(Xf):,} (targets to {SP.month(cut)}), inputs {Xf.shape[1]} ({time.time() - t0:.0f} s)", flush=True)
    rec = {"fit_targets_to": SP.month(cut), "left_out": f"pairs with origin up to {SP.month(BREAK[1])} and target from {SP.month(BREAK[0])}", "pairs_before": int(n_all), "pairs_after": int(len(t)), "fit_rows": int(len(Xf)), "inputs": list(Xf.columns), "seeds": list(EV.SEEDS), "models": {}}
    for k in "EVS":
        y = M.target(D, mf, k)
        tag = tag_for(best, k, len(Xf), Xf.columns)
        files = []
        for sd in EV.SEEDS:
            tt = time.time()
            path = MDIR / f"{k}_seed{sd}_{tag}.json"
            if not path.exists():
                EV.fit_target(Xf, y, best[k], sd).save_model(str(path))
            files.append(path.name)
            print(f"  {k} seed {sd}: {time.time() - tt:.0f} s", flush=True)
        rec["models"][k] = {"files": files, "trees_by_band": best[k]["trees_by_band"]}
    rec["seconds"] = round(time.time() - t0)
    (OUT / "deploy_fit.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print("done", rec["seconds"], "s")


if __name__ == "__main__":
    main()
