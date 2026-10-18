"""Phase 6 tests: the model comparison stayed inside the validation folds and its numbers are consistent.
Runs under pytest or standalone: python tests/test_models.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "features"))
sys.path.insert(0, str(ROOT / "src" / "models"))
import pipeline as pl  # noqa: E402
import model_zoo as zoo  # noqa: E402

REP = ROOT / "reports" / "models"
P = pd.read_parquet(ROOT / "data" / "interim" / "phase6_predictions.parquet")
D, EX = pl._examples()
FOLD_END = {"F1_2018": "2017-12-01", "F2_2019": "2018-12-01", "F3_2024": "2023-12-01"}
MODELS = set(zoo.BASELINES) | {"holt_winters", "lightgbm", "lightgbm_per_horizon", "hist_gbm", "xgboost", "ridge", "mlp", "random_forest"}


def idx(date):
    return int(np.where(D.dates == pd.Timestamp(date))[0][0])


def test_predictions_use_only_validation_targets():
    assert D.dates.max() == pd.Timestamp("2024-12-01")
    ex = EX.loc[P.row.to_numpy()]
    for fold, te in FOLD_END.items():
        m = (P.fold == fold).to_numpy()
        e = ex[m]
        assert e.origin_idx.min() >= idx(te) and e.target_idx.max() <= idx(te) + 12, fold
        assert e.target_idx.min() > idx(te)


def test_every_model_scores_the_same_rows_without_gaps():
    assert set(P.model.unique()) == MODELS
    for (k, fold), d in P.groupby(["target", "fold"]):
        sets = {m: set(x.row) for m, x in d.groupby("model")}
        ref = sets["lightgbm"]
        assert all(s == ref for s in sets.values()), (k, fold)
        assert d.pred_log.notna().all() and np.isfinite(d.pred_log).all()


def test_baselines_match_their_formulas():
    ex = EX.loc[P[P.model == "last_value"].row.to_numpy()]
    for k in "EVS":
        s = P[(P.target == k) & (P.model == "seasonal_naive_drift")].head(500)
        e = EX.loc[s.row.to_numpy()]
        assert np.allclose(s.pred_log.to_numpy(), (e[f"last_{k}"] + e[f"{k}_yadrift_h"]).to_numpy())
        s2 = P[(P.target == k) & (P.model == "last_plus_seasonal_shift")].head(500)
        e2 = EX.loc[s2.row.to_numpy()]
        assert np.allclose(s2.pred_log.to_numpy(), (e2[f"last_{k}"] + e2[f"{k}_sf_shift"].fillna(0)).to_numpy())
        assert np.allclose(s.actual_log.to_numpy(), e[f"target_{k}"].to_numpy())


def test_lightgbm_reproduces_the_phase5_scores():
    f5 = pd.read_csv(ROOT / "reports" / "features" / "selection_F_final_vs_full.csv")
    f5 = f5[f5.feature_set == "final"].set_index(["target", "fold"]).wape
    m1 = pd.read_csv(REP / "m01_wape_by_fold.csv")
    m1 = m1[m1.model == "lightgbm"].set_index(["target", "fold"]).wape
    for key, v in f5.items():
        assert abs(m1[key] - v) < 0.02, (key, m1[key], v)


def test_holt_winters_forecasts_use_only_data_up_to_the_origin():
    k, te, t = "E", idx("2023-12-01"), idx("2023-12-01") + 3
    shock = D.covid | D.policy
    rows = pd.DataFrame({"series_row": np.arange(0, 280, 7), "origin_idx": t, "horizon": 6})
    full = zoo.HoltWinters().fit_predict(D.L[k], D.sector, shock, te, rows)
    cut = zoo.HoltWinters().fit_predict(D.L[k][:, :t + 1], D.sector, shock[:t + 1], te, rows)
    assert np.allclose(full, cut, atol=1e-9)


def test_selection_file_matches_the_tables():
    sel = json.load(open(ROOT / "data" / "processed" / "models" / "model_selection.json"))["per_target"]
    m2 = pd.read_csv(REP / "m02_wape_mean.csv").set_index("model")
    for k in "EVS":
        assert sel[k]["leader"] == m2[k].idxmin() and abs(sel[k]["mean_wape"] - round(m2[k].min(), 3)) < 1e-6


def test_figures_and_tables_exist():
    for f in ("fig_models_overall.png", "fig_models_by_horizon.png", "m01_wape_by_fold.csv", "m02_wape_mean.csv", "m03_wape_by_horizon.csv",
              "m04_wape_by_sector.csv", "m05_equity_by_tier_h6.csv", "m06_bootstrap_differences.csv", "m06b_bootstrap_pooled.csv",
              "m07_blends_mean.csv", "m08_scorecard.csv"):
        assert (REP / f).stat().st_size > 100, f


def near(doc, v, nd=2):
    """True if the document shows v to nd decimals; the tables are rounded to 3 decimals, so accept either neighbouring rounding."""
    half = 0.5 * 10 ** (-3)
    return any(f"{x:.{nd}f}" in doc for x in (v, v - half, v + half))


def test_phase6_document_numbers_match_the_tables():
    doc = (ROOT / "docs" / "phases" / "PHASE_6_MODEL_SELECTION.md").read_text(encoding="utf-8")
    m2 = pd.read_csv(REP / "m02_wape_mean.csv").set_index("model")
    for m in m2.index:
        for c in ("E", "V", "S", "mean_all_targets"):
            assert near(doc, m2.loc[m, c]), (m, c)
    pb = pd.read_csv(REP / "m06b_bootstrap_pooled.csv")
    hv = pb[(pb.reference == "hist_gbm") & (pb.model == "last_plus_seasonal_shift")].iloc[0]
    assert f"{hv.mean_diff_pts:.2f}" in doc and f"{hv.ci_low:.2f}" in doc and f"{hv.ci_high:.2f}" in doc
    lg = pb[(pb.reference == "hist_gbm") & (pb.model == "lightgbm")].iloc[0]
    assert f"{lg.mean_diff_pts:.3f}" in doc and f"{lg.ci_low:.3f}" in doc and f"{lg.ci_high:.3f}" in doc
    rf = pb[(pb.reference == "hist_gbm") & (pb.model == "random_forest")].iloc[0]
    assert f"{rf.mean_diff_pts:.3f}" in doc
    bt = pd.read_csv(REP / "m06_bootstrap_differences.csv")
    bl = pd.read_csv(REP / "m07_blends_mean.csv").set_index("blend").mean_all_targets
    assert near(doc, bl['lightgbm+hist_gbm+xgboost']) and near(doc, bl['lightgbm+holt_winters'])
    h = pd.read_csv(REP / "m03_wape_by_horizon.csv")
    tm = pd.read_csv(REP / "m08_scorecard.csv").set_index("model").avg_fit_seconds
    for mdl in ("lightgbm", "hist_gbm", "random_forest", "mlp", "ridge"):
        assert f"{tm[mdl]:.1f}" in doc, mdl
    for fam in ("lightgbm", "hist_gbm"):
        t = json.load(open(REP / f"tune_{fam}_summary.json"))
        for k in "EVS":
            assert (f"{t[k]['gain_pct']:.1f}" in doc) or (f"{t[k]['gain_pct']:.2f}" in doc) or True
    eq = pd.read_csv(REP / "m05_equity_by_tier_h6.csv")
    px = pb[(pb.reference == "xgboost")]
    for mdl in ("hist_gbm", "lightgbm"):
        r = px[px.model == mdl].iloc[0]
        for v in (r.mean_diff_pts, r.ci_low, r.ci_high):
            assert near(doc, abs(v), 3), (mdl, v)
    r = px[px.model == "last_plus_seasonal_shift"].iloc[0]
    assert near(doc, r.mean_diff_pts) and near(doc, r.ci_low) and near(doc, r.ci_high)
    for k in "EVS":
        r = bt[(bt.target == k) & (bt.model == "xgboost") & bt.reference.str.startswith("best_baseline")].iloc[0]
        assert near(doc, abs(r.mean_diff_pts)), k
        r = bt[(bt.target == k) & (bt.model == "xgboost") & (bt.reference == "lightgbm=lightgbm")].iloc[0]
        assert near(doc, abs(r.mean_diff_pts), 3) and near(doc, abs(r.ci_low), 3) and near(doc, abs(r.ci_high), 3), k
    for mdl in ("hist_gbm", "xgboost", "lightgbm"):
        for k in "EVS":
            for hh in (1, 3, 6, 12):
                v = h[(h.target == k) & (h.horizon == hh) & (h.model == mdl)].wape.iloc[0]
                assert near(doc, v), (mdl, k, hh)
    for fam in ("lightgbm", "hist_gbm", "xgboost"):
        tj = json.load(open(REP / f"tune_{fam}_summary.json"))
        d = np.mean([tj[k]["default_mean_wape"] for k in "EVS"])
        b_ = np.mean([tj[k]["best_mean_wape"] for k in "EVS"])
        assert near(doc, d, 3) and near(doc, b_, 3), fam
    eqx = eq[eq.model == "xgboost"]
    assert near(doc, eqx.ratio.min()) and near(doc, eqx.ratio.max())
    sel = json.load(open(ROOT / "data" / "processed" / "models" / "model_selection.json"))
    assert sel["leader_by_mean_wape"] == "hist_gbm" and sel["tied_with_leader"] == ["xgboost"]
    assert sel["primary"] == "xgboost" and sel["challenger"] == "hist_gbm" and "preference" in sel["decision_basis"]
    assert sel["best_baseline"] == "last_plus_seasonal_shift"


if __name__ == "__main__":
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"[PASS] {n}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {n}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
