#!/usr/bin/env python3
"""
Phase 8 - diagnostic figures and tables from the saved evaluation predictions (no model is changed here).

Figures in reports/evaluation/figures/:
    d01_wape_by_horizon     WAPE by horizon, primary vs baselines vs challenger vs Phase 7 configuration
    d02_residuals           histogram of log errors and error spread by horizon
    d03_pred_vs_actual      predicted vs actual (log counts), horizon 6
    d04_shap_importance     mean |SHAP| of the 12 most influential features per target (XGBoost TreeSHAP of the first seed model)
    d05_error_heatmap       WAPE by sector and target year
    d06_interval_coverage   observed coverage of the 90% intervals by horizon, new vs Phase 7 intervals
    d07_weak_spots          seekers at 12 months and IT-ITeS vacancies: monthly totals, actual vs predicted
    d08_bias                mean signed log error by horizon
Tables: reports/evaluation/test/shap_importance.csv, gain_importance.csv.
Run: python src/evaluation/diagnostics.py [--dry-run]
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import lmis_data as ld  # noqa: E402
import splits as sp  # noqa: E402
from predict import Forecaster  # noqa: E402

DRY = "--dry-run" in sys.argv
OUT = ROOT / "reports" / "evaluation"
TBL = OUT / ("dryrun" if DRY else "test")
FIG = OUT / ("dryrun_figures" if DRY else "figures")
COL = {"cv_blend": "#2da44e", "primary": "#1f6feb", "train_only": "#7aa7f7", "v1_refit": "#8957e5", "hgb": "#d29922", "last_plus_seasonal_shift": "#6e7781", "last_value": "#b1bac4", "seasonal_naive_drift": "#cf222e"}
LAB = {"cv_blend": "Phase 8 model + fold-chosen blend", "primary": "Phase 8 model (declared)", "train_only": "Phase 8, train only", "v1_refit": "Phase 7 settings", "hgb": "HistGradientBoosting", "last_plus_seasonal_shift": "last value + seasonal shift",
       "last_value": "last value", "seasonal_naive_drift": "seasonal naive + drift"}
NAME = {"E": "Employed workers", "V": "Job vacancies", "S": "Registered seekers"}


def wape(g, c):
    a, p = np.exp(g.actual_log.to_numpy()), np.exp(g[c].to_numpy())
    return 100 * np.abs(a - p).sum() / a.sum()


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    pred = pd.read_parquet(ROOT / "data" / "interim" / ("phase8_dryrun_predictions.parquet" if DRY else "phase8_test_predictions.parquet"))
    P = {k: pred[pred.target == k].reset_index(drop=True) for k in "EVS"}
    S = {k: v[~v.shock] for k, v in P.items()}
    # d01
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for a, k in zip(ax, "EVS"):
        for m in ("last_value", "seasonal_naive_drift", "last_plus_seasonal_shift", "hgb", "v1_refit", "cv_blend", "primary"):
            hs = sorted(S[k].horizon.unique())
            a.plot(hs, [wape(S[k][S[k].horizon == h], m) for h in hs], color=COL[m], lw=2.6 if m == "primary" else 1.4, marker="o" if m == "primary" else None, ms=4, label=LAB[m])
        a.set_title(NAME[k]); a.set_xlabel("horizon (months)"); a.set_ylabel("WAPE %"); a.grid(alpha=.3)
    ax[0].legend(fontsize=8)
    fig.suptitle("Test WAPE by forecast horizon" if not DRY else "DRY RUN (validation rows)", y=1.02)
    fig.tight_layout(); fig.savefig(FIG / "d01_wape_by_horizon.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d02 residuals
    fig, ax = plt.subplots(2, 3, figsize=(15, 7))
    for j, k in enumerate("EVS"):
        e = S[k].actual_log - S[k].primary
        lim = np.quantile(np.abs(e), 0.995)
        ax[0, j].hist(e.clip(-lim, lim), bins=80, color=COL["primary"], alpha=.85)
        ax[0, j].axvline(0, color="k", lw=1); ax[0, j].axvline(e.median(), color="#cf222e", ls="--", label=f"median {e.median():+.3f}")
        ax[0, j].set_title(f"{NAME[k]}: log error (actual - predicted)"); ax[0, j].legend(fontsize=8)
        hs = [h for h in (1, 3, 6, 9, 12) if h in set(S[k].horizon)]
        ax[1, j].boxplot([(S[k][S[k].horizon == h].actual_log - S[k][S[k].horizon == h].primary).clip(-lim, lim) for h in hs], labels=hs, showfliers=False)
        ax[1, j].axhline(0, color="k", lw=1); ax[1, j].set_xlabel("horizon"); ax[1, j].set_ylabel("log error")
    fig.tight_layout(); fig.savefig(FIG / "d02_residuals.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d03
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    rng = np.random.default_rng(1)
    for a, k in zip(ax, "EVS"):
        g = S[k][S[k].horizon == 6]
        g = g.iloc[rng.choice(len(g), min(4000, len(g)), replace=False)]
        a.scatter(g.actual_log, g.primary, s=4, alpha=.35, color=COL["primary"])
        lo, hi = g.actual_log.min(), g.actual_log.max()
        a.plot([lo, hi], [lo, hi], "k", lw=1); a.set_title(f"{NAME[k]}, horizon 6 (WAPE {wape(S[k][S[k].horizon == 6], 'primary'):.1f}%)"); a.set_xlabel("actual (log count)"); a.set_ylabel("predicted")
    fig.tight_layout(); fig.savefig(FIG / "d03_pred_vs_actual.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d04 SHAP
    split_df = sp.load_split("validation") if DRY else sp.load_split("test", unlock_test=True, verify=True)
    fc = Forecaster.load(ROOT / "models" / "xgboost_v2" / "primary")
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    shap_rows, gain_rows = [], []
    for a, k in zip(ax, "EVS"):
        p = fc.params[k]
        samp = split_df.sample(min(20000, len(split_df)), random_state=0)
        Z = fc.pre[k].transform(samp[p["features"]])
        contrib = fc.models[k][0].get_booster().predict(xgb.DMatrix(Z), pred_contribs=True)[:, :-1]
        imp = pd.Series(np.abs(contrib).mean(0), index=p["features"]).sort_values(ascending=False)
        gain = pd.Series(fc.models[k][0].get_booster().get_score(importance_type="total_gain")).reindex(p["features"]).fillna(0)
        gain = gain / gain.sum()
        shap_rows += [dict(target=k, feature=f, mean_abs_shap=v, share=v / imp.sum()) for f, v in imp.items()]
        gain_rows += [dict(target=k, feature=f, gain_share=v) for f, v in gain.sort_values(ascending=False).items()]
        top = imp.head(12)[::-1]
        a.barh(top.index, top.values, color=COL["primary"]); a.set_title(f"{NAME[k]}: mean |SHAP| (log change)"); a.tick_params(axis="y", labelsize=8)
    fig.tight_layout(); fig.savefig(FIG / "d04_shap_importance.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    pd.DataFrame(shap_rows).to_csv(TBL / "shap_importance.csv", index=False)
    pd.DataFrame(gain_rows).to_csv(TBL / "gain_importance.csv", index=False)
    # d05 heatmap
    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    for a, k in zip(ax, "EVS"):
        g = S[k].assign(year=S[k].target_date.dt.year)
        tab = pd.DataFrame({y: {s: wape(d, "primary") for s, d in gg.groupby("sector")} for y, gg in g.groupby("year")})
        im = a.imshow(tab.values, cmap="YlOrRd", aspect="auto")
        a.set_xticks(range(tab.shape[1])); a.set_xticklabels(tab.columns); a.set_yticks(range(tab.shape[0])); a.set_yticklabels([s[:18] for s in tab.index], fontsize=8)
        for i in range(tab.shape[0]):
            for j in range(tab.shape[1]):
                a.text(j, i, f"{tab.values[i, j]:.1f}", ha="center", va="center", fontsize=8)
        a.set_title(f"{NAME[k]}: WAPE % by sector and year")
    fig.tight_layout(); fig.savefig(FIG / "d05_error_heatmap.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d06 coverage
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for a, k in zip(ax, "EVS"):
        for lab, lo, hi, c in (("Phase 8 intervals", "primary_lo", "primary_hi", COL["primary"]), ("Phase 7 intervals", "v1_refit_lo", "v1_refit_hi", COL["v1_refit"])):
            g = S[k]
            cov = ((g.actual_log >= g[lo]) & (g.actual_log <= g[hi])).groupby(g.horizon).mean() * 100
            a.plot(cov.index, cov.values, marker="o", color=c, label=lab)
        a.axhline(90, color="k", ls="--", lw=1); a.set_ylim(30, 100); a.set_title(NAME[k]); a.set_xlabel("horizon"); a.set_ylabel("coverage %"); a.grid(alpha=.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "d06_interval_coverage.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d07 weak spots
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    g = S["S"][S["S"].horizon == 12]
    if len(g):
        t = g.groupby("target_date").apply(lambda d: pd.Series({"actual": np.exp(d.actual_log).sum(), **{m: np.exp(d[m]).sum() for m in ("primary", "cv_blend", "v1_refit", "last_plus_seasonal_shift")}}), include_groups=False)
        ax[0].plot(t.index, t.actual, "k", lw=2, label="actual")
        for m in ("primary", "cv_blend", "v1_refit", "last_plus_seasonal_shift"):
            ax[0].plot(t.index, t[m], color=COL[m], label=LAB[m])
        ax[0].set_title("Seekers, 12 months ahead: all districts and sectors"); ax[0].legend(fontsize=8)
    for a, (k, title) in zip(ax[1:], (("V", "IT-ITeS vacancies, horizon 6"), ("S", "IT-ITeS seekers, horizon 6"))):
        g = S[k][(S[k].sector.str.contains("IT")) & (S[k].horizon == 6)]
        if len(g):
            t = g.groupby("target_date").apply(lambda d: pd.Series({"actual": np.exp(d.actual_log).sum(), "primary": np.exp(d.primary).sum(), "base": np.exp(d.last_plus_seasonal_shift).sum()}), include_groups=False)
            a.plot(t.index, t.actual, "k", lw=2, label="actual"); a.plot(t.index, t.primary, color=COL["primary"], label="Phase 8 model"); a.plot(t.index, t.base, color=COL["last_plus_seasonal_shift"], label="baseline")
            a.set_title(title); a.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "d07_weak_spots.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    # d08 bias
    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    for a, k in zip(ax, "EVS"):
        for m in ("primary", "v1_refit", "last_plus_seasonal_shift"):
            b = (S[k].actual_log - S[k][m]).groupby(S[k].horizon).mean()
            a.plot(b.index, b.values, marker="o", ms=3, color=COL[m], label=LAB[m])
        a.axhline(0, color="k", lw=1); a.set_title(f"{NAME[k]}: mean log error (positive = under-forecast)"); a.set_xlabel("horizon"); a.grid(alpha=.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "d08_bias.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
