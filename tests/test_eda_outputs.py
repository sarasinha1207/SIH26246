"""Phase 4 tests: the EDA stayed inside train+validation, produced every output, and the document's numbers match the data.
Runs under pytest or standalone: python tests/test_eda_outputs.py"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EDA = ROOT / "reports" / "eda"
from _guard import read_doc, skip_module_unless  # noqa: E402
skip_module_unless(ROOT / "docs" / "phases" / "PHASE_4_EDA.md", why="checks the Phase 4 write-up against the EDA tables")
DOC = read_doc(ROOT / "docs" / "phases" / "PHASE_4_EDA.md")
F = json.load(open(EDA / "eda_findings.json"))
FIGS = ["fig01_trends", "fig02_seasonality", "fig03_covid", "fig04_coverage", "fig05_density_heatmap", "fig06_rank_stability",
        "fig07_acf", "fig08_leadlag", "fig09_covariate_signal", "fig10_seats_vs_demand", "fig11_noise_vs_volume", "fig12_yoy_growth",
        "fig13_distributions", "fig14_correlation", "fig15_states", "fig16_unemployment_wages", "fig17_status_classes"]


def test_eda_never_touched_the_test_period():
    assert F["scope"]["roles"] == ["train", "validation"] and F["scope"]["last"] == "2024-12-01" and F["scope"]["rows"] == 47040
    src = (ROOT / "src" / "eda" / "run_eda.py").read_text(encoding="utf-8")
    assert "unlock_test=True" not in src and 'roles=("train", "validation")' in src


def test_all_figures_and_tables_exist():
    for f in FIGS:
        assert (EDA / "figures" / f"{f}.png").stat().st_size > 10_000, f
        assert f in DOC, f"{f} not listed in the document"
    assert len(list((EDA / "tables").glob("t*.csv"))) == 22


def has(value, nd, suffix=""):
    """True if the document contains |value| formatted with nd decimals (so '-0.31' matches '−0.31')."""
    return f"{abs(value):.{nd}f}{suffix}" in DOC


def test_document_numbers_match_the_data():
    c = {r["sector"]: r for r in pd.read_csv(EDA / "tables" / "t03_covid_impact.csv").query("target == 'Employed workers'").to_dict("records")}
    v = {r["sector"]: r for r in pd.read_csv(EDA / "tables" / "t03_covid_impact.csv").query("target == 'Job vacancies'").to_dict("records")}
    checks = [has(c[s]["worst_decline_pct"], 1, "%") for s in ("Construction", "Textiles and Apparel", "Manufacturing")]
    checks += [has(v[s]["worst_decline_pct"], 1, "%") for s in ("Construction", "Textiles and Apparel", "Manufacturing")]
    checks += [has(v["Healthcare"]["peak_surge_pct"], 1, "%"), has(v["IT-ITeS"]["peak_surge_pct"], 1, "%"),
               has(c["Healthcare"]["peak_surge_pct"], 1, "%"), has(c["IT-ITeS"]["peak_surge_pct"], 1, "%")]
    cov = F["coverage"]
    checks += [has(cov[s]["ratio_post_over_pre"], 2, "×") for s in cov]
    conc = F["concentration"]
    checks += [has(conc["IT-ITeS"]["top5_share_pct"], 1, "%"), has(conc["Manufacturing"]["top5_share_pct"], 1, "%"),
               has(conc["IT-ITeS"]["gini"], 3), has(F["density"]["mfg_ratio_hub_to_tribal"], 1, "×"),
               has(F["density"]["it_ratio_top_tier_to_tribal"], 1, "×")]
    acf = F["acf"]
    checks += [has(acf["E"]["lag12"], 2), has(acf["V"]["lag1"], 2), has(acf["S"]["lag1"], 2), has(F["leadlag"]["vac_vs_emp_lag0"], 3),
               has(F["noise"]["V"]["median_noise_pct"], 1, "%"), has(F["noise"]["S"]["median_noise_pct"], 1, "%"),
               has(F["noise"]["E"]["median_noise_pct"], 1, "%")]
    tv = pd.DataFrame(F["training_vs_demand"]).set_index("sector")
    checks += [has(tv.loc[s, "seats_per_100_vacancies"], 0) for s in tv.index]
    checks += [has(tv.spearman_seats_vs_vacancies.min(), 2), has(tv.spearman_seats_vs_vacancies.max(), 2),
               has(100 * tv.total_variation_distance.min(), 0, "%") or has(100 * tv.total_variation_distance.min(), 0),
               has(100 * tv.total_variation_distance.max(), 0)]
    d = pd.read_csv(EDA / "tables" / "t11_drift_train_vs_validation.csv")
    checks += [has(x, 1) for x in d[d.target == "Employed workers"][["train_2012_2019_mean_yoy_pct", "val_2024_mean_yoy_pct"]].to_numpy().ravel()]
    it = d[(d.target == "Job vacancies") & (d.sector == "IT-ITeS")].iloc[0]
    checks += [has(it.val_2024_mean_yoy_pct, 1, "%"), has(it.ks_stat, 2)]
    b = pd.read_csv(EDA / "tables" / "t10_baseline_errors_validation_2024.csv")
    bb = b[b.scope == "all"].pivot_table(index=["target", "horizon"], columns="model", values="wape_pct")
    for col in ("last value", "seasonal naive + drift", "seasonally adjusted 3-month level"):
        checks += [has(x, 2) for x in bb[col].to_numpy()]
    bad = [i for i, ok in enumerate(checks) if not ok]
    assert not bad, f"{len(bad)} document numbers do not match the data (check indexes {bad})"


def test_new_findings_match_the_data():
    d = F["distributions"]
    adf = pd.DataFrame(F["adf"]).set_index(["target", "transform"]).share_rejecting_unit_root_pct
    st = pd.DataFrame(F["status_2024"]).T
    gap = pd.DataFrame(F["net_gap_2024"]).T
    eq = F["equity_preview_h6_last_value"]["worst_tier_over_overall"]
    checks = [has(d["mean_skew_level"], 2), has(d["mean_skew_log_level"], 2), has(d["mean_skew_12m"], 2), has(d["max_excess_kurtosis_12m"], 2),
              has(F["correlation_yoy"]["max_abs_offdiag"], 2), has(100 * F["correlation_yoy"]["share_abs_below_0_2"], 0, "%"),
              str(F["redundant_pairs_levels"]) in DOC]
    checks += [has(adf[(t, "level (log)")], 1, "%") for t in ("Employed workers", "Job vacancies")]
    checks += [has(adf[(t, "month-on-month difference")], 0, "%") for t in ("Employed workers", "Job vacancies", "Registered seekers")]
    checks += [has(adf[(t, "12-month difference")], 0, "%") for t in ("Employed workers", "Job vacancies")]
    checks += [has(100 * st.loc["Construction", "Saturation Risk"], 0, "%"), has(100 * st.loc["Textiles and Apparel", "Saturation Risk"], 0, "%"),
               has(100 * st.loc["IT-ITeS", "Balanced"], 0, "%"), has(100 * st.loc["Healthcare", "Oversupply Watch"], 0, "%"),
               has(100 * st.loc["Manufacturing", "Oversupply Watch"], 0, "%")]
    checks += [has(eq[k], 2, "×") for k in eq]
    assert (gap.share_of_districts_with_openings_above_seekers == 0).all() and "No district in any sector has more openings" in DOC
    ur = F["unemployment_peak"]
    checks += [has(ur[s][1], 1) for s in ur]
    lo, hi = F["wage_tier_spread_pct"]
    checks += [has(lo, 1, "%"), has(hi, 1, "%")]
    bad = [i for i, ok in enumerate(checks) if not ok]
    assert not bad, f"new-finding numbers not in the document (indexes {bad})"


def test_adf_implementation_is_sound():
    sys.path.insert(0, str(ROOT / "src" / "eda"))
    import numpy as np
    from stat_tests import adf_tstat, ADF_CRIT_5PCT
    rng = np.random.default_rng(0)
    walks = [adf_tstat(np.cumsum(rng.normal(size=96))) < ADF_CRIT_5PCT for _ in range(300)]
    noise = [adf_tstat(rng.normal(size=96)) < ADF_CRIT_5PCT for _ in range(300)]
    assert np.mean(walks) < 0.12, f"random walks rejected too often: {np.mean(walks):.2f}"
    assert np.mean(noise) > 0.95, f"white noise not rejected: {np.mean(noise):.2f}"


def test_seasonality_numbers():
    t = pd.read_csv(EDA / "tables" / "t02_seasonality.csv").query("target == 'Employed workers'").set_index("sector")
    for s in t.index:
        assert has(t.loc[s, "amplitude_pct"], 1, "%")
    assert has(t.loc["Construction", "variance_share_pct"], 0, "%") and has(t.loc["Textiles and Apparel", "variance_share_pct"], 0, "%")


def test_rank_stability_range_in_document():
    r = pd.DataFrame(F["rank_stability"])
    one, five = r[r.lag_years == 1].mean_spearman, r[r.lag_years == 5].mean_spearman
    assert has(one.min(), 2) and has(one.max(), 2) and has(five.min(), 2) and has(five.max(), 2)


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
