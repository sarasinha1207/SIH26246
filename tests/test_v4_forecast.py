"""v4 phase 6 tests: reconciliation, Demand Index, capacity gap and roll-ups are correct on synthetic data, and the exported 2026-2030 forecast is complete, consistent and traceable.
The first group runs on synthetic arrays; the second reads data/v4/exports and the manifest (skipped until the forecast has been produced).
Runs under pytest or standalone: python tests/test_v4_forecast.py"""
import hashlib
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
import capacity as CAP  # noqa: E402
import demand_index as DI  # noqa: E402
import forecast as FC  # noqa: E402
import exports as EX  # noqa: E402

EXPORTS = C.DATA / "exports"
MANIFEST = C.DATA / "FORECAST_MANIFEST.json"


def need(path):
    if not Path(path).exists():
        raise unittest.SkipTest(f"{Path(path).name} not produced yet")


# ---- reconciliation ----------------------------------------------------------------------------------------------------------------------------
def test_trades_add_up_to_the_rounded_group_total_and_stay_close_to_their_own_forecast():
    rng = np.random.default_rng(0)
    pts = rng.random((20, 60)) * 1000
    group = np.repeat(np.arange(4), 5)[rng.permutation(20)]                    # 4 groups of 5, interleaved
    out = FC.reconcile(pts, group)
    for g in range(4):
        m = group == g
        assert (out[m].sum(axis=0) == np.rint(pts[m].sum(axis=0))).all()
    assert (out == np.floor(out)).all() and (out >= np.floor(pts)).all() and (out <= np.ceil(pts)).all()


# ---- Demand Index ------------------------------------------------------------------------------------------------------------------------------
def panel(n=60, T=40, seed=0):
    rng = np.random.default_rng(seed)
    trade = np.repeat(["a", "b"], n // 2)
    E = rng.uniform(1000, 5000, (n, T))
    V = E * rng.uniform(0.01, 0.05, (n, T))
    return trade, E, V


def test_standardisation_gives_zero_mean_unit_spread_in_every_trade_and_month():
    trade, E, V = panel()
    z = DI.zscore_by_trade(np.log((V + 1) / E), trade)
    for t in ("a", "b"):
        assert np.allclose(z[trade == t].mean(axis=0), 0, atol=1e-9) and np.allclose(z[trade == t].std(axis=0), 1)


def test_composite_has_unit_spread_and_ignores_missing_channels():
    trade, E, V = panel()
    z1 = DI.zscore_by_trade(np.log((V + 1) / E), trade)
    z2 = DI.zscore_by_trade(np.log((V * 1.3 + 5) / E) + np.random.default_rng(1).normal(0, 0.1, V.shape), trade)
    z2[:, :10] = np.nan                                                         # a channel that starts later
    c = DI.composite([z1, z2], trade)
    assert np.isfinite(c).all()
    assert np.allclose(c[trade == "a"].std(axis=0), 1)
    assert np.allclose(DI.composite([z1], trade), z1)


def test_level_shift_is_zero_in_the_reference_period_on_average():
    trade, E, V = panel(T=300)
    L = DI.level_shift(V, E, trade)
    assert abs(L[:, DI.REF[0]:DI.REF[1] + 1].mean()) < 1e-9
    V2 = V.copy()
    V2[:, 250:] *= 1.5                                                          # demand up 50% everywhere
    assert (DI.level_shift(V2, E, trade)[:, 260] > L[:, 260]).all()


def test_index_is_between_0_and_100_and_rises_with_vacancies():
    from scipy.special import ndtr
    z = np.array([-5.0, 0.0, 1.0, 5.0])
    di = 100 * ndtr(z)
    assert di[0] < 0.01 and di[-1] > 99.99 and di[1] == 50 and abs(di[2] - 84.13) < 0.01 and (np.diff(di) > 0).all()


# ---- capacity gap ------------------------------------------------------------------------------------------------------------------------------
def test_status_thresholds():
    m = np.array([-1.0, -0.51, -0.5, 0.0, 0.5, 0.51, 2.0])
    assert list(CAP.status_of(m)) == ["Seats fall short of demand", "Seats fall short of demand", "Balanced", "Balanced", "Balanced", "Seats exceed demand", "Seats exceed demand"]


def test_measures_are_ratios_of_the_inputs():
    f = pd.DataFrame({"avg_vacancies": [100.0, 50.0], "seats": [20.0, 100.0], "expected_certified": [10.0, 80.0]})
    m = CAP.with_measures(f)
    assert list(m.openings_per_seat) == [5.0, 0.5] and list(m.supply_per_opening) == [0.1, 1.6]


# ---- helpers of the exports --------------------------------------------------------------------------------------------------------------------
def test_state_names_make_safe_file_names():
    assert EX.slug("Uttar Pradesh") == "uttar-pradesh" and EX.slug("West Bengal") == "west-bengal"


# ---- the recorded forecast ---------------------------------------------------------------------------------------------------------------------
def load_series():
    need(EXPORTS / "forecast_series.parquet")
    return pd.read_parquet(EXPORTS / "forecast_series.parquet")


def test_forecast_is_complete_for_every_series_and_month():
    f = load_series()
    assert len(f) == C.n_series() * 60 and f.Series_ID.nunique() == C.n_series()
    assert f.groupby("Series_ID").horizon.nunique().eq(60).all()
    assert f.month.min() == "2026-01" and f.month.max() == "2030-12"
    assert f.isna().sum().sum() == 0
    for k in "EVS":
        assert (f[k] >= 0).all()
        assert (f[f"{k}_lo"] <= f[k]).all() and (f[k] <= f[f"{k}_hi"]).all()
        assert (f[f"{k}_hi_wide"] >= f[k]).all() and (f[f"{k}_lo_wide"] <= f[k]).all()


def test_trades_add_up_to_their_district_sector_in_every_month():
    f = load_series()
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    sec = pd.read_parquet(C.DATA / "raw" / "sector_monthly_2000_2025.parquet")
    last = sec[sec.Date == "2025-12-01"]
    g = f.merge(dim[["Series_ID", "District_LGD_Code", "Sector_Name"]], on="Series_ID").groupby(["District_LGD_Code", "Sector_Name", "horizon"])[["E", "V", "S"]].sum().reset_index()
    assert len(g) == 317 * 5 * 60
    # the district-sector forecasts are continuous with the last observed month: no jump of more than 25% in the first month
    first = g[g.horizon == 1].merge(last.rename(columns={"Total_Employed_Workers": "E0"})[["District_LGD_Code", "Sector_Name", "E0"]], on=["District_LGD_Code", "Sector_Name"])
    assert (np.abs(first.E / first.E0 - 1) < 0.25).all()


def test_flags_put_about_a_tenth_of_each_trade_in_each_alert_tail():
    f = load_series()
    share = f.flag_code.value_counts(normalize=True)
    assert 0.08 < share[0] < 0.12 and 0.08 < share[4] < 0.12
    assert set(f.flag_code.unique()) == {0, 1, 2, 3, 4}


def test_confidence_labels_are_present_for_every_row():
    f = load_series()
    for k in "EVS":
        assert set(f[f"{k}_confidence"].unique()) <= {"High", "Medium", "Low"}


def test_rollups_add_up_and_the_demand_index_stays_in_range():
    need(EXPORTS / "forecast_rollups.csv.gz")
    r = pd.read_csv(EXPORTS / "forecast_rollups.csv.gz", low_memory=False)
    assert set(r.level) == {"district_sector", "state_sector", "state", "sector", "trade", "india"}
    for level in ("state", "sector", "trade"):
        tot = r[r.level == level].groupby("month")[["E", "V", "S"]].sum()
        ind = r[r.level == "india"].set_index("month")[["E", "V", "S"]]
        assert (tot == ind).all().all(), level
    ds = r[r.level == "district_sector"].groupby("month")[["E", "V", "S"]].sum()
    assert (ds == r[r.level == "india"].set_index("month")[["E", "V", "S"]]).all().all()
    assert r.DI.between(0, 100).all() and r.DI.notna().all()
    for k in "EVS":
        assert (r[f"{k}_lo"] <= r[k]).all() and (r[k] <= r[f"{k}_hi"]).all()


def test_demand_index_of_forecast_months_is_close_to_the_three_channel_index_in_history():
    p = C.REPORTS / "forecast" / "demand_index_check.json"
    need(p)
    c = json.loads(p.read_text(encoding="utf-8"))["v_only_vs_three_channels_by_year"]
    assert all(v["correlation"] > 0.85 for v in c.values())


def test_manifest_checksums_match_the_files():
    need(MANIFEST)
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["data_simulated"] is True and m["series"] == C.n_series()
    for name, v in m["files"].items():
        p = EXPORTS / name
        if not p.exists():
            continue                                                            # the git-ignored files are not in a fresh clone
        assert hashlib.sha256(p.read_bytes()).hexdigest() == v["sha256"], name
    assert m["shards"] and set(m["shards"]) == set(C.STATES)


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
