#!/usr/bin/env python3
"""
Phase 8 - descriptive metrics requested after the evaluation: RMSE / MAE / bias per model, and a first look at forecast-based early-warning flags.
Reads the saved test predictions only; no model, weight or interval is changed.   Writes reports/evaluation/test/{full_metrics,flag_check}.csv
Run: python src/evaluation/extra_metrics.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
import splits as sp  # noqa: E402

T = ROOT / "reports" / "evaluation" / "test"
MODELS = ["primary", "cv_blend", "v1_refit", "hgb", "last_plus_seasonal_shift", "last_value", "seasonal_naive_drift"]


def auc(score, y):
    r = pd.Series(score).rank().to_numpy()
    n1, n0 = y.sum(), (~y).sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    pred = pd.read_parquet(ROOT / "data" / "interim" / "phase8_test_predictions.parquet")
    rows = []
    for k in "EVS":
        S = pred[(pred.target == k) & ~pred.shock]
        a = np.exp(S.actual_log.to_numpy())
        for m in MODELS:
            p = np.exp(S[m].to_numpy())
            e = a - p
            hz = [100 * np.abs(a[S.horizon == h] - p[(S.horizon == h).to_numpy()]).sum() / a[S.horizon == h].sum() for h in range(1, 13)]
            rows.append(dict(target=k, model=m, wape_mean_horizon=np.mean(hz), wape_pooled=100 * np.abs(e).sum() / a.sum(), mae_count=np.abs(e).mean(), rmse_count=np.sqrt((e ** 2).mean()),
                             mae_log=np.abs(S.actual_log - S[m]).mean(), rmse_log=np.sqrt(((S.actual_log - S[m]) ** 2).mean()), bias_log=(S.actual_log - S[m]).mean(),
                             median_ape_pct=100 * np.median(np.abs(e) / a), r2_log=1 - ((S.actual_log - S[m]) ** 2).sum() / ((S.actual_log - S.actual_log.mean()) ** 2).sum(), rows=len(S)))
    pd.DataFrame(rows).to_csv(T / "full_metrics.csv", index=False)
    # ---- forecast-based flags: percentile of V/S coverage among the 56 districts of a sector in the target month
    test = sp.load_split("test", unlock_test=True, verify=True, columns=["Series_ID", "sector", "origin_idx", "target_idx", "horizon", "last_V", "last_S"])
    pv, ps = pred[pred.target == "V"].reset_index(drop=True), pred[pred.target == "S"].reset_index(drop=True)
    d = test.copy()
    d["act_cov"] = np.exp(pv.actual_log - ps.actual_log)
    d["fc_cov"] = np.exp(pv.primary - ps.cv_blend)
    d["fc_cov_primary"] = np.exp(pv.primary - ps.primary)
    d["now_cov"] = np.exp(d.last_V - d.last_S)
    d["lo"] = np.exp(pv.primary_lo - ps.primary_hi)
    d["hi"] = np.exp(pv.primary_hi - ps.primary_lo)
    d["ramp"] = ps["shock"].to_numpy()
    d = d[~d.ramp]
    out = []
    for h in (1, 3, 6, 12):
        g = d[d.horizon == h].copy()
        for c in ("act_cov", "fc_cov", "fc_cov_primary", "now_cov"):
            g[c + "_pct"] = g.groupby(["sector", "target_idx"])[c].rank(pct=True) * 100 if c != "now_cov" else g.groupby(["sector", "origin_idx"])[c].rank(pct=True) * 100
        for label, test_ev, col_event in (("tightest decile (shortage)", lambda x: x >= 90, 1), ("loosest decile (saturation)", lambda x: x <= 10, 0)):
            y = test_ev(g.act_cov_pct).to_numpy()
            for name, c in (("persistence (today's percentile)", "now_cov_pct"), ("model forecast (blended seekers)", "fc_cov_pct"), ("model forecast (declared seekers)", "fc_cov_primary_pct")):
                f = test_ev(g[c]).to_numpy()
                score = g[c].to_numpy() if col_event else -g[c].to_numpy()
                out.append(dict(horizon=h, event=label, flag_source=name, base_rate=float(y.mean()), precision=float((f & y).sum() / max(f.sum(), 1)), recall=float((f & y).sum() / max(y.sum(), 1)), auc=auc(score, y), rows=len(g)))
        inside = ((g.act_cov >= g.lo) & (g.act_cov <= g.hi)).mean()
        out.append(dict(horizon=h, event="actual coverage ratio inside [V_lo/S_hi, V_hi/S_lo]", flag_source="intervals", base_rate=np.nan, precision=float(inside), recall=np.nan, auc=np.nan, rows=len(g)))
        out.append(dict(horizon=h, event="rank correlation, forecast vs actual percentile", flag_source="model forecast (blended seekers)", base_rate=np.nan,
                        precision=float(g.fc_cov_pct.corr(g.act_cov_pct, method="spearman")), recall=np.nan, auc=np.nan, rows=len(g)))
        out.append(dict(horizon=h, event="rank correlation, today vs actual percentile", flag_source="persistence", base_rate=np.nan,
                        precision=float(g.now_cov_pct.corr(g.act_cov_pct, method="spearman")), recall=np.nan, auc=np.nan, rows=len(g)))
    pd.DataFrame(out).to_csv(T / "flag_check.csv", index=False)
    print("done")


if __name__ == "__main__":
    main()
