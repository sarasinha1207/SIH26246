#!/usr/bin/env python3
"""
Phase 8 - one-shot evaluation on the locked test split (2023-01 to 2026-12), with the models frozen in models/xgboost_v2/frozen_config.json.

Before opening the test file this script checks the SHA-256 of every frozen file and writes reports/evaluation/test_access_log.json.  A second run is refused
unless --rerun is given, and every run is appended to the log, so the number of times the test split was looked at is on record.
Nothing is tuned here.  Outputs: reports/evaluation/test/*.csv, test_results.json, data/interim/phase8_test_predictions.parquet (not in git).

Run: python src/evaluation/evaluate.py            (--dry-run scores the validation split instead, to debug the code path; writes to reports/evaluation/dryrun, never opens the test file)
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training", "evaluation"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from predict import Forecaster  # noqa: E402

V2 = ROOT / "models" / "xgboost_v2"
OUT = ROOT / "reports" / "evaluation"
TBL = OUT / "test"
LOG = OUT / "test_access_log.json"
TODAY = pd.Timestamp("2026-10-19")
MODELS = ["primary", "cv_blend", "train_only", "v1_refit", "hgb"]
BASELINES = ["last_plus_seasonal_shift", "last_value", "seasonal_naive_drift"]
ALL = MODELS + BASELINES
N_BOOT = 500


def verify_frozen():
    fr = json.load(open(V2 / "frozen_config.json"))
    assert fr["test_split_opened"] is False, "the freeze record says the test split was already opened"
    for variant, files in fr["files_sha256"].items():
        for name, digest in files.items():
            assert sp.sha256(V2 / variant / name) == digest, f"{variant}/{name} changed after the freeze"
    for k, digest in fr["finalize_sha256"].items():
        assert sp.sha256(OUT / f"finalize_{k}.json") == digest, f"finalize_{k}.json changed after the freeze"
    return fr


def predictions(test, hgb_dir):
    dims = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv")[["Series_ID", "Econ_Tier", "Low_Volume", "District_Name"]]
    out = {}
    fc = {v: Forecaster.load(V2 / v) for v in ("primary", "train_only", "v1_refit")}
    raw = {v: f.predict(test) for v, f in fc.items()}
    fcb = Forecaster.load(V2 / "primary")                 # same models, horizon blend chosen on the folds before the validation veto
    fcb.blend = json.load(open(V2 / "primary" / "blend_cv.json"))["model_weight_by_target_horizon"]
    raw["cv_blend"] = fcb.predict(test)
    for k in "EVS":
        sk = ld.spec()[k]
        P = test[["Series_ID", "sector", "state", "origin_idx", "target_idx", "target_date", "horizon", f"target_in_shock_{'S' if k == 'S' else 'EV'}"]].copy()
        P = P.rename(columns={f"target_in_shock_{'S' if k == 'S' else 'EV'}": "shock"})
        P["actual_log"] = test[f"target_{k}"].to_numpy()
        for v in raw:
            P[v] = raw[v][f"pred_log_{k}"].to_numpy()
        P["hgb"] = test[f"{sk['base']}_{k}"].to_numpy() + joblib.load(hgb_dir / f"{k}.joblib").predict(test[sk["features"]])
        for b in BASELINES:
            P[b] = ld.baseline_log(test, k, b)
        for v in ("primary", "v1_refit"):
            P[f"{v}_lo"] = np.log(raw[v][f"lo90_{k}"].to_numpy())
            P[f"{v}_hi"] = np.log(raw[v][f"hi90_{k}"].to_numpy())
        out[k] = P.merge(dims, on="Series_ID", how="left")
    return out, fc


def wape(P, col):
    a, p = np.exp(P.actual_log.to_numpy()), np.exp(P[col].to_numpy())
    return 100 * np.abs(a - p).sum() / a.sum()


def mh(P, col):
    """Mean over horizons of WAPE (equal weight per horizon present)."""
    v = [wape(g, col) for _, g in P.groupby("horizon")]
    return float(np.mean(v)) if v else np.nan


def matrices(P, cols):
    sid = {s: i for i, s in enumerate(sorted(P.Series_ID.unique()))}
    si, hi = P.Series_ID.map(sid).to_numpy().astype(int), P.horizon.to_numpy().astype(int) - 1
    a = np.exp(P.actual_log.to_numpy())
    D = np.zeros((len(sid), 12))
    np.add.at(D, (si, hi), a)
    A = {}
    for c in cols:
        M = np.zeros((len(sid), 12))
        np.add.at(M, (si, hi), np.abs(a - np.exp(P[c].to_numpy())))
        A[c] = M
    return A, D


def bootstrap_diff(A, D, c1, c2, rng, by_horizon=False):
    n = D.shape[0]
    res = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, n)
        den = D[idx].sum(0)
        w1, w2 = 100 * A[c1][idx].sum(0) / den, 100 * A[c2][idx].sum(0) / den
        res.append(w1 - w2 if by_horizon else (w1 - w2).mean())
    res = np.array(res)
    return np.quantile(res, [0.025, 0.975], axis=0)


def main():
    global TBL, OUT_RES
    dry = "--dry-run" in sys.argv
    rerun = "--rerun" in sys.argv
    fr = verify_frozen()
    log = json.load(open(LOG)) if LOG.exists() else {"runs": []}
    if not dry:
        if log["runs"] and not rerun:
            raise SystemExit("the test split has already been evaluated once (see test_access_log.json); pass --rerun only to repeat the identical evaluation")
        log["runs"].append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "frozen_at": fr["frozen_at"], "git_head_at_freeze": fr["git_head_at_freeze"],
                            "frozen_config_sha256": sp.sha256(V2 / "frozen_config.json"), "purpose": "one-shot Phase 8 evaluation"})
        json.dump(log, open(LOG, "w"), indent=1)
    else:
        TBL = OUT / "dryrun"
    OUT_RES = OUT / ("dryrun/test_results.json" if dry else "test_results.json")
    TBL.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    test = sp.load_split("validation") if dry else sp.load_split("test", unlock_test=True, verify=True)
    print(f"{'DRY RUN on validation' if dry else 'test'} rows {len(test):,}; frozen at {fr['frozen_at']}", flush=True)
    PRED, fc = predictions(test, V2 / "challenger_hgb")
    if dry:                      # every validation month is inside the seekers' ramp; do not mask, so the code path is exercised for all targets
        for k in PRED:
            PRED[k]["shock"] = False
    pd.concat({k: v for k, v in PRED.items()}, names=["target"]).reset_index(level=0).to_parquet(
        ROOT / "data" / "interim" / ("phase8_dryrun_predictions.parquet" if dry else "phase8_test_predictions.parquet"), index=False)
    rng = np.random.default_rng(2026)
    R = {"rows": int(len(test)), "frozen_at": fr["frozen_at"], "targets": {}}
    overall, by_h, by_slice, weak, cover, equity, score_rows = [], [], [], [], [], [], []
    for k in "EVS":
        P = PRED[k]
        S = P[~P.shock.to_numpy()].reset_index(drop=True)                 # scored rows (seekers: ramp months excluded)
        A, D = matrices(S, ALL)
        best_base = min(BASELINES, key=lambda b: mh(S, b))
        R["targets"][k] = {"scored_rows": int(len(S)), "excluded_shock_rows": int(len(P) - len(S)), "best_baseline": best_base}
        for m in ALL:
            lo, hi = bootstrap_diff(A, D, "primary", m, rng) if m != "primary" else (np.nan, np.nan)
            overall.append(dict(target=k, model=m, wape_mean_horizon=mh(S, m), wape_pooled=wape(S, m), diff_primary_minus_model=mh(S, "primary") - mh(S, m) if m != "primary" else 0.0,
                                diff_ci_low=lo, diff_ci_high=hi, bias_mean_log_error=float((S.actual_log - S[m]).mean())))
        for h, g in S.groupby("horizon"):
            for m in ALL:
                by_h.append(dict(target=k, horizon=h, model=m, wape=wape(g, m), rows=len(g)))
        # slices (primary vs best baseline vs v1_refit vs hgb)
        S["year"] = S.target_date.dt.year
        S["future_month"] = S.target_date >= TODAY.replace(day=1)
        for name, col in (("sector", "sector"), ("tier", "Econ_Tier"), ("state", "state"), ("target_year", "year"), ("low_volume", "Low_Volume"), ("future_month", "future_month")):
            for val, g in S.groupby(col):
                by_slice.append(dict(target=k, slice=name, value=str(val), rows=len(g), **{m: mh(g, m) for m in ("primary", "v1_refit", "train_only", "hgb", best_base)}))
        # months after today excluded
        g = S[~S.future_month]
        R["targets"][k]["primary_wape_excluding_months_after_today"] = mh(g, "primary")
        R["targets"][k]["baseline_wape_excluding_months_after_today"] = mh(g, best_base)
        # weak spots
        for label, sel in (("all horizons", S.horizon >= 1), ("horizon 12", S.horizon == 12), ("horizons 9-12", S.horizon >= 9), ("horizon 1-3", S.horizon <= 3)):
            g = S[sel]
            weak.append(dict(target=k, slice=label, sector="all", rows=len(g), **{m: mh(g, m) if label.startswith("all") or "-" in label else wape(g, m) for m in ("primary", "cv_blend", "train_only", "v1_refit", "hgb", best_base)}))
        for sec, g in S.groupby("sector"):
            weak.append(dict(target=k, slice="all horizons", sector=sec, rows=len(g), **{m: mh(g, m) for m in ("primary", "cv_blend", "train_only", "v1_refit", "hgb", best_base)}))
            g12 = g[g.horizon == 12]
            weak.append(dict(target=k, slice="horizon 12", sector=sec, rows=len(g12), **{m: wape(g12, m) for m in ("primary", "cv_blend", "train_only", "v1_refit", "hgb", best_base)}))
        # intervals
        for label, lo_c, hi_c in (("primary", "primary_lo", "primary_hi"), ("v1_refit", "v1_refit_lo", "v1_refit_hi")):
            inside = (S.actual_log >= S[lo_c]) & (S.actual_log <= S[hi_c])
            for h, g in S.groupby("horizon"):
                cover.append(dict(target=k, intervals=label, horizon=h, coverage=float(inside[g.index].mean()), mean_width_pct=float(100 * (np.exp(g[hi_c] - g[lo_c]) - 1).mean())))
            R["targets"][k][f"interval_coverage_{label}"] = float(inside.mean())
        # equity at h=6 and h=1..12 mean
        g6 = S[S.horizon == 6]
        tiers = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv").groupby("Econ_Tier").District_Name.nunique()
        overall6 = wape(g6, "primary")
        for t, g in g6.groupby("Econ_Tier"):
            equity.append(dict(target=k, tier=t, districts=int(tiers[t]), wape_h6=wape(g, "primary"), ratio_to_overall=wape(g, "primary") / overall6, baseline_ratio=wape(g, best_base) / wape(g6, best_base)))
        # Phase 1 scorecard
        pr, bb = mh(S, "primary"), mh(S, best_base)
        sn = min(mh(S, "seasonal_naive_drift"), mh(S, "last_value"))
        h1, h12 = wape(S[S.horizon == 1], "primary"), wape(S[S.horizon == 12], "primary")
        target_wape = {"E": 2.0, "V": 7.0, "S": 6.0}[k]
        score_rows.append(dict(target=k, wape_mean_horizon=pr, phase1_wape_limit=target_wape, within_limit=pr <= target_wape, best_baseline=best_base, improvement_over_best_baseline_pct=100 * (1 - pr / bb),
                               improvement_over_phase1_baseline_pct=100 * (1 - pr / sn), meets_20pct=(1 - pr / sn) >= 0.20, h12_over_h1=h12 / h1, within_1_5x=h12 / h1 <= 1.5,
                               worst_tier_ratio_h6_all=max(e["ratio_to_overall"] for e in equity if e["target"] == k),
                               worst_tier_ratio_h6_4plus_districts=max(e["ratio_to_overall"] for e in equity if e["target"] == k and e["districts"] >= 4)))
        R["targets"][k].update(primary_wape=pr, best_baseline_wape=bb, v1_refit_wape=mh(S, "v1_refit"), train_only_wape=mh(S, "train_only"), hgb_wape=mh(S, "hgb"))
    # series with the largest errors for the primary model
    worst = []
    for k in "EVS":
        S = PRED[k][~PRED[k].shock.to_numpy()]
        for sid, g in S.groupby("Series_ID"):
            worst.append(dict(target=k, Series_ID=sid, wape=mh(g, "primary"), baseline=mh(g, "last_plus_seasonal_shift")))
    W = pd.DataFrame(worst)
    for name, rows in (("overall", overall), ("by_horizon", by_h), ("by_slice", by_slice), ("weak_spots", weak), ("interval_coverage", cover), ("equity_h6", equity), ("phase1_scorecard", score_rows)):
        pd.DataFrame(rows).to_csv(TBL / f"{name}.csv", index=False)
    W.sort_values("wape", ascending=False).groupby("target").head(15).to_csv(TBL / "worst_series.csv", index=False)
    # bootstrap by horizon vs best baseline for the primary model
    bh = []
    for k in "EVS":
        S = PRED[k][~PRED[k].shock.to_numpy()].reset_index(drop=True)
        A, D = matrices(S, ["primary", R["targets"][k]["best_baseline"]])
        lo, hi = bootstrap_diff(A, D, "primary", R["targets"][k]["best_baseline"], rng, by_horizon=True)
        for h in range(12):
            bh.append(dict(target=k, horizon=h + 1, ci_low=lo[h], ci_high=hi[h]))
    pd.DataFrame(bh).to_csv(TBL / "primary_minus_baseline_by_horizon_ci.csv", index=False)
    json.dump(R, open(OUT_RES, "w"), indent=1, default=float)
    if not dry:
        log["runs"][-1]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        log["runs"][-1]["seconds"] = round(time.time() - t0)
        json.dump(log, open(LOG, "w"), indent=1)
    print(pd.DataFrame(overall)[["target", "model", "wape_mean_horizon", "wape_pooled", "diff_primary_minus_model", "diff_ci_low", "diff_ci_high"]].round(3).to_string(), flush=True)
    print(pd.DataFrame(score_rows).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
