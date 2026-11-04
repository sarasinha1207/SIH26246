"""v4 phase 4 tests: scoring helpers are exact, the model inputs are the intended ones, and the recorded results are complete and honest.
The first group runs on synthetic arrays; the second reads reports/v4/evaluation (skipped until the models have been run).
Runs under pytest or standalone: python tests/test_v4_models.py"""
import json
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
import evaluate as EV  # noqa: E402
import features as F  # noqa: E402
import model_lib as M  # noqa: E402
import splits as SP  # noqa: E402

EVAL = C.REPORTS / "evaluation"


def need(*names):
    for n in names:
        if not (EVAL / n).exists():
            raise unittest.SkipTest(f"{n} not produced yet")


# ---- helpers -----------------------------------------------------------------------------------------------------------------------------------
def test_wape_is_the_level_scale_percentage_error():
    base = np.log(np.array([100.0, 200.0]))
    actual = np.log(np.array([110.0, 180.0])) - base
    pred = np.log(np.array([100.0, 200.0])) - base
    assert abs(M.wape(pred, actual, base) - (10 + 20) / (110 + 180) * 100) < 1e-6
    assert M.wape(actual, actual, base) == 0


def test_bands_cover_the_sixty_horizons():
    assert M.BAND_LABELS == ["1-12", "13-24", "25-36", "37-48", "49-60"]
    assert list(M.band_of([1, 12, 13, 24, 25, 48, 49, 60])) == ["1-12", "1-12", "13-24", "13-24", "25-36", "37-48", "49-60", "49-60"]
    w = M.band_wapes(np.zeros(3), np.array([0.1, 0.1, 0.1]), np.zeros(3), np.array([1, 30, 60]))
    assert np.isnan(w["13-24"]) and w["1-12"] > 0


def test_model_inputs_follow_the_documented_rules():
    cols = ["E_mom12", "trd_E_mom12", "sec_V_dev12", "ss_S_mom3", "cat_sector", "cat_trade", "cat_state", "cat_tier", "cat_district", "log_pop", "horizon", "series_row"]
    chosen = M.input_columns([c for c in cols if c != "log_pop"])
    assert chosen == ["E_mom12", "cat_sector", "cat_trade", "cat_state", "horizon"]
    assert "trd_E_mom12" in M.input_columns(cols, "all_candidates") and "cat_district" in M.input_columns(cols, "no_groups")
    assert not [c for c in M.input_columns(cols, "no_identity") if c.startswith("cat_")]


def test_slice_table_matches_a_direct_computation():
    rng = np.random.default_rng(3)
    n = 40000
    ns = 60                                                                    # more than 25 trades: slice codes above 127 must not overflow
    me = pd.DataFrame({"series_row": rng.integers(0, ns, n), "horizon": rng.integers(1, 61, n), "shock_EV": rng.random(n) < 0.3, "shock_S": rng.random(n) < 0.3})
    dim = pd.DataFrame({"Sector_Name": list("AB") * (ns // 2), "Trade_Code": [f"T{i}" for i in range(ns)], "State_Name": list("XXYYZZ") * (ns // 6)})
    stats = pd.DataFrame({"Low_Volume_Train": [True, False] * (ns // 2)})
    base = rng.normal(8, 1, n).astype(np.float32)
    actual = rng.normal(0.1, 0.1, n)
    preds = {"model": actual + rng.normal(0, 0.03, n), "naive": np.zeros(n), "seasonal_naive": rng.normal(0, 0.05, n), "damped_trend": np.full(n, 0.05)}
    tab = EV.table("w", "E", me, dim, stats, actual, base, preds)
    row = tab[(tab.slice == "sector") & (tab.value == "A") & (tab.band == "13-24")].iloc[0]
    m = (dim.Sector_Name.to_numpy()[me.series_row] == "A") & (M.band_of(me.horizon) == "13-24")
    assert abs(row.wape_model - M.wape(preds["model"][m], actual[m], base[m])) < 1e-6 and row.rows == m.sum()
    assert abs(row.wape_naive - M.wape(preds["naive"][m], actual[m], base[m])) < 1e-6
    allrow = tab[(tab.slice == "all") & (tab.band == "all horizons")].iloc[0]
    assert abs(allrow.wape_model - M.wape(preds["model"], actual, base)) < 1e-6 and allrow.rows == n
    assert (tab.wape_best_baseline <= tab[["wape_naive", "wape_seasonal_naive", "wape_damped_trend"]].max(axis=1) + 1e-9).all()


def test_baselines_use_only_origin_information():
    X = pd.DataFrame({"E_ya_h": [0.1, np.nan], "E_sf_shift": [0.01, 0.02], "E_mom36_pa": [0.06, 0.06]})
    meta = pd.DataFrame({"horizon": [12, 24]})
    b = M.baselines(X, meta, "E")
    assert np.allclose(b["naive"], 0) and np.allclose(b["seasonal_naive"], [0.1, 0.0]) and np.allclose(b["damped_trend"], [0.06 * 0.5 + 0.01, 0.12 * 0.5 * 1 + 0.02])


# ---- recorded results ----------------------------------------------------------------------------------------------------------------------------
def test_tuned_parameters_are_inside_the_search_space():
    need("best_params.json")
    best = json.loads((EVAL / "best_params.json").read_text(encoding="utf-8"))
    assert set(best) == {"E", "V", "S"}
    for k, b in best.items():
        p = b["params"]
        assert 3 <= p["max_depth"] <= 7 and 50 <= p["min_child_weight"] <= 2000 and 0.5 <= p["subsample"] <= 0.9 and 0.3 <= p["colsample_bytree"] <= 0.8
        assert 1 <= p["reg_lambda"] <= 200 and 50 <= b["trees"] <= 400 and b["tuning_rows"] > 1_000_000


def test_each_scored_window_has_complete_tables():
    for window in ("validation", "test", "stress"):
        if not (EVAL / f"{window}_metrics.csv").exists():
            continue
        tab = pd.read_csv(EVAL / f"{window}_metrics.csv")
        s = json.loads((EVAL / f"{window}_summary.json").read_text(encoding="utf-8"))
        assert set(tab.target) == {"E", "V", "S"} and set(tab.band) == set(M.BAND_LABELS) | {"all horizons"}
        assert tab[["wape_model", "wape_best_baseline"]].notna().all().all() and (tab.rows > 0).all()
        lo, hi = SP.window(window)
        assert s["fit_targets_to"] == SP.month(SP.fit_cut_for(window)) and s["seeds"] == list(EV.SEEDS)
        assert not set(s["inputs"]) & F.TIME_PROXY_FEATURES and not any(c.startswith(M.GROUP_PREFIXES) for c in s["inputs"])
        allrows = tab[(tab.slice == "all") & (tab.band == "all horizons")]
        assert (allrows.rows == s["scored_rows"]).all()


def test_scored_once_windows_are_recorded():
    for window in SP.LOCKED:
        if (EVAL / f"{window}_metrics.csv").exists():
            lock = json.loads((EVAL / f"{window}_opened.json").read_text(encoding="utf-8"))
            assert lock["window"] == window and "scored_at_utc" in lock and len(lock["params_sha256"]) == 64


def test_ablation_supports_the_choice_of_inputs():
    need("ablation_validation.csv")
    a = pd.read_csv(EVAL / "ablation_validation.csv")
    a = a[(a.trees == 250)]
    for k in "EVS":
        sub = a[a.target == k].set_index("inputs").mean_band
        assert sub["no_groups"] < sub["all_candidates"], k                    # the group aggregates hurt on validation
        assert sub["chosen"] < sub["all_candidates"], k


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
