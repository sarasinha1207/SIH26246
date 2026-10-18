#!/usr/bin/env python3
"""
Phase 6 - analyse the model comparison (train + validation periods only).

Reads data/interim/phase6_predictions.parquet and writes reports/models/m*.csv, figures and data/processed/models/model_selection.json.
Scores are WAPE on counts (sum |error| / sum actual).  Differences between models are tested with a paired bootstrap over series
(500 resamples of the 280 series), so a gain is only called real when the 95% interval excludes zero.

Run: python src/models/analyze_models.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports" / "models"
SELECT = ROOT / "data" / "processed" / "models" / "model_selection.json"
TNAME = {"E": "Employed workers", "V": "Job vacancies", "S": "Registered seekers"}
BASELINES = ["last_value", "seasonal_naive_drift", "last_plus_seasonal_shift", "sm3_plus_seasonal_shift"]
STAT = ["holt_winters"]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"], "font.size": 9, "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True})


def wape(a, p):
    return 100 * np.abs(a - p).sum() / a.sum()


def score(df):
    return wape(np.exp(df.actual_log.to_numpy()), np.exp(df.pred_log.to_numpy()))


def main():
    REP.mkdir(parents=True, exist_ok=True)
    P = pd.read_parquet(ROOT / "data" / "interim" / "phase6_predictions.parquet")
    P["a"], P["p"] = np.exp(P.actual_log), np.exp(P.pred_log)
    models = sorted(P.model.unique())
    ds = pd.read_csv(ROOT / "data" / "processed" / "dim_series.csv", dtype={"District_LGD_Code": str})
    P = P.merge(ds[["Series_ID", "Sector_Name", "Econ_Tier"]].rename(columns={"Series_ID": "series"}), on="series", how="left")

    # ---- m01/m02: WAPE by fold and mean ------------------------------------------------------------------------------
    g = P.groupby(["target", "fold", "model"]).apply(lambda d: wape(d.a, d.p), include_groups=False).rename("wape").reset_index()
    g.round(3).to_csv(REP / "m01_wape_by_fold.csv", index=False)
    mean = g.groupby(["target", "model"]).wape.mean().unstack("target")
    mean["mean_all_targets"] = mean.mean(axis=1)
    f3 = g[g.fold == "F3_2024"].pivot(index="model", columns="target", values="wape")
    mean = mean.join(f3.add_prefix("F3_"))
    mean = mean.sort_values("mean_all_targets")
    mean.round(3).to_csv(REP / "m02_wape_mean.csv")
    print(mean.round(2))

    # ---- m03/m04/m05 breakdowns ---------------------------------------------------------------------------------------
    byh = P.groupby(["target", "model", "horizon"]).apply(lambda d: wape(d.a, d.p), include_groups=False).rename("wape").reset_index()
    byh.round(3).to_csv(REP / "m03_wape_by_horizon.csv", index=False)
    bys = P.groupby(["target", "model", "Sector_Name"]).apply(lambda d: wape(d.a, d.p), include_groups=False).rename("wape").reset_index()
    bys.round(3).to_csv(REP / "m04_wape_by_sector.csv", index=False)
    h6 = P[P.horizon == 6]
    eq = []
    for (k, mdl), d in h6.groupby(["target", "model"]):
        overall = wape(d.a, d.p)
        tier = d.groupby("Econ_Tier").apply(lambda x: wape(x.a, x.p), include_groups=False)
        n_dist = d.groupby("Econ_Tier").series.nunique()
        eq.append(dict(target=k, model=mdl, overall=overall, worst_tier=tier.idxmax(), worst_tier_wape=tier.max(), ratio=tier.max() / overall,
                       ratio_tiers_with_4plus_districts=(tier[n_dist >= 20].max() / overall) if (n_dist >= 20).any() else np.nan))
    pd.DataFrame(eq).round(3).to_csv(REP / "m05_equity_by_tier_h6.csv", index=False)

    # ---- m06: paired bootstrap against references --------------------------------------------------------------------------
    rng = np.random.default_rng(42)
    series = np.array(sorted(P.series.unique()))
    boot = []
    for k in "EVS":
        d = P[P.target == k]
        piv_a = d[d.model == "last_value"].set_index(["fold", "row"]).a
        by_series = {}
        for mdl in models:
            x = d[d.model == mdl].set_index(["fold", "row"])
            by_series[mdl] = x.assign(err=np.abs(x.p - x.a)).groupby("series").agg(err=("err", "sum"), act=("a", "sum"))
        base_name = min(BASELINES, key=lambda m: wape(*(d[d.model == m][["a", "p"]].to_numpy().T)))
        ref_names = {"best_baseline": base_name, "holt_winters": "holt_winters", "lightgbm": "lightgbm"}
        draws = rng.integers(0, len(series), size=(500, len(series)))
        for mdl in models:
            for rname, ref in ref_names.items():
                if mdl == ref:
                    continue
                e1, e0 = by_series[mdl].reindex(series), by_series[ref].reindex(series)
                diffs = []
                for idx in draws:
                    diffs.append(100 * (e1.err.to_numpy()[idx].sum() - e0.err.to_numpy()[idx].sum()) / e0.act.to_numpy()[idx].sum())
                diffs = np.array(diffs)
                boot.append(dict(target=k, model=mdl, reference=f"{rname}={ref}", mean_diff_pts=diffs.mean(), ci_low=np.percentile(diffs, 2.5),
                                 ci_high=np.percentile(diffs, 97.5), share_better=float((diffs < 0).mean())))
    bt = pd.DataFrame(boot)
    bt.round(3).to_csv(REP / "m06_bootstrap_differences.csv", index=False)

    # pooled over the three targets (equal weight, same resampled series for every target)
    pooled = []
    err = {}
    for k in "EVS":
        d = P[P.target == k]
        for mdl in models:
            x = d[d.model == mdl]
            err[(k, mdl)] = x.assign(e=np.abs(x.p - x.a)).groupby("series").agg(err=("e", "sum"), act=("a", "sum")).reindex(series)
    draws = np.random.default_rng(43).integers(0, len(series), size=(500, len(series)))
    for ref in ("lightgbm", "hist_gbm", "xgboost"):
        for mdl in models:
            if mdl == ref:
                continue
            diffs = np.zeros(len(draws))
            for k in "EVS":
                e1, e0 = err[(k, mdl)], err[(k, ref)]
                diffs += np.array([100 * (e1.err.to_numpy()[i].sum() - e0.err.to_numpy()[i].sum()) / e0.act.to_numpy()[i].sum() for i in draws]) / 3
            pooled.append(dict(model=mdl, reference=ref, mean_diff_pts=diffs.mean(), ci_low=np.percentile(diffs, 2.5), ci_high=np.percentile(diffs, 97.5),
                               share_better=float((diffs < 0).mean())))
    pd.DataFrame(pooled).round(3).to_csv(REP / "m06b_bootstrap_pooled.csv", index=False)

    # ---- m07: simple blends of log forecasts ------------------------------------------------------------------------------
    ml = [m for m in models if m in ("lightgbm", "hist_gbm", "xgboost", "random_forest", "mlp", "ridge", "lightgbm_per_horizon")]
    blends = {"lightgbm+holt_winters": ["lightgbm", "holt_winters"], "lightgbm+hist_gbm": ["lightgbm", "hist_gbm"],
              "lightgbm+hist_gbm+random_forest": ["lightgbm", "hist_gbm", "random_forest"], "lightgbm+hist_gbm+xgboost": ["lightgbm", "hist_gbm", "xgboost"],
              "lightgbm+holt_winters+last_plus_seasonal_shift": ["lightgbm", "holt_winters", "last_plus_seasonal_shift"]}
    rows = []
    for name, parts in blends.items():
        if not set(parts) <= set(models):
            continue
        for (k, fold), d in P.groupby(["target", "fold"]):
            pv = d[d.model.isin(parts)].pivot_table(index="row", columns="model", values="pred_log")
            actual = d[d.model == parts[0]].set_index("row").actual_log.reindex(pv.index)
            rows.append(dict(target=k, fold=fold, blend=name, wape=wape(np.exp(actual.to_numpy()), np.exp(pv.mean(axis=1).to_numpy()))))
    bl = pd.DataFrame(rows)
    bl.round(3).to_csv(REP / "m07_blends.csv", index=False)
    bmean = bl.groupby(["blend", "target"]).wape.mean().unstack("target")
    bmean["mean_all_targets"] = bmean.mean(axis=1)
    bmean.round(3).to_csv(REP / "m07_blends_mean.csv")

    # ---- m08: timings and scorecard -------------------------------------------------------------------------------------------
    tm = pd.read_csv(REP / "compare_timings.csv").groupby("model").seconds.mean().round(1)
    qual = {  # NaN handling, categorical handling, interval support, interpretability (1 = poor, 3 = good)
        "lightgbm": (3, 3, 3, 2), "lightgbm_per_horizon": (3, 3, 3, 2), "hist_gbm": (3, 3, 3, 2), "xgboost": (3, 2, 3, 2), "random_forest": (1, 1, 2, 2), "ridge": (1, 1, 1, 3),
        "mlp": (1, 1, 1, 1), "holt_winters": (3, 1, 2, 3), "last_value": (3, 3, 1, 3), "seasonal_naive_drift": (3, 3, 1, 3),
        "last_plus_seasonal_shift": (3, 3, 1, 3), "sm3_plus_seasonal_shift": (3, 3, 1, 3)}
    sc = pd.DataFrame({"mean_wape": mean.mean_all_targets, "wape_range_across_folds": g.groupby("model").wape.apply(lambda s: s.max() - s.min()),
                       "avg_fit_seconds": tm})
    sc["rank_accuracy"] = sc.mean_wape.rank()
    for i, c in enumerate(["native_missing_values", "native_categoricals", "interval_support", "interpretability"]):
        sc[c] = [qual.get(m, (0, 0, 0, 0))[i] for m in sc.index]
    sc = sc.sort_values("mean_wape")
    sc.round(3).to_csv(REP / "m08_scorecard.csv")
    print(sc.round(2))

    # ---- figures ---------------------------------------------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.0))
    for ax, k in zip(axes, "EVS"):
        t = mean[k].sort_values(ascending=False)
        cols = ["#898781" if m in BASELINES else "#3987e5" if m in STAT else "#2a78d6" for m in t.index]
        ax.barh(range(len(t)), t.values, color=cols, height=0.62)
        ax.set_yticks(range(len(t)), t.index, fontsize=8)
        ax.set_title(f"{TNAME[k]}: mean WAPE (%), 3 folds", loc="left", fontsize=9, color=INK2)
        ax.grid(axis="y", visible=False)
        for i, v in enumerate(t.values):
            ax.text(v, i, f" {v:.2f}", va="center", fontsize=7.5, color=INK2)
        ax.set_xlim(0, t.max() * 1.15)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.text(0.005, 0.985, "Tree-based models lead on every target; the simple baselines trail", ha="left", va="top", fontsize=11, fontweight="semibold")
    fig.text(0.005, 0.925, "Grey: no-learning baselines; light blue: Holt-Winters; blue: global machine-learning models. Validation folds F1-F3, horizons 1/3/6/12.",
             ha="left", va="top", fontsize=8.5, color=INK2)
    fig.savefig(REP / "fig_models_overall.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    top = list(mean.mean_all_targets.sort_values().index[:3])
    show = [m for m in top if m not in BASELINES][:2] + ["holt_winters", "last_plus_seasonal_shift", "last_value"]
    cols5 = dict(zip(show, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), sharex=True)
    for ax, k in zip(axes, "EVS"):
        for m in show:
            d = byh[(byh.target == k) & (byh.model == m)]
            ax.plot(d.horizon, d.wape, color=cols5[m], lw=1.6, marker="o", ms=3.5)
        ax.set_xticks([1, 3, 6, 12])
        ax.set_title(f"{TNAME[k]}: WAPE (%) by horizon", loc="left", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.80))
    fig.legend([plt.Line2D([0], [0], color=cols5[m], lw=2) for m in show], show, loc="upper left", ncol=5, bbox_to_anchor=(0.0, 0.855), fontsize=8, frameon=False,
               labelcolor=INK2)
    fig.text(0.005, 0.985, "Error rises with horizon; the learned models lead except for seekers twelve months ahead", ha="left", va="top", fontsize=11, fontweight="semibold")
    fig.text(0.005, 0.925, "Pooled over three validation folds. Holt-Winters is far worse for seekers (e-Shram break).", ha="left", va="top", fontsize=8.5, color=INK2)
    fig.savefig(REP / "fig_models_by_horizon.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---- selection ---------------------------------------------------------------------------------------------------------------
    # Rule (written after the pooled table had been produced, so it is a judgement, not a pre-registration): the leader is the learned model with the lowest mean WAPE over the three targets and
    # folds; another model counts as tied only if its pooled paired-bootstrap interval against the leader includes zero.
    learned = [m for m in mean.index if m not in BASELINES]
    leader = mean.loc[learned, "mean_all_targets"].idxmin()
    pooled_df = pd.read_csv(REP / "m06b_bootstrap_pooled.csv")
    vs = pooled_df[pooled_df.reference == leader].set_index("model")
    tied = [m for m in learned if m != leader and m in vs.index and vs.loc[m, "ci_low"] <= 0 <= vs.loc[m, "ci_high"]]
    PREFERRED = "xgboost"          # project owner's stated preference; used ONLY to break a statistical tie with the leader
    primary = PREFERRED if (PREFERRED == leader or PREFERRED in tied) else leader
    challenger = [m for m in mean.loc[learned, "mean_all_targets"].sort_values().index if m != primary][0]
    best_base = mean.loc[BASELINES, "mean_all_targets"].idxmin()
    sel = {"created_from": "train+validation only (folds F1-F3)",
           "rule": "leader = lowest mean WAPE among learned models; tied only if the pooled bootstrap CI vs the leader includes 0; among tied models the owner's preference decides",
           "leader_by_mean_wape": leader, "tied_with_leader": tied, "primary": primary, "challenger": challenger, "best_baseline": best_base,
           "decision_basis": ("statistical tie broken by project-owner preference" if primary != leader else "lowest mean WAPE"),
           "mean_wape": {m: round(float(mean.at[m, "mean_all_targets"]), 3) for m in mean.index}, "per_target": {}}
    for k in "EVS":
        order = mean[k].sort_values()
        ref = bt[(bt.target == k) & (bt.model == order.index[0]) & (bt.reference.str.startswith("best_baseline"))].iloc[0]
        sel["per_target"][k] = dict(leader=order.index[0], mean_wape=round(float(order.iloc[0]), 3), ranking=[[m, round(float(v), 3)] for m, v in order.items()],
                                    vs_best_baseline=dict(reference=ref.reference, mean_diff_pts=round(float(ref.mean_diff_pts), 3),
                                                          ci=[round(float(ref.ci_low), 3), round(float(ref.ci_high), 3)]))
    tun = {}
    for fam in ("lightgbm", "hist_gbm", "xgboost"):
        tp = REP / f"tune_{fam}_summary.json"
        if tp.exists():
            t = json.load(open(tp))
            tun[fam] = {k: dict(default=v["default_mean_wape"], best=v["best_mean_wape"], gain_pct=v["gain_pct"], best_config=v["best_config"],
                                top5_param_ranges=v["top5_param_ranges"]) for k, v in t.items()}
    sel["tuning"] = tun
    json.dump(sel, open(SELECT, "w"), indent=2)
    print(json.dumps({k: sel[k] for k in ("leader_by_mean_wape", "tied_with_leader", "primary", "challenger", "best_baseline", "decision_basis")}, indent=1))
    for k, v in sel["per_target"].items():
        print(k, v["leader"], v["mean_wape"], v["vs_best_baseline"])


if __name__ == "__main__":
    main()
