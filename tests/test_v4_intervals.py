"""v4 phase 5 tests: interval calibration, flags and confidence labels are correct on synthetic data, and the recorded results are complete and honest.
The first group runs on synthetic frames; the second reads the files of phase 5 (skipped until they have been produced).
Runs under pytest or standalone: python tests/test_v4_intervals.py"""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "v4"))
sys.path.insert(0, str(ROOT / "tests"))
import _guard  # noqa: E402
import config as C  # noqa: E402

_guard.skip_module_unless(C.DATA / "SPLITS_MANIFEST.json", why="needs the v4 phase 3 records")
import early_warning as EW  # noqa: E402
import intervals as IV  # noqa: E402

EVAL = C.REPORTS / "evaluation"


def need(path):
    if not Path(path).exists():
        raise unittest.SkipTest(f"{Path(path).name} not produced yet")


def synthetic(n_origins=30, per_origin=400, seed=0, sd=0.1, scale_with_h=True):
    """Predictions with N(0, sd * sqrt(h)) errors, for horizons 1..60, several origins, two sectors and two volume classes."""
    rng = np.random.default_rng(seed)
    rows = []
    for h in range(1, 61):
        for o in range(n_origins):
            sd_h = sd * np.sqrt(h) if scale_with_h else sd
            sec = rng.integers(0, 2, per_origin)
            rows.append(pd.DataFrame({"origin_idx": o + 100, "horizon": h, "series_row": 0, "sector": np.where(sec == 0, "A", "B"), "volume": np.where(rng.random(per_origin) < 0.3, "low", "normal"),
                                      "pred_E": 0.0, "act_E": rng.normal(0, sd_h, per_origin), "vol_E": 0.05, "base_E": 5.0, "shock_EV": False, "shock_S": False}))
    return pd.concat(rows, ignore_index=True)


# ---- calibration -------------------------------------------------------------------------------------------------------------------------------
def test_scheme_names_are_parsed():
    assert IV.parse("h") == (False, "")
    assert IV.parse("h_sector") == (False, "sector")
    assert IV.parse("h_volume") == (False, "volume")
    assert IV.parse("h_scaled") == (True, "")
    assert IV.parse("h_scaled_sector") == (True, "sector")


def test_interval_covers_about_ninety_percent_on_exchangeable_errors():
    cal, chk = synthetic(seed=1), synthetic(seed=2)
    table = IV.calibrate(cal, "E", "h")
    lo, hi = IV.apply(chk, "E", "h", table)
    cover = ((chk.act_E >= lo) & (chk.act_E <= hi)).mean()
    assert 0.88 < cover < 0.92, cover
    assert (table.lo < 0).all() and (table.hi > 0).all()
    assert table.hi.iloc[-1] > table.hi.iloc[0]                      # the interval widens with the horizon


def test_group_schemes_give_each_group_its_own_quantiles():
    cal = synthetic(seed=3)
    cal.loc[cal.sector == "B", "act_E"] *= 3                          # sector B is three times as noisy
    t = IV.calibrate(cal, "E", "h_sector").set_index(["group", "horizon"])
    assert t.loc[("B", 20), "hi"] > 2.5 * t.loc[("A", 20), "hi"]
    lo, hi = IV.apply(cal, "E", "h_sector", t.reset_index())
    assert ((hi - lo)[cal.sector == "B"].mean()) > 2.5 * ((hi - lo)[cal.sector == "A"].mean())


def test_long_horizons_with_few_origins_pool_neighbouring_horizons():
    cal = synthetic(n_origins=3, per_origin=3000, seed=4)             # every horizon has only 3 origins: fewer than MIN_ORIGINS
    t = IV.calibrate(cal, "E", "h")
    assert (t.radius > IV.SMOOTH).all()
    full = IV.calibrate(synthetic(n_origins=20, per_origin=300, seed=4), "E", "h")
    assert (full.radius == IV.SMOOTH).all()


def test_scaled_scheme_multiplies_by_the_series_volatility():
    cal = synthetic(seed=5)
    t = IV.calibrate(cal, "E", "h_scaled")
    a, b = cal.head(5).copy(), cal.head(5).copy()
    b["vol_E"] = a.vol_E * 2
    lo_a, hi_a = IV.apply(a, "E", "h_scaled", t)
    lo_b, hi_b = IV.apply(b, "E", "h_scaled", t)
    assert np.allclose(hi_b - a.pred_E, 2 * (hi_a - a.pred_E))


def test_interval_evaluation_counts_misses_and_scores_them():
    df = pd.DataFrame({"act_E": [0.0, 1.0, -1.0], "pred_E": [0.0, 0.0, 0.0], "horizon": [1, 1, 1], "sector": ["A"] * 3, "volume": ["normal"] * 3,
                       "shock_EV": [False] * 3, "shock_S": [False] * 3})
    r = IV.evaluate(df, "E", np.array([-0.5] * 3), np.array([0.5] * 3))
    a = r[r.slice == "all"].iloc[0]
    assert abs(a.coverage - 1 / 3) < 1e-9
    # width 1; misses by 0.5 each: score = 1 + 20 * 0.5 for two rows, 1 for the covered one
    assert abs(a.interval_score - (1 + 11 + 11) / 3) < 1e-9


# ---- flags -------------------------------------------------------------------------------------------------------------------------------------
def test_cohort_percentile_ranks_within_trade_origin_and_horizon():
    df = pd.DataFrame({"origin_idx": [1, 1, 1, 1, 2, 2], "horizon": [3, 3, 3, 3, 3, 3]})
    trade = np.array(["a", "a", "a", "a", "b", "b"])
    p = EW.cohort_percentile(df, np.array([4.0, 1.0, 3.0, 2.0, 5.0, 6.0]), trade)
    assert np.allclose(p, [100, 25, 75, 50, 50, 100])


def test_flag_levels_follow_the_percentile_cut_points():
    p = np.array([100, 90, 89.9, 75, 74.9, 50, 25, 25.1, 10, 9.9, np.nan])
    code = EW.flag_code(p)
    assert list(code[:-1]) == [0, 0, 1, 1, 2, 2, 3, 2, 4, 4]
    assert np.isnan(code[-1])


def test_flag_precision_is_exact_when_the_forecast_is_perfect():
    rng = np.random.default_rng(0)
    n = 400
    p = rng.random(n) * 100
    cf = pd.DataFrame({"horizon": np.full(n, 6), "volume": "normal", "p_fc": p, "p_act": p, "p_now": rng.random(n) * 100})
    t = EW.flag_table(cf, "w")
    m = t[(t.source == "model") & (t.volume == "all") & (t.band == "1-12")].set_index("flag")
    assert m.loc["Shortage alert", "precision_decile"] == 1.0 and m.loc["Oversupply alert", "precision_decile"] == 1.0
    assert m.loc["Shortage watch", "precision_decile"] == 0.0               # a watch (75-90th percentile) is not in the top decile
    assert m.loc["Shortage watch", "precision_quartile"] == 1.0
    assert m.loc["Shortage alert", "recall_decile_alert_or_watch"] == 1.0


# ---- confidence labels -------------------------------------------------------------------------------------------------------------------------
def test_label_thresholds_and_low_volume_demotion():
    w = np.array([3.0, 8.0, 8.1, 20.0, 20.1])
    assert list(EW.label_from_wape(w, np.zeros(5, bool))) == ["High", "High", "Medium", "Medium", "Low"]
    assert list(EW.label_from_wape(w, np.ones(5, bool))) == ["Medium", "Medium", "Low", "Low", "Low"]


# ---- recorded results --------------------------------------------------------------------------------------------------------------------------
def test_deployed_calibration_covers_every_target_and_horizon():
    need(C.DATA / "interval_calibration.csv")
    t = pd.read_csv(C.DATA / "interval_calibration.csv")
    for k in "EVS":
        sub = t[t.target == k]
        assert set(sub.horizon) == set(range(1, 61))
        assert sub.groupby("group").horizon.nunique().eq(60).all()
    assert (t.lo < 0).all() and (t.hi > 0).all() and (t.lo_wide < 0).all() and (t.hi_wide > 0).all()
    assert t[["lo", "hi", "lo_wide", "hi_wide"]].notna().all().all()
    e = t[(t.target == "E") & (t.group == "Construction")].set_index("horizon")
    assert e.loc[60, "hi"] - e.loc[60, "lo"] > e.loc[1, "hi"] - e.loc[1, "lo"]


def test_interval_coverage_is_recorded_for_every_window_and_not_overstated():
    need(EVAL / "interval_coverage.csv")
    c = pd.read_csv(EVAL / "interval_coverage.csv")
    fwd = c[(c.calibration == "forward") & (c.slice == "all")].set_index(["window", "target"]).coverage
    assert set(fwd.index) == {(w, k) for w in ("test", "stress") for k in "EVS"}
    assert 0.80 < fwd[("test", "E")] < 0.95                      # employed workers: close to the 90% aim in ordinary years
    assert fwd[("stress", "E")] < 0.5                            # and far below it when a shock arrives that no earlier window contained: the result must stay visible
    assert {"leave_one_window_out"} <= set(c.calibration)


def test_flags_beat_the_base_rate_and_are_compared_with_persistence():
    need(EVAL / "flag_precision.csv")
    f = pd.read_csv(EVAL / "flag_precision.csv")
    a = f[(f.volume == "all") & (f.band == "all horizons") & (f.window == "test") & f.flag.isin(["Shortage alert", "Oversupply alert"])]
    assert set(a.source) == {"model", "persistence"}
    assert (a.lift_decile > 3).all()                               # alerts hold many more tail districts than chance
    m = a[a.source == "model"].precision_decile.to_numpy()
    p = a[a.source == "persistence"].precision_decile.to_numpy()
    assert (m >= p - 0.01).all()


def test_confidence_cells_are_complete():
    need(C.DATA / "confidence_cells.csv")
    t = pd.read_csv(C.DATA / "confidence_cells.csv")
    assert len(t) == 3 * 25 * 5 and t.notna().all().all()
    assert set(t.label_normal_volume) <= {"High", "Medium", "Low"}
    order = {"High": 0, "Medium": 1, "Low": 2}
    assert (t.label_low_volume.map(order) >= t.label_normal_volume.map(order)).all()


def test_confidence_labels_rank_the_error_for_employed_workers_in_ordinary_years():
    need(EVAL / "confidence_labels.csv")
    c = pd.read_csv(EVAL / "confidence_labels.csv")
    e = c[(c.window == "test") & (c.target == "E") & (c.band == "all horizons")].set_index("label").wape_pct
    assert e["High"] < e["Medium"] < e["Low"]


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except unittest.SkipTest as e:
                print("SKIP", name, e)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e)[:300])
    sys.exit(1 if fails else 0)
