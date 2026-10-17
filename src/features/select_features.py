#!/usr/bin/env python3
"""
Phase 5 - feature selection experiments (train + validation periods only; the test period is never loaded).

A fixed LightGBM "probe" (not the final model; that is Phase 6) is trained on expanding-window folds and scored by WAPE on the
level scale.  Folds (all targets, horizons 1/3/6/12):
    F1  train targets <= 2017-12, validate 2018        F2  train <= 2018-12, validate 2019        F3  train <= 2023-12, validate 2024
Steps: A) which base the model predicts relative to   B) training policy (mask shock windows, recency weights)
       C) group ablation (drop-one from the full set, add-one to a core set)   D) final feature set + correlation pruning
       E) permutation importance on F3   F) final vs full vs core vs baselines.

Outputs: reports/features/*.csv, data/processed/features/feature_sets.json, feature_catalog.csv
Run:     python src/features/select_features.py [--quick]
"""
import json
import sys
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402

warnings.filterwarnings("ignore")
REP, FEAT = ROOT / "reports" / "features", ROOT / "data" / "processed" / "features"
QUICK = "--quick" in sys.argv
HORIZONS = (1, 3, 6, 12)
PROBE = dict(objective="regression", n_estimators=250, learning_rate=0.08, num_leaves=31, min_child_samples=100, feature_fraction=0.8,
             bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, n_jobs=-1, verbose=-1, random_state=42)
FOLDS = {"F1_2018": ("2017-12-01", 2018), "F2_2019": ("2018-12-01", 2019), "F3_2024": ("2023-12-01", 2024)}
if QUICK:
    FOLDS = {"F3_2024": FOLDS["F3_2024"]}
GAIN_THRESHOLD = 0.005          # floor for the group-effect threshold; replaced by 2 x seed noise when that is larger
CORR_PRUNE = 0.97
T0 = time.time()


def log(msg):
    line = f"[{time.time() - T0:6.0f}s] {msg}"
    print(line, flush=True)
    with open(REP / "selection_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


class Ctx:
    def __init__(self):
        self.D = en.PanelData(load_panel("monthly"))                    # train + validation only
        OF, SF = en.origin_features(self.D)
        self.ex = en.make_categorical(en.build_examples(self.D, OF, SF, horizons=HORIZONS), self.D)
        self.feats = en.feature_names(self.ex)
        d = self.D
        self.tgt_shock = {"E": (d.covid | d.policy)[self.ex.target_idx.to_numpy()], "S": (d.covid | d.policy | d.ramp)[self.ex.target_idx.to_numpy()]}
        self.date_idx = {str(x.date()): i for i, x in enumerate(d.dates)}


def fold_split(C, key, k, mask_train=True, halflife=None):
    te_date, year = FOLDS[key]
    te = C.date_idx[te_date]
    ex = C.ex
    shock_col = "shock_S" if k == "S" else "shock_EV"
    tr = (ex.target_idx <= te)
    if mask_train:
        tr &= ~ex[shock_col].to_numpy()
    va = (ex.origin_idx >= te) & (ex.target_idx <= te + 12)
    va &= ~(C.tgt_shock["S" if k == "S" else "E"])
    w = None
    if halflife:
        w = 0.5 ** ((te - ex.target_idx[tr].to_numpy()) / halflife)
    return tr.to_numpy(), va.to_numpy(), w


def wape(actual, pred):
    return 100 * np.abs(actual - pred).sum() / actual.sum()


def probe(C, key, k, feats, base="last", mask_train=True, halflife=None, return_model=False, shuffle=None):
    tr, va, w = fold_split(C, key, k, mask_train, halflife)
    ex = C.ex
    Xtr, Xva = ex.loc[tr, feats], ex.loc[va, feats]
    y = ex.loc[tr, f"target_{k}"] - ex.loc[tr, f"{base}_{k}"]
    m = lgb.LGBMRegressor(**PROBE)
    m.fit(Xtr, y, sample_weight=w)
    if shuffle is not None:
        Xva = Xva.copy()
        Xva[shuffle] = Xva[shuffle].sample(frac=1.0, random_state=0).to_numpy()
    p = np.exp(ex.loc[va, f"{base}_{k}"].to_numpy() + m.predict(Xva))
    a = np.exp(ex.loc[va, f"target_{k}"].to_numpy())
    h = ex.loc[va, "horizon"].to_numpy()
    out = {"wape": wape(a, p), **{f"h{x}": wape(a[h == x], p[h == x]) for x in HORIZONS}}
    return (out, m) if return_model else out


def baselines(C, key, k):
    _, va, _ = fold_split(C, key, k)
    ex = C.ex.loc[va]
    a = np.exp(ex[f"target_{k}"].to_numpy())
    last = np.exp(ex[f"last_{k}"].to_numpy())
    sn_drift = np.exp(ex[f"last_{k}"].to_numpy() + ex[f"{k}_yadrift_h"].to_numpy())
    return {"last value": wape(a, last), "seasonal naive + drift": wape(a, sn_drift)}


def groups_for(C, k):
    g = {}
    for f in C.feats:
        g.setdefault(en.group_of(f, k), []).append(f)
    return g


def run():
    REP.mkdir(parents=True, exist_ok=True)
    FEAT.mkdir(parents=True, exist_ok=True)
    (REP / "selection_log.txt").write_text("", encoding="utf-8")
    C = Ctx()
    log(f"examples {C.ex.shape}; features {len(C.feats)}; folds {list(FOLDS)}")
    targets = "EVS"
    res = {}

    # ---- 0. time-proxy audit and probe seed noise --------------------------------------------------------------------
    from scipy import stats as sps
    OFall, _ = en.origin_features(C.D)
    tt, audit = np.arange(C.D.T), []
    for name, arr in OFall.items():
        rho = []
        for i in range(0, len(C.D.sid), 4):
            v = arr[i]
            ok = ~np.isnan(v)
            if ok.sum() > 40 and np.nanstd(v) > 0:
                rho.append(abs(sps.spearmanr(tt[ok], v[ok])[0]))
        audit.append(dict(feature=name, median_abs_rho_with_time=float(np.median(rho)) if rho else np.nan,
                          excluded_as_time_proxy=name in en.TIME_PROXY_FEATURES))
    pd.DataFrame(audit).sort_values("median_abs_rho_with_time", ascending=False).round(3).to_csv(REP / "time_proxy_audit.csv", index=False)
    noise = []
    for k in "EVS":
        for key in FOLDS:
            vals = []
            for seed in (42, 43, 44):
                PROBE_SEED = dict(PROBE, random_state=seed)
                tr, va, w = fold_split(C, key, k)
                m = lgb.LGBMRegressor(**PROBE_SEED).fit(C.ex.loc[tr, C.feats], C.ex.loc[tr, f"target_{k}"] - C.ex.loc[tr, f"last_{k}"])
                p = np.exp(C.ex.loc[va, f"last_{k}"].to_numpy() + m.predict(C.ex.loc[va, C.feats]))
                vals.append(wape(np.exp(C.ex.loc[va, f"target_{k}"].to_numpy()), p))
            noise.append(dict(target=k, fold=key, mean_wape=np.mean(vals), std_wape=np.std(vals, ddof=1), rel_std=np.std(vals, ddof=1) / np.mean(vals)))
    nz = pd.DataFrame(noise)
    nz.round(4).to_csv(REP / "selection_0_seed_noise.csv", index=False)
    thr = float(max(GAIN_THRESHOLD, 2 * nz.rel_std.mean()))
    log(f"time proxies excluded: {sorted(en.TIME_PROXY_FEATURES)}; seed noise rel std {nz.rel_std.mean():.4f} -> group threshold {thr:.4f}")

    # ---- A. base ------------------------------------------------------------------------------------------------
    rows = []
    for k in targets:
        for key in FOLDS:
            for base in ("last", "sm3", "sm6"):
                r = probe(C, key, k, C.feats, base=base)
                rows.append(dict(target=k, fold=key, base=base, **r))
            for name, v in baselines(C, key, k).items():
                rows.append(dict(target=k, fold=key, base=name, wape=v))
        log(f"A done for {k}")
    A = pd.DataFrame(rows)
    A.round(3).to_csv(REP / "selection_A_base.csv", index=False)
    best_base = {k: A[(A.target == k) & A.base.isin(["last", "sm3", "sm6"])].groupby("base").wape.mean().idxmin() for k in targets}
    log(f"best base: {best_base}")

    # ---- B. training policy -------------------------------------------------------------------------------------
    rows = []
    for k in targets:
        for key in FOLDS:
            for mask, hl in [(True, None), (False, None), (True, 36), (True, 18)]:
                r = probe(C, key, k, C.feats, base=best_base[k], mask_train=mask, halflife=hl)
                rows.append(dict(target=k, fold=key, mask_shocks=mask, halflife=hl or 0, **r))
        log(f"B done for {k}")
    B = pd.DataFrame(rows)
    B.round(3).to_csv(REP / "selection_B_policy.csv", index=False)
    policy = {}
    for k in targets:
        g = B[B.target == k].groupby(["mask_shocks", "halflife"]).wape.mean()
        (m, hl) = g.idxmin()
        policy[k] = dict(mask_shocks=bool(m), halflife=int(hl))
    log(f"policy: {policy}")

    # ---- C. group ablation --------------------------------------------------------------------------------------
    rows = []
    for k in targets:
        groups = groups_for(C, k)
        full = C.feats
        core = groups["core_horizon"] + groups["own_level_dev"] + groups["own_momentum"]
        for key in FOLDS:
            kw = dict(base=best_base[k], mask_train=policy[k]["mask_shocks"], halflife=policy[k]["halflife"] or None)
            ref_full = probe(C, key, k, full, **kw)["wape"]
            ref_core = probe(C, key, k, core, **kw)["wape"]
            rows.append(dict(target=k, fold=key, group="__full__", kind="ref", wape=ref_full, delta_rel=0.0))
            rows.append(dict(target=k, fold=key, group="__core__", kind="ref", wape=ref_core, delta_rel=0.0))
            for g, fs in groups.items():
                if g == "core_horizon":
                    continue
                w1 = probe(C, key, k, [f for f in full if f not in fs], **kw)["wape"]
                rows.append(dict(target=k, fold=key, group=g, kind="drop", wape=w1, delta_rel=(w1 - ref_full) / ref_full))
                if g not in ("own_level_dev", "own_momentum"):
                    w2 = probe(C, key, k, core + fs, **kw)["wape"]
                    rows.append(dict(target=k, fold=key, group=g, kind="add", wape=w2, delta_rel=(w2 - ref_core) / ref_core))
        log(f"C done for {k}")
    Cdf = pd.DataFrame(rows)
    Cdf.round(4).to_csv(REP / "selection_C_groups.csv", index=False)

    # ---- D. choose groups, prune correlated features ------------------------------------------------------------
    chosen, notes = {}, []
    for k in targets:
        groups = groups_for(C, k)
        keep = {"core_horizon", "own_level_dev", "own_momentum"}
        for g in groups:
            if g in keep or g == "core_horizon":
                continue
            dr = Cdf[(Cdf.target == k) & (Cdf.group == g) & (Cdf.kind == "drop")].delta_rel
            ad = Cdf[(Cdf.target == k) & (Cdf.group == g) & (Cdf.kind == "add")].delta_rel
            need = min(2, len(dr))
            helps_drop = dr.mean() >= thr and (dr > 0).sum() >= need
            helps_add = len(ad) > 0 and ad.mean() <= -thr and (ad < 0).sum() >= need
            if helps_drop or helps_add:
                keep.add(g)
            notes.append(dict(target=k, group=g, mean_drop_delta=float(dr.mean()), mean_add_delta=float(ad.mean()) if len(ad) else np.nan,
                              kept=bool(g in keep)))
        # backward pass: drop a kept group if removing it lowers the mean error by more than the threshold in >= 2 folds
        kw_ = dict(base=best_base[k], mask_train=policy[k]["mask_shocks"], halflife=policy[k]["halflife"] or None)
        for it in range(3):
            cur = [f for f in C.feats if en.group_of(f, k) in keep]
            ref = {key: probe(C, key, k, cur, **kw_)["wape"] for key in FOLDS}
            worst, worst_delta = None, 0.0
            for g in sorted(keep - {"core_horizon", "own_level_dev", "own_momentum"}):
                d_ = np.array([(probe(C, key, k, [f for f in cur if en.group_of(f, k) != g], **kw_)["wape"] - ref[key]) / ref[key] for key in FOLDS])
                if d_.mean() <= -thr and (d_ < 0).sum() >= min(2, len(d_)) and d_.mean() < worst_delta:
                    worst, worst_delta = g, d_.mean()
            if worst is None:
                break
            keep.discard(worst)
            notes.append(dict(target=k, group=worst, mean_drop_delta=worst_delta, mean_add_delta=np.nan, kept=False, pruned="backward pass"))
            log(f"backward pass {k}: removed group {worst} ({worst_delta:+.3%})")
        feats = [f for f in C.feats if en.group_of(f, k) in keep]
        # correlation pruning on numeric training rows of the last fold
        tr, _, _ = fold_split(C, list(FOLDS)[-1], k, policy[k]["mask_shocks"])
        num = [f for f in feats if f not in en.CAT_COLS and f != "horizon"]
        cm = C.ex.loc[tr, num].corr().abs()
        drop = set()
        for i, a in enumerate(num):
            if a in drop:
                continue
            for b in num[i + 1:]:
                if b not in drop and cm.loc[a, b] > CORR_PRUNE:
                    drop.add(b)
        chosen[k] = [f for f in feats if f not in drop]
        notes.append(dict(target=k, group="__pruned__", mean_drop_delta=np.nan, mean_add_delta=np.nan, kept=True, pruned=sorted(drop)))
        log(f"D {k}: {len(feats)} features in {len(keep)} groups, {len(drop)} pruned -> {len(chosen[k])}")
    pd.DataFrame(notes).to_csv(REP / "selection_D_choice.csv", index=False)

    # ---- E/F. final evaluation and importance -------------------------------------------------------------------
    rows, imp_rows = [], []
    for k in targets:
        groups = groups_for(C, k)
        core = groups["core_horizon"] + groups["own_level_dev"] + groups["own_momentum"]
        kw = dict(base=best_base[k], mask_train=policy[k]["mask_shocks"], halflife=policy[k]["halflife"] or None)
        for key in FOLDS:
            for name, fs in [("final", chosen[k]), ("full", C.feats), ("core", core)]:
                r = probe(C, key, k, fs, **kw)
                rows.append(dict(target=k, fold=key, feature_set=name, n_features=len(fs), **r))
            for name, v in baselines(C, key, k).items():
                rows.append(dict(target=k, fold=key, feature_set=name, n_features=0, wape=v))
        # permutation importance on the last fold
        key = list(FOLDS)[-1]
        base_r, model = probe(C, key, k, chosen[k], return_model=True, **kw)
        gain = dict(zip(chosen[k], model.booster_.feature_importance("gain")))
        _, va, _ = fold_split(C, key, k, policy[k]["mask_shocks"])
        ex = C.ex.loc[va]
        a = np.exp(ex[f"target_{k}"].to_numpy())
        b = ex[f"{best_base[k]}_{k}"].to_numpy()
        ref = wape(a, np.exp(b + model.predict(ex[chosen[k]])))
        for f in chosen[k]:
            incs = []
            for rep in range(3):
                Xs = ex[chosen[k]].copy()
                shuf = Xs[f].sample(frac=1.0, random_state=rep)
                shuf.index = Xs.index
                Xs[f] = shuf
                incs.append(wape(a, np.exp(b + model.predict(Xs))) - ref)
            imp_rows.append(dict(target=k, feature=f, group=en.group_of(f, k), perm_importance_wape_pts=float(np.mean(incs)),
                                 gain_share_pct=100 * gain[f] / sum(gain.values())))
        log(f"E/F done for {k}")
    Fdf = pd.DataFrame(rows)
    Fdf.round(3).to_csv(REP / "selection_F_final_vs_full.csv", index=False)
    imp = pd.DataFrame(imp_rows).sort_values(["target", "perm_importance_wape_pts"], ascending=[True, False])
    imp.round(4).to_csv(REP / "selection_E_permutation_importance.csv", index=False)

    spec = {"created_from": "train+validation only", "probe_params": PROBE, "folds": FOLDS, "group_effect_threshold": thr, "time_proxy_features_excluded": sorted(en.TIME_PROXY_FEATURES), "corr_prune": CORR_PRUNE,
            "targets": {k: dict(base=best_base[k], mask_shock_windows=policy[k]["mask_shocks"], recency_halflife_months=policy[k]["halflife"],
                                features=chosen[k], groups=sorted({en.group_of(f, k) for f in chosen[k]})) for k in targets}}
    json.dump(spec, open(FEAT / "feature_sets.json", "w"), indent=2)
    log("finished")


if __name__ == "__main__":
    run()
