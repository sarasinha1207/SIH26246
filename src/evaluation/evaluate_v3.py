#!/usr/bin/env python3
"""
Phase 8 - evaluate the declared configuration (models/xgboost_v3: blend from the folds for every target + adaptive conformal intervals) on a data source, with NO refitting.

    python src/evaluation/evaluate_v3.py original          the original 2023-2026 test split (already spent: this is a post-hoc re-scoring)
    python src/evaluation/evaluate_v3.py fresh 2027        a fresh synthetic draw built by make_fresh_draw.py (never seen by any model or decision)

Compared on the same rows: v3 (declared), v2 primary (seekers blend vetoed), Phase 7 settings refitted, HistGradientBoosting, and the baselines.
Intervals: the static fold-based intervals vs the adaptive conformal ones (settings declared in models/xgboost_v3/conformal.json, chosen before this run).
Writes reports/evaluation/v3/<source>/*.csv and results.json.
"""
import json
import sys
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
from conformal import adaptive_intervals, interval_metrics  # noqa: E402
from evaluate import bootstrap_diff, matrices, mh, wape  # noqa: E402

V2, V3 = ROOT / "models" / "xgboost_v2", ROOT / "models" / "xgboost_v3"
BASE = {"E": "seasonal_naive_drift", "V": "last_plus_seasonal_shift", "S": "last_plus_seasonal_shift"}


def load(source, seed):
    if source == "original":
        return sp.load_split("validation"), sp.load_split("test", unlock_test=True, verify=True), ROOT / "reports" / "evaluation" / "v3" / "original"
    d = ROOT / "data" / "fresh_draws" / f"seed_{seed}" / "data" / "splits"
    return pd.read_parquet(d / "validation.parquet"), pd.read_parquet(d / "test.parquet"), ROOT / "reports" / "evaluation" / "v3" / f"fresh_{seed}"


def main():
    source = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    val, test, out = load(source, seed)
    out.mkdir(parents=True, exist_ok=True)
    decl = json.load(open(V3 / "declaration.json"))
    for name, digest in decl["files_sha256"].items():
        assert sp.sha256(V3 / name) == digest, f"{name} changed after the declaration"
    cfg = json.load(open(V3 / "conformal.json"))
    fc3, fc2, fc1 = Forecaster.load(V3 / "primary"), Forecaster.load(V2 / "primary"), Forecaster.load(V2 / "v1_refit")
    fc_tr = Forecaster.load(V2 / "train_only")
    fc_tr.blend = fc3.blend                                   # same blend for the calibration errors
    R3, R2, R1, Rt = fc3.predict(test), fc2.predict(test), fc1.predict(test), fc_tr.predict(val)
    results = {"source": source if seed is None else f"fresh draw seed {seed}", "test_rows": int(len(test)), "series": int(test.Series_ID.nunique()), "targets": {}}
    metric_rows, int_rows, h_rows, alpha_rows = [], [], [], []
    rng = np.random.default_rng(5)
    for k in "EVS":
        sk = ld.spec()[k]
        shock = "target_in_shock_S" if k == "S" else "target_in_shock_EV"
        P = test[["Series_ID", "sector", "origin_idx", "target_idx", "horizon"]].copy()
        P["actual_log"] = test[f"target_{k}"].to_numpy()
        P["v3"], P["v2_primary"], P["v1_refit"] = R3[f"pred_log_{k}"].to_numpy(), R2[f"pred_log_{k}"].to_numpy(), R1[f"pred_log_{k}"].to_numpy()
        P["hgb"] = test[f"{sk['base']}_{k}"].to_numpy() + joblib.load(V2 / "challenger_hgb" / f"{k}.joblib").predict(test[sk["features"]])
        for b in ("last_plus_seasonal_shift", "last_value", "seasonal_naive_drift"):
            P[b] = ld.baseline_log(test, k, b)
        P["excl"] = test[shock].to_numpy()
        S = P[~P.excl].reset_index(drop=True)
        A, D = matrices(S, ["v3", "v2_primary", "v1_refit", "hgb", BASE[k]])
        for m in ("v3", "v2_primary", "v1_refit", "hgb", "last_plus_seasonal_shift", "last_value", "seasonal_naive_drift"):
            row = dict(target=k, model=m, wape_mean_horizon=mh(S, m), wape_pooled=wape(S, m), rmse_count=float(np.sqrt(((np.exp(S.actual_log) - np.exp(S[m])) ** 2).mean())),
                       mae_count=float(np.abs(np.exp(S.actual_log) - np.exp(S[m])).mean()), bias_log=float((S.actual_log - S[m]).mean()))
            if m not in ("v3", "last_value", "seasonal_naive_drift") and m in A:
                lo, hi = bootstrap_diff(A, D, "v3", m, rng)
                row.update(v3_minus_this=mh(S, "v3") - mh(S, m), ci_low=lo, ci_high=hi)
            metric_rows.append(row)
        for h, g in S.groupby("horizon"):
            h_rows.append(dict(target=k, horizon=h, **{m: wape(g, m) for m in ("v3", "v2_primary", "v1_refit", "hgb", "last_plus_seasonal_shift")}))
        # ---- intervals
        static_lo = np.array([fc3.intervals[k][str(int(h))][0] for h in P.horizon])
        static_hi = np.array([fc3.intervals[k][str(int(h))][1] for h in P.horizon])
        R = P.rename(columns={"actual_log": "y", "v3": "pred"})[["sector", "horizon", "origin_idx", "target_idx", "y", "pred", "excl"]].copy()
        R["static_lo"], R["static_hi"] = static_lo, static_hi
        C0 = pd.DataFrame({"sector": val.sector.to_numpy(), "horizon": val.horizon.to_numpy(), "target_idx": val.target_idx.to_numpy(), "resid": val[f"target_{k}"].to_numpy() - Rt[f"pred_log_{k}"].to_numpy(),
                           "excl": val[shock].to_numpy()})
        lo, hi, used, al = adaptive_intervals(R, C0, window=cfg["window"], gamma=cfg["gamma"], alpha=cfg["alpha"], n_min=cfg["n_min"], alpha_range=tuple(cfg["alpha_range"]))
        al["target"] = k
        alpha_rows.append(al)
        ms, ma = interval_metrics(R, static_lo, static_hi), interval_metrics(R, lo, hi)
        for lab, m in (("static (fold-based)", ms), ("adaptive conformal", ma)):
            int_rows.append(dict(target=k, intervals=lab, coverage=m["coverage"], width_pct=m["width_pct"], interval_score=m["interval_score"],
                                 coverage_h1=m["by_horizon"].coverage.loc[1], coverage_h6=m["by_horizon"].coverage.loc[6], coverage_h12=m["by_horizon"].coverage.loc[12],
                                 width_h12=m["by_horizon"].width_pct.loc[12], share_rows_adaptive=float(used[~R.excl.to_numpy()].mean()) if lab.startswith("adaptive") else 0.0))
            for h, r in m["by_horizon"].iterrows():
                h_rows.append(dict(target=k, horizon=h, **{f"{lab.split()[0]}_coverage": r.coverage, f"{lab.split()[0]}_width_pct": r.width_pct}))
        results["targets"][k] = dict(v3=mh(S, "v3"), v2_primary=mh(S, "v2_primary"), baseline=mh(S, BASE[k]), scored_rows=int(len(S)))
        np.save(out / f"adaptive_lo_{k}.npy", lo)
        np.save(out / f"adaptive_hi_{k}.npy", hi)
    M, I = pd.DataFrame(metric_rows), pd.DataFrame(int_rows)
    M.to_csv(out / "metrics.csv", index=False)
    I.to_csv(out / "intervals.csv", index=False)
    pd.concat(alpha_rows).to_csv(out / "alpha_path.csv", index=False)
    H = pd.DataFrame(h_rows)
    H.groupby(["target", "horizon"]).first().reset_index().to_csv(out / "by_horizon.csv", index=False)
    json.dump(results, open(out / "results.json", "w"), indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(M.round(3).to_string(index=False)); print(I.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
