"""Phase 8 addendum tests: noise floor, flag significance, v3 declaration, fresh draws, interval policy, and the numbers quoted in the document.
Runs under pytest or standalone: python tests/test_phase8_addendum.py"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "common"))
import splits as sp  # noqa: E402

OUT, V3 = ROOT / "reports" / "evaluation", ROOT / "models" / "xgboost_v3"
DOC = (ROOT / "docs" / "phases" / "PHASE_8_EVALUATION_AND_TUNING.md").read_text(encoding="utf-8")
SOURCES = ("original", "fresh_2027", "fresh_2028")


def test_noise_floor_is_a_lower_bound_and_the_filter_simulation_agrees():
    nf = json.load(open(OUT / "noise_floor.json"))
    for k, d in nf["mean_over_horizons"].items():
        assert d["floor_wape"] < d["blend_wape"] <= d["model_wape"] + 1e-9, k
    for k, hs in nf["simulation_check"].items():
        for h, v in hs.items():
            assert abs(v["simulated"] - v["formula"]) / v["formula"] < 0.02, (k, h)
    F = pd.read_csv(OUT / "noise_floor.csv")
    assert (F.model_wape > F.floor_wape).all() and F.groupby("target").floor_wape.apply(lambda s: s.is_monotonic_increasing).all()


def test_v3_declaration_files_are_unchanged_and_the_blend_is_the_fold_blend():
    d = json.load(open(V3 / "declaration.json"))
    for name, digest in d["files_sha256"].items():
        assert sp.sha256(V3 / name) == digest, name
    blend = json.load(open(V3 / "primary" / "blend.json"))["model_weight_by_target_horizon"]
    fold = json.load(open(ROOT / "models" / "xgboost_v2" / "primary" / "blend_cv.json"))["model_weight_by_target_horizon"]
    conf = json.load(open(V3 / "conformal.json"))
    assert blend == fold and min(blend["S"].values()) == 0.5
    assert conf["window"] == 12 and conf["gamma"] == 0.05 and conf["n_min"] == 200


def test_fresh_draws_are_new_worlds_with_full_series_coverage():
    orig = pd.read_parquet(ROOT / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date", "Total_Employed_Workers"])
    for seed in (2027, 2028):
        d = ROOT / "data" / "fresh_draws" / f"seed_{seed}"
        for n, rows in (("train", 307440), ("validation", 15400), ("test", 142800)):
            f = pd.read_parquet(d / "data" / "splits" / f"{n}.parquet", columns=["Series_ID"])
            assert len(f) == rows and f.Series_ID.nunique() == 280, (seed, n)
        new = pd.read_parquet(d / "data" / "processed" / "panel_monthly.parquet", columns=["Series_ID", "Date", "Total_Employed_Workers"])
        m = orig.merge(new, on=["Series_ID", "Date"], suffixes=("", "_n"))
        assert len(m) == 53760 and (m.Total_Employed_Workers == m.Total_Employed_Workers_n).mean() < 0.001
        assert f"SEED = {seed}" in (d / "src" / "data_generation" / "generate_lmis_master_dataset.py").read_text(encoding="utf-8")


def test_fresh_draw_results_replicate_the_main_findings():
    for src in SOURCES:
        M = pd.read_csv(OUT / "v3" / src / "metrics.csv").set_index(["target", "model"])
        assert M.loc[("S", "last_plus_seasonal_shift"), "ci_high"] < 0, src        # v3 minus baseline: the blend is better and the interval excludes zero
        assert M.loc[("S", "v2_primary"), "ci_high"] < 0 and M.loc[("E", "v1_refit"), "ci_high"] < 0, src
        assert M.loc[("V", "last_plus_seasonal_shift"), "ci_high"] < 0, src        # vacancies: small but real gain over the baseline
        assert M.loc[("E", "v3"), "wape_mean_horizon"] < 0.8 * M.loc[("E", "seasonal_naive_drift"), "wape_mean_horizon"], src
        assert M.loc[("S", "v3"), "wape_mean_horizon"] < M.loc[("S", "last_plus_seasonal_shift"), "wape_mean_horizon"] - 0.5, src


def test_interval_policy_matches_the_evidence():
    for src in SOURCES:
        I = pd.read_csv(OUT / "v3" / src / "intervals.csv").set_index(["target", "intervals"])
        assert abs(I.loc[("S", "adaptive conformal"), "coverage"] - 0.90) < 0.015, src
        assert I.loc[("S", "adaptive conformal"), "width_pct"] < 0.8 * I.loc[("S", "static (fold-based)"), "width_pct"], src
        assert I.loc[("E", "adaptive conformal"), "coverage"] < I.loc[("E", "static (fold-based)"), "coverage"] - 0.04, src
        assert I.loc[("V", "adaptive conformal"), "coverage_h12"] < I.loc[("V", "static (fold-based)"), "coverage_h12"], src
    R = pd.read_csv(OUT / "v3" / "vacancy_interval_recalibration.csv")
    fresh = R[R.source.str.startswith("fresh") & (R.intervals == "recalibrated static")]
    assert len(fresh) == 2 and (abs(fresh.coverage_h12 - 0.90) < 0.015).all()
    pol = json.load(open(V3 / "final_interval_policy.json"))["policy"]
    assert set(pol) == {"E", "V", "S"} and "adaptive" in pol["S"]


def test_flag_significance_table_and_the_document():
    F = pd.read_csv(OUT / "test" / "flag_significance.csv")
    assert len(F) == 8 and set(F.horizon) == {1, 3, 6, 12}
    sat12 = F[(F.horizon == 12) & F.event.str.startswith("saturation")].iloc[0]
    assert sat12.diff_precision > 0.02 and not sat12.series_precision_ci.startswith("-")
    assert "saturation at 12 months" in DOC


def test_document_numbers_match_the_tables():
    nf = json.load(open(OUT / "noise_floor.json"))["mean_over_horizons"]
    for k in "EVS":
        assert f"{nf[k]['floor_wape']:.2f}%" in DOC, k
    for src in SOURCES:
        M = pd.read_csv(OUT / "v3" / src / "metrics.csv").set_index(["target", "model"])
        for k in "EVS":
            assert f"{M.loc[(k, 'v3'), 'wape_mean_horizon']:.2f}" in DOC, (src, k)


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
