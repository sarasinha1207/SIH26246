"""Phase 5 tests: features are leak-safe, aligned with their targets, and documented.
Runs under pytest or standalone: python tests/test_features.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(ROOT / "src" / "features"))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402

PANEL = load_panel("monthly")
D = en.PanelData(PANEL)
OF, SF = en.origin_features(D)
EX = en.make_categorical(en.build_examples(D, OF, SF, horizons=(1, 6, 12)), D)
FEATS_ALL = en.feature_names(EX, include_time_proxies=True)
FEATS = en.feature_names(EX)


def test_panel_excludes_the_locked_test_period():
    assert D.dates.max() == pd.Timestamp("2024-12-01") and set(PANEL.Split_Role.astype(str)) == {"train", "validation"}


def test_features_use_only_data_up_to_the_origin():
    """Rebuild every feature from a panel truncated at the origin; values must be identical."""
    rng = np.random.default_rng(7)
    for t in (50, 83, 120, 150):
        cut = PANEL[PANEL.Date <= D.dates[t]]
        Dt = en.PanelData(cut)
        assert Dt.T == t + 1
        OFt, SFt = en.origin_features(Dt)
        ext = en.build_examples(Dt, OFt, SFt, horizons=(1, 6, 12), origin_min=t, origin_max=t, need_target=False)
        ext = ext[ext.origin_idx == t]
        full = EX[EX.origin_idx == t]
        for h in (1, 6, 12):
            a = ext[ext.horizon == h].sort_values("Series_ID").reset_index(drop=True)
            b = full[full.horizon == h].sort_values("Series_ID").reset_index(drop=True)
            assert len(a) == len(b) == 280, (t, h, len(a), len(b))
            for f in FEATS_ALL:
                if f in en.CAT_COLS:
                    assert (a[f].astype(str) == b[f].astype(str)).all(), f
                    continue
                x, y = a[f].to_numpy(float), b[f].to_numpy(float)
                assert np.allclose(x, y, rtol=1e-9, atol=1e-9, equal_nan=True), f"{f} differs at origin {t}, h={h}: uses information after the origin"


def test_targets_are_the_log_level_h_months_ahead():
    for k in "EVS":
        sub = EX.sample(200, random_state=1)
        i = sub.series_row.to_numpy()
        got = sub[f"target_{k}"].to_numpy()
        exp = D.L[k][i, sub.target_idx.to_numpy()]
        assert np.allclose(got, exp)
        assert np.allclose(sub[f"last_{k}"].to_numpy(), D.L[k][i, sub.origin_idx.to_numpy()])
        assert (sub.target_idx - sub.origin_idx == sub.horizon).all()


def test_calendar_features_describe_the_target_month():
    sub = EX.sample(300, random_state=2)
    tm = (D.dates[sub.target_idx.to_numpy()].month).to_numpy()
    om = (D.dates[sub.origin_idx.to_numpy()].month).to_numpy()
    assert (sub.target_month.to_numpy() == tm).all() and (sub.origin_month.to_numpy() == om).all()


def test_shock_window_flags():
    h = EX[EX.horizon == 6]
    sample = h.sample(300, random_state=3)
    for _, r in sample.iterrows():
        lo, hi = max(int(r.origin_idx) - 12, 0), int(r.target_idx)
        e = (D.covid | D.policy)[lo:hi + 1].any()
        s = (D.covid | D.policy | D.ramp)[lo:hi + 1].any()
        assert bool(r.shock_EV) == bool(e) and bool(r.shock_S) == bool(s)


def test_every_feature_has_a_group_and_few_missing_values():
    for target in "EVS":
        groups = {en.group_of(f, target) for f in FEATS_ALL}
        assert "core_horizon" in groups and len(groups) >= 14
    assert EX[FEATS_ALL].isna().mean().max() < 0.05
    assert np.isfinite(EX[[f for f in FEATS if f not in en.CAT_COLS]].to_numpy(float)[~np.isnan(EX[[f for f in FEATS if f not in en.CAT_COLS]].to_numpy(float))]).all()


def test_time_proxies_are_excluded_and_documented():
    assert en.TIME_PROXY_FEATURES.isdisjoint(FEATS) and en.TIME_PROXY_FEATURES <= set(FEATS_ALL)
    audit = ROOT / "reports" / "features" / "time_proxy_audit.csv"
    if audit.exists():
        a = pd.read_csv(audit)
        flagged = set(a[a.median_abs_rho_with_time >= 0.69].feature)
        assert flagged == en.TIME_PROXY_FEATURES, f"audit and exclusion list differ: {flagged ^ en.TIME_PROXY_FEATURES}"
    fs = ROOT / "data" / "processed" / "features" / "feature_sets.json"
    if fs.exists():
        for k, spec in json.load(open(fs))["targets"].items():
            assert not set(spec["features"]) & en.TIME_PROXY_FEATURES, k


def test_pipeline_interface_respects_masks_and_locks():
    import pipeline as pl
    spec = pl.spec()
    for k in "EVS":
        X, y, w, meta = pl.training_frame(k, "2023-12-01")
        assert list(X.columns) == spec[k]["features"] and len(X) == len(y) == len(meta)
        assert meta.target_idx.max() <= int(np.where(D.dates == pd.Timestamp("2023-12-01"))[0][0])
        if spec[k]["mask_shock_windows"]:
            ex = pl._examples()[1].loc[meta.index]
            assert not ex["shock_S" if k == "S" else "shock_EV"].any()
        Xv, yv, _, mv = pl.validation_frame(k, "2023-12-01", 12)
        assert mv.origin_idx.min() >= int(np.where(D.dates == pd.Timestamp("2023-12-01"))[0][0]) and mv.target_idx.max() <= D.T - 1
        assert (mv.target_idx > meta.target_idx.max()).all()
    Xv, yv, _, mv = pl.validation_frame("V", "2024-12-01", 12)
    assert len(mv) == 0, "rows beyond 2024-12 are reachable without unlocking the test period"


def test_categorical_features_have_fixed_categories():
    for c, mcol in en.CAT_COLS.items():
        assert str(EX[c].dtype) == "category" and set(EX[c].cat.categories) == set(D.meta[mcol])


def test_selected_feature_sets_are_valid():
    path = ROOT / "data" / "processed" / "features" / "feature_sets.json"
    if not path.exists():
        return
    fs = json.load(open(path))
    for k, spec in fs["targets"].items():
        assert set(spec["features"]) <= set(FEATS) and "horizon" in spec["features"], k
        assert spec["base"] in ("last", "sm3", "sm6")
    cat = pd.read_csv(ROOT / "data" / "processed" / "features" / "feature_catalog.csv")
    assert set(FEATS_ALL) <= set(cat.feature)


def test_relative_flags_are_leak_safe_and_balanced():
    import flags as fl
    R = fl.relative_flags(D)
    for t in (60, 110, 150):
        Dt = en.PanelData(PANEL[PANEL.Date <= D.dates[t]])
        Rt = fl.relative_flags(Dt)
        for name in ("cov_pct", "cov_trend_rel", "status_code", "seat_mismatch", "coverage_3m_log"):
            assert np.allclose(Rt[name][:, t], R[name][:, t], equal_nan=True), f"{name} uses data after the origin (t={t})"
    code = R["status_code"][:, 40:]
    for s in np.unique(D.sector):
        c = code[D.sector == s]
        shares = [np.mean(c == i) for i in range(5)]
        assert abs(shares[0] - 0.107) < 0.01 and abs(shares[2] - 0.393) < 0.01, (s, shares)
    assert fl.STATUSES[0] == "Tightest decile" and fl.absolute_context([1.2, 0.5, 0.15, 0.05]).tolist() ==         ["openings exceed seekers", "moderate", "oversupplied", "deep surplus"]


def test_flag_findings_in_summary_and_document():
    S = json.load(open(ROOT / "reports" / "features" / "flags_summary.json"))
    doc = (ROOT / "docs" / "phases" / "PHASE_5_FEATURE_ENGINEERING.md").read_text(encoding="utf-8")
    fv = {r["event"]: r for r in S["forward_value"]}
    sat, sho = fv["in the saturation decile 12 months later"], fv["in the shortage decile 12 months later"]
    assert sat["auc_current_percentile"] > 0.9 and sho["auc_current_percentile"] > 0.9
    assert sat["auc_trailing_trend_among_not_yet_extreme"] < 0.5 and sho["auc_trailing_trend_among_not_yet_extreme"] < 0.5
    for v in (sat["auc_trailing_trend_among_not_yet_extreme"], sho["auc_trailing_trend_among_not_yet_extreme"]):
        assert f"{v:.3f}" in doc
    assert f"{S['pct_rank_persistence_12m']:.2f}" in doc
    pb = {(r["event"], r["flag_if_percentile_within"]): r for r in S["persistence_benchmark"]}
    for key, r in pb.items():
        if key[1] in (10, 20):
            assert f"{r['precision']:.2f}" in doc and f"{r['recall']:.2f}" in doc, key


def test_phase5_document_numbers_match_the_experiment_tables():
    doc = (ROOT / "docs" / "phases" / "PHASE_5_FEATURE_ENGINEERING.md").read_text(encoding="utf-8")
    rep = ROOT / "reports" / "features"
    F = pd.read_csv(rep / "selection_F_final_vs_full.csv")
    m = F.pivot_table(index="target", columns="feature_set", values="wape")
    for k in "EVS":
        for col in ("core", "full", "final", "last value", "seasonal naive + drift"):
            assert f"{m.loc[k, col]:.2f}" in doc, (k, col)
        assert f"{100 * (1 - m.loc[k, 'final'] / m.loc[k, 'last value']):.0f}%" in doc
    nz = pd.read_csv(rep / "selection_0_seed_noise.csv")
    thr = json.load(open(ROOT / "data" / "processed" / "features" / "feature_sets.json"))["group_effect_threshold"]
    assert f"{100 * thr:.2f}%" in doc and abs(100 * thr / 2 - 100 * nz.rel_std.mean()) < 0.02, "noise level and threshold in the document"
    sets = json.load(open(ROOT / "data" / "processed" / "features" / "feature_sets.json"))["targets"]
    for k in "EVS":
        assert f"| {len(sets[k]['features'])} |" in doc, k
    g = pd.read_csv(rep / "selection_G_all_horizons.csv").groupby("target")[["probe_wape", "last_value_wape"]].mean()
    for k in "EVS":
        assert f"{g.loc[k, 'probe_wape']:.2f}" in doc and f"{g.loc[k, 'last_value_wape']:.2f}" in doc, k
    cat = pd.read_csv(ROOT / "data" / "processed" / "features" / "feature_catalog.csv")
    assert f"{len(cat)} candidate" in doc.replace("85 candidates", "85 candidate") or f"{len(cat)} candidates" in doc


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
