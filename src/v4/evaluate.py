#!/usr/bin/env python3
"""
v4 phase 4 - fit the tuned models and score them, window by window.

    validation  fit on targets to 2009-12, scored on 2010-2014     (the tuning window; reported, not an honest estimate)
    test        fit on targets to 2014-12, scored on 2015-2019     (opened once)
    stress      fit on targets to 2019-12, scored on 2020-2025     (opened once; COVID-19 and the e-Shram break; information only)

Each target has a seed ensemble of XGBoost models (3 seeds, the tuned settings, 'trees' rounds).  Scores are level-scale WAPE; the baselines are no change,
seasonal naive and a damped trend; "best baseline" is the lowest of the three in each cell.  Tables are written to reports/v4/evaluation/<window>_metrics.csv
(one row per target, slice, horizon band) and <window>_summary.json; the fitted models to models/v4/<window>/ (git-ignored).  A scored test or stress window
leaves a *_opened.json file and is not scored again unless --reopen is given (which records that it was).

Run: python src/v4/evaluate.py validation|test|stress [--reopen]
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import model_lib as M
import splits as SP

SEEDS = (11, 22, 33)
GRID = (1, 3, 6, 12, 24, 36, 48, 60)
FIT_FRAC = 1 / 12                                      # share of the (origin, horizon) pairs of a fitting window used to fit (the tuning used 30% of the 1/6 sample)
NMAX = 400                                             # trees grown; the number used depends on the horizon (trees_by_band, chosen on the validation window)
CHECK = (25, 50, 100, 150, 200, 250, 300, 400)
CENTERS = [(a + b) / 2 for a, b in M.BANDS]
OUT = C.REPORTS / "evaluation"


def fit_target(Xf, y, p, seed):
    params = dict(M.BASE_PARAMS, **p["params"], seed=seed)
    params["min_child_weight"] = p["params"]["min_child_weight"] * len(Xf) / p["tuning_rows"]       # the tuning used fewer rows; keep the same minimum share of rows per leaf
    return xgb.train(params, M.dtrain(Xf, y), NMAX)


def trees_for(horizon, by_band):
    """Number of trees used at each horizon: the per-band counts chosen on validation, interpolated between band centres and rounded to 25 (no jump at a band edge)."""
    n = np.interp(np.asarray(horizon, float), CENTERS, [by_band[b] for b in M.BAND_LABELS])
    return np.maximum(25, np.rint(n / 25) * 25).astype(int)


def predict_by_horizon(boosters, de, horizon, by_band):
    """Seed-averaged prediction in which each row uses the tree count of its horizon."""
    n_row = trees_for(horizon, by_band)
    out = np.zeros(len(n_row))
    for n in np.unique(n_row):
        idx = np.where(n_row == n)[0]
        part = de.slice(idx) if len(idx) < len(n_row) else de
        out[idx] = np.mean([b.predict(part, iteration_range=(0, int(n))) for b in boosters], axis=0)
    return out


def choose_trees(boosters, de, actual, base, horizon):
    """On the validation window: for each horizon band the tree count (from CHECK) with the lowest WAPE of the seed ensemble."""
    scores = {n: M.band_wapes(np.mean([b.predict(de, iteration_range=(0, n)) for b in boosters], axis=0), actual, base, horizon) for n in CHECK}
    by_band = {lab: int(min(CHECK, key=lambda n: scores[n][lab])) for lab in M.BAND_LABELS}
    return by_band, {int(n): {k: round(v, 3) for k, v in sc.items()} for n, sc in scores.items()}


def slices(me, dim, stats, k):
    """name -> (integer code per row, labels) for the slices reported."""
    s = me.series_row.to_numpy()
    out = {"all": (np.zeros(len(me), int), ["all"])}
    out["horizon"] = (np.searchsorted(GRID, me.horizon.to_numpy()), [str(g) for g in GRID] + [">60"])
    for name, col in (("sector", "Sector_Name"), ("trade", "Trade_Code"), ("state", "State_Name")):
        lab = sorted(dim[col].unique())
        out[name] = (pd.Categorical(dim[col].to_numpy()[s], categories=lab).codes, lab)
    vol = np.where(stats.Low_Volume_Train.to_numpy()[s], 1, 0)
    out["volume"] = (vol, ["normal volume", "low volume"])
    shock = me.shock_S.to_numpy() if k == "S" else me.shock_EV.to_numpy()
    out["shock_window"] = (shock.astype(int), ["calm window", "touches a shock"])
    return out


def table(window, k, me, dim, stats, actual, base, preds):
    """Long table of WAPE (model and baselines) by slice and horizon band."""
    a = np.exp(base.astype(np.float64) + actual)
    band = pd.Categorical(M.band_of(me.horizon.to_numpy()), categories=M.BAND_LABELS).codes.astype(np.int64)
    rows = []
    errs = {nm: np.abs(np.exp(base.astype(np.float64) + pr) - a) for nm, pr in preds.items()}
    signed = np.exp(base.astype(np.float64) + preds["model"]) - a
    for sname, (code, labels) in slices(me, dim, stats, k).items():
        G = len(labels)
        key = np.asarray(code).astype(np.int64) * 6 + band
        cnt = np.bincount(key, minlength=G * 6).reshape(G, 6)
        den = np.bincount(key, weights=a, minlength=G * 6).reshape(G, 6)
        sums = {nm: np.bincount(key, weights=e, minlength=G * 6).reshape(G, 6) for nm, e in errs.items()}
        bias = np.bincount(key, weights=signed, minlength=G * 6).reshape(G, 6)
        for g in range(G):
            for b in range(6):
                if b < 5:
                    n, d = cnt[g, b], den[g, b]
                    num = {nm: sums[nm][g, b] for nm in sums}
                    bi = bias[g, b]
                    lab = M.BAND_LABELS[b]
                else:
                    n, d, bi = cnt[g].sum(), den[g].sum(), bias[g].sum()
                    num = {nm: sums[nm][g].sum() for nm in sums}
                    lab = "all horizons"
                if n == 0:
                    continue
                w = {nm: num[nm] / d * 100 for nm in num}
                best = min(w["naive"], w["seasonal_naive"], w["damped_trend"])
                rows.append({"window": window, "target": k, "slice": sname, "value": labels[g], "band": lab, "rows": int(n), "wape_model": w["model"], "wape_naive": w["naive"],
                             "wape_seasonal_naive": w["seasonal_naive"], "wape_damped_trend": w["damped_trend"], "wape_best_baseline": best,
                             "improvement_vs_best_baseline_pct": (1 - w["model"] / best) * 100, "bias_pct": bi / d * 100})
    return pd.DataFrame(rows)


def main(window, reopen=False):
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / f"{window}_opened.json"
    if window in SP.LOCKED and lock.exists() and not reopen:
        raise SystemExit(f"the {window} window was already scored ({lock.name}); it is scored once. Use --reopen only to record a deliberate second look.")
    best = json.loads((OUT / "best_params.json").read_text(encoding="utf-8"))
    D, OF, SF = M.load_world()
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    stats = pd.read_csv(C.DATA / "dim_series_stats.csv")
    cut = SP.fit_cut_for(window)
    t0 = time.time()
    t, h = SP.fit_pairs(cut, frac=FIT_FRAC)
    Xf, mf = M.build(D, OF, SF, t, h)
    et, eh = SP.eval_pairs(window, unlock=True)
    Xe, me = M.build(D, OF, SF, et, eh)
    de = M.ddata(Xe)
    print(f"{window}: fit rows {len(Xf):,} (targets to {SP.month(cut)}), scored rows {len(Xe):,}, inputs {Xf.shape[1]} ({time.time() - t0:.0f} s)", flush=True)
    mdir = C.MODELS / window
    mdir.mkdir(parents=True, exist_ok=True)
    tabs, summary = [], {"window": window, "fit_targets_to": SP.month(cut), "fit_rows": int(len(Xf)), "scored_rows": int(len(Xe)), "inputs": list(Xf.columns), "seeds": list(SEEDS)}
    for k in "EVS":
        y, ye, base = M.target(D, mf, k), M.target(D, me, k), M.base_log(D, me, k)
        tag = hashlib.sha256(json.dumps([best[k]["params"], best[k]["tuning_rows"], len(Xf), NMAX, list(Xf.columns)], sort_keys=True).encode()).hexdigest()[:10]
        boosters, files = [], []
        for sd in SEEDS:
            tt = time.time()
            path = mdir / f"{k}_seed{sd}_{tag}.json"
            if path.exists():                                                   # fitted earlier with the same settings, rows and inputs
                b = xgb.Booster()
                b.load_model(str(path))
            else:
                b = fit_target(Xf, y, best[k], sd)
                b.save_model(str(path))
            boosters.append(b)
            files.append(path.name)
            print(f"  {k} seed {sd}: {time.time() - tt:.0f} s", flush=True)
        if window == "validation":                                              # the tree count per horizon band is chosen here and only here
            best[k]["trees_by_band"], summary.setdefault("tree_scores", {})[k] = choose_trees(boosters, de, ye, base, me.horizon.to_numpy())
            (OUT / "best_params.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
        elif "trees_by_band" not in best[k]:
            raise SystemExit("run the validation window first: it chooses the number of trees per horizon band")
        pr = predict_by_horizon(boosters, de, me.horizon.to_numpy(), best[k]["trees_by_band"])
        preds = {"model": pr, **M.baselines(Xe, me, k)}
        tab = table(window, k, me, dim, stats, ye, base, preds)
        tabs.append(tab)
        row = tab[(tab.slice == "all") & (tab.band == "all horizons")].iloc[0]
        summary[k] = {"models": files, "trees_by_band": best[k]["trees_by_band"], "wape_model": round(row.wape_model, 3), "wape_best_baseline": round(row.wape_best_baseline, 3), "improvement_pct": round(row.improvement_vs_best_baseline_pct, 1),
                      "bands": {r.band: {"model": round(r.wape_model, 2), "best_baseline": round(r.wape_best_baseline, 2), "improvement_pct": round(r.improvement_vs_best_baseline_pct, 1)}
                                for r in tab[(tab.slice == "all") & (tab.band != "all horizons")].itertuples()}}
        print(k, json.dumps(summary[k]["bands"]), flush=True)
    pd.concat(tabs).round(4).to_csv(OUT / f"{window}_metrics.csv", index=False)
    summary["seconds"] = round(time.time() - t0)
    (OUT / f"{window}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if window in SP.LOCKED:
        lock.write_text(json.dumps({"window": window, "scored_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reopened": bool(reopen),
                                    "params_sha256": hashlib.sha256((OUT / "best_params.json").read_bytes()).hexdigest()}, indent=2), encoding="utf-8")
    print("done", summary["seconds"], "s")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or args[0] not in ("validation", "test", "stress"):
        sys.exit(__doc__)
    main(args[0], "--reopen" in sys.argv)
