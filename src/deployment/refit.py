#!/usr/bin/env python3
"""
Phase 9 - refit the declared xgboost_v3 configuration on all history up to a forecast origin, and (with --backtest) check that refitting on newer data does not hurt.

    python src/deployment/refit.py --origin 2026-10            -> models/deployed/origin_2026-10/   (the models the forecast uses)
    python src/deployment/refit.py --backtest 2025-12          -> reports/deployment/refit_backtest.json

Hyper-parameters, tree counts, seeds, recency weighting, the horizon blend and the interval policy are those declared in models/xgboost_v3 (nothing is re-tuned).
Only the training rows change: every (series, origin, horizon) example whose target month is inside the history, with the Phase 5 shock-window policy for employed workers.
The backtest refits through an earlier month and scores the months after it against the declared v3 models (fitted on data to 2022-12) and the baseline on the same rows.
"""
import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training", "evaluation", "deployment"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import features as df_  # noqa: E402
import lmis_data as ld  # noqa: E402
import opt_lib as ol  # noqa: E402
import splits as sp  # noqa: E402
from preprocess import FeaturePreprocessor  # noqa: E402
from predict import Forecaster  # noqa: E402

V3 = ROOT / "models" / "xgboost_v3"
SEEDS = (42, 43, 44, 45, 46)


def fit_all(ex, through_idx, jobs=-1):
    """Fit E, V, S ensembles on the examples whose target month index is <= through_idx.  Returns models, preprocessors, params and row counts."""
    prm = json.load(open(V3 / "primary" / "params.json"))
    models, pres, params = {}, {}, {}
    for k in "EVS":
        sk = ld.spec()[k]
        tr = ld.train_rows(ex[ex.target_idx <= through_idx], k, sk)
        X, y = ld.xy(tr, k, sk)
        pre = FeaturePreprocessor(X.columns).fit(X, tr["split"], allowed=("deploy",))
        cfg, n = prm[k]["config"], prm[k]["xgboost_params"]["n_estimators"]
        t0 = time.time()
        models[k] = ol.fit_ensemble(cfg, n, pre.transform(X), y, tr.target_idx.to_numpy(), through_idx, jobs, SEEDS)
        pres[k] = pre
        params[k] = {**prm[k], "training_rows": int(len(tr)), "last_target_index": int(through_idx), "n_series": int(tr.Series_ID.nunique())}
        print(f"  {k}: {len(tr):,} rows, {n} trees x {len(SEEDS)} seeds, {time.time() - t0:.0f}s", flush=True)
    return models, pres, params


def backtest(through, jobs):
    last = df_.load_history("2026-10")
    ex, D = df_.training_rows(last)
    idx = {pd.Timestamp(d).strftime("%Y-%m"): i for i, d in enumerate(D.dates)}
    t = idx[through]
    print(f"backtest: refit through {through}, score origins from {through} with targets up to 2026-10", flush=True)
    models, pres, params = fit_all(ex, t, jobs)
    ev = ex[(ex.origin_idx >= t) & (ex.target_idx > t)].copy()
    fc3 = Forecaster.load(V3 / "primary")
    p3 = fc3.predict(ev)
    out = {"refit_through": through, "evaluated_rows": int(len(ev)), "targets_up_to": "2026-10", "horizons": sorted(ev.horizon.unique().tolist()), "wape_mean_horizon": {}, "note":
           "pseudo-holdout: not an unbiased test (the blend and interval policy were chosen with the 2023-2026 data in view); it checks that more data does not hurt"}
    for k in "EVS":
        sk = ld.spec()[k]
        Z = pres[k].transform(ev[sk["features"]])
        base = ev[f"{sk['base']}_{k}"].to_numpy() + ol.predict_ensemble(models[k], Z)
        w = np.array([fc3.blend[k][str(int(h))] for h in ev.horizon])
        base_line = ev[f"last_{k}"].to_numpy() + np.nan_to_num(ev[f"{k}_sf_shift"].to_numpy(), nan=0.0)
        new = w * base + (1 - w) * base_line
        act = ev[f"target_{k}"].to_numpy()
        out["wape_mean_horizon"][k] = {"refit_to_" + through: ld.mean_horizon_wape(ev, act, new)[0], "v3_fitted_to_2022-12": ld.mean_horizon_wape(ev, act, p3[f"pred_log_{k}"].to_numpy())[0],
                                       "baseline": ld.mean_horizon_wape(ev, act, ld.baseline_log(ev, k, "seasonal_naive_drift" if k == "E" else "last_plus_seasonal_shift"))[0]}
        print(k, {a: round(b, 3) for a, b in out["wape_mean_horizon"][k].items()}, flush=True)
    json.dump(out, open(ROOT / "reports" / "deployment" / "refit_backtest.json", "w"), indent=1)


def deploy(origin, jobs):
    panel = df_.load_history(origin)
    ex, D = df_.training_rows(panel)
    t = D.T - 1
    models, pres, params = fit_all(ex, t, jobs)
    out = ROOT / "models" / "deployed" / f"origin_{origin}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for k in "EVS":
        for sd, m in zip(SEEDS, models[k]):
            m.save_model(out / f"{k}_seed{sd}.ubj")
    json.dump(params, open(out / "params.json", "w"), indent=1, default=float)
    json.dump({k: p.to_dict() for k, p in pres.items()}, open(out / "preprocessor.json", "w"), indent=1)
    for name in ("blend.json", "intervals.json"):
        shutil.copy(V3 / "primary" / name, out / name)
    for name in ("conformal.json", "vacancy_intervals_recalibrated.json", "final_interval_policy.json"):
        shutil.copy(V3 / name, out / name)
    files = {f.name: sp.sha256(f) for f in sorted(out.iterdir())}
    json.dump({"origin": origin, "history": [str(D.dates[0].date()), str(D.dates[-1].date())], "training_target_months_up_to": str(D.dates[-1].date()), "source_declaration": "models/xgboost_v3/declaration.json",
               "source_declaration_sha256": sp.sha256(V3 / "declaration.json"), "panel_sha256": sp.sha256(df_.PANEL), "files_sha256": files, "built": time.strftime("%Y-%m-%d %H:%M:%S"),
               "environment": {"python": platform.python_version(), "xgboost": xgb.__version__, "numpy": np.__version__, "pandas": pd.__version__}}, open(out / "manifest.json", "w"), indent=1)
    shutil.copy(out / "manifest.json", out / "checkpoint_manifest.json")           # Forecaster.load expects this name
    print("deployed models ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin")
    ap.add_argument("--backtest")
    ap.add_argument("--jobs", type=int, default=-1)
    a = ap.parse_args()
    if a.backtest:
        backtest(a.backtest, a.jobs)
    elif a.origin:
        deploy(a.origin, a.jobs)
    else:
        ap.error("give --origin or --backtest")
