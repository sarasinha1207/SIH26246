"""v4 phase 3 tests: the time windows follow the strict origin rule for all 60 horizons, and no feature looks past its forecast origin.
Runs under pytest or standalone: python tests/test_v4_features.py"""
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

PANEL = C.DATA / "raw" / "trade_monthly_2000_2025.parquet"
_guard.skip_module_unless(C.DATA / "dim_series.csv", C.DATA / "SPLITS_MANIFEST.json", C.REPORTS / "features" / "feature_catalogue.csv", why="needs the v4 phase 3 records")
import features as F  # noqa: E402
import splits as SP  # noqa: E402

DIM = pd.read_csv(C.DATA / "dim_series.csv")
MAN = json.loads((C.DATA / "SPLITS_MANIFEST.json").read_text(encoding="utf-8"))
_cache = {}


def need_panel():
    if not PANEL.exists():
        raise unittest.SkipTest("the panel is not built (python src/v4/generate.py)")
    if "df" not in _cache:
        _cache["df"] = pd.read_parquet(PANEL)
    return _cache["df"]


def subset(df, step=130):
    keep = DIM.Series_ID.iloc[::step]
    return df[df.Series_ID.isin(set(keep))].reset_index(drop=True), DIM[DIM.Series_ID.isin(set(keep))].reset_index(drop=True)


# ---- windows and origin rules -------------------------------------------------------------------------------------------------------------------
def test_windows_tile_the_history_without_gaps():
    w = [SP.window(n) for n in SP.NAMES]
    assert w[0][0] == 0 and w[-1][1] == C.N_MONTHS - 1 and all(a[1] + 1 == b[0] for a, b in zip(w, w[1:]))
    assert [SP.month(SP.window(n)[0]) for n in SP.NAMES] == ["2000-01", "2010-01", "2015-01", "2020-01"]
    assert [SP.month(SP.window(n)[1]) for n in SP.NAMES] == ["2009-12", "2014-12", "2019-12", "2025-12"]
    assert all(b - a + 1 >= 60 for a, b in w)                                    # long enough to evaluate the 60-month horizon with strict origins


def test_fit_rows_only_use_targets_up_to_the_cut():
    for cut in (SP.CUT["train"], SP.CUT["validation"], SP.CUT["test"], SP.CUT["stress"]):
        t, h = SP.fit_pairs(cut)
        assert (t + h <= cut).all() and (t >= SP.MIN_ORIGIN).all() and len(set(zip(t, h))) == len(t)


def test_evaluation_rows_start_after_the_fitted_period_and_stay_in_their_window():
    for name in ("validation", "test", "stress"):
        lo, hi = SP.window(name)
        t, h = SP.eval_pairs(name, unlock=True)
        cut = SP.fit_cut_for(name)
        assert (t >= cut).all() and (t + h >= lo).all() and (t + h <= hi).all()
        assert (t + h > cut).all()                                                # every target is after the last month the model was fitted on
        assert set(np.unique(h)) == set(range(1, 61)), name                      # all 60 horizons are scored with strict origins


def test_test_and_stress_windows_are_locked():
    SP.eval_pairs("validation")
    for name in SP.LOCKED:
        try:
            SP.eval_pairs(name)
        except PermissionError:
            continue
        raise AssertionError(f"{name} opened without unlock")


def test_sampling_is_nested_and_keeps_the_long_horizons():
    t1, h1 = SP.fit_pairs(SP.CUT["stress"], frac=1 / 12)
    t2, h2 = SP.fit_pairs(SP.CUT["stress"], frac=1 / 6)
    assert set(zip(t1, h1)) <= set(zip(t2, h2)) and len(t1) < len(t2)
    for name in ("validation", "test"):
        t, h = SP.eval_pairs(name, unlock=True)
        assert np.bincount(h, minlength=61)[1:].min() >= 1
    t, h = SP.fit_pairs(SP.CUT["train"])
    assert np.bincount(h, minlength=61)[50:].min() >= 6                           # the 50..60 month horizons keep at least 6 origins


def test_manifest_matches_the_code():
    assert MAN["counts"] == json.loads(json.dumps(SP.describe()))
    assert MAN["pair_sha256"]["validation"] == __import__("hashlib").sha256(np.ascontiguousarray(np.stack(SP.eval_pairs("validation", unlock=True))).tobytes()).hexdigest()
    assert MAN["horizons"] == [1, 60] and MAN["sampling_fraction"] == SP.FRAC


# ---- features ---------------------------------------------------------------------------------------------------------------------------------
def test_year_ago_anchor_is_never_after_the_origin_and_matches_the_target_month():
    t = np.arange(36, 312)[:, None]
    h = np.arange(1, 61)[None, :]
    ya = t + h - 12 * ((h + 11) // 12)
    assert (ya <= t).all() and (ya > t - 12).all() and ((t + h - ya) % 12 == 0).all()


def test_no_feature_changes_when_the_future_is_rewritten():
    df = need_panel()
    d1, dim1 = subset(df)
    rng = np.random.default_rng(1)
    d2 = d1.copy()
    cut = 200
    late = (d2.groupby("Series_ID").cumcount() > cut).to_numpy()
    for c in ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Training_Seats_Sanctioned"]:
        d2.loc[late, c] = (d2.loc[late, c] * rng.uniform(1.5, 4.0, late.sum())).astype(np.int32)
    for c in ["Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "Female_Share_Pct", "Trainees_Certified_Monthly", "Sig_Portal_Postings", "Sig_Hiring_Survey_Index",
              "Sig_NCS_Vacancies", "Sig_Labour_Survey_Employment"]:
        d2.loc[late, c] = (d2.loc[late, c] * rng.uniform(0.3, 3.0, late.sum())).astype(d2[c].dtype)
    D1, D2 = F.PanelData(d1, dim1), F.PanelData(d2, dim1)
    OF1, SF1 = F.origin_features(D1)
    OF2, SF2 = F.origin_features(D2)
    t = rng.integers(36, cut + 1, 400)
    h = rng.integers(1, 61, 400)
    X1, m1 = F.assemble(D1, OF1, SF1, t, h)
    X2, m2 = F.assemble(D2, OF2, SF2, t, h)
    pd.testing.assert_frame_equal(X1, X2)                                         # identical features (NaN counts as equal)
    pd.testing.assert_frame_equal(m1, m2)
    far = (m1.target_idx > cut).to_numpy()
    assert far.any() and not np.allclose(F.target_change(D1, m1, "E")[far], F.target_change(D2, m2, "E")[far])      # the targets did change, so the test could fail


def test_target_is_the_log_change_over_the_horizon():
    df = need_panel()
    d1, dim1 = subset(df, step=500)
    D = F.PanelData(d1, dim1)
    OF, SF = F.origin_features(D)
    t, h = np.array([50, 100, 250]), np.array([1, 12, 60])
    X, meta = F.assemble(D, OF, SF, t, h)
    for k in F.KEYS:
        y = F.target_change(D, meta, k)
        s, tt, hh = meta.series_row.to_numpy(), meta.origin_idx.to_numpy(), meta.horizon.to_numpy()
        want = np.log(D.X[k][s, tt + hh]) - np.log(D.X[k][s, tt])
        assert np.allclose(y, want, atol=1e-5)


def test_model_inputs_exclude_time_proxies_and_eval_only_columns():
    df = need_panel()
    d1, dim1 = subset(df, step=500)
    D = F.PanelData(d1, dim1)
    OF, SF = F.origin_features(D)
    X, meta = F.assemble(D, OF, SF, np.array([60, 200]), np.array([5, 40]))
    assert not (set(X.columns) & F.TIME_PROXY_FEATURES) and not (set(X.columns) & F.EVAL_ONLY)
    assert set(F.TIME_PROXY_FEATURES) <= set(OF)
    assert not np.isinf(X.select_dtypes("number").to_numpy()).any()
    assert set(F.CAT_COLS) <= set(X.columns) and X.cat_district.cat.categories.size == len(D.cat_levels["cat_district"])


def test_catalogue_describes_every_candidate_feature():
    cat = pd.read_csv(C.REPORTS / "features" / "feature_catalogue.csv")
    build = json.loads((C.REPORTS / "features" / "phase3_build.json").read_text(encoding="utf-8"))
    assert len(cat) == build["candidate_features"] and cat.feature.is_unique
    assert set(cat[cat.time_proxy].feature) == F.TIME_PROXY_FEATURES
    assert build["model_inputs"] == len(cat) - len(F.TIME_PROXY_FEATURES) and build["series"] == 7925
    assert {"source_channels", "trade_aggregates", "state_sector_aggregates", "sector_aggregates"} <= set(cat.group)
    stats = pd.read_csv(C.DATA / "dim_series_stats.csv")
    assert len(stats) == 7925 and (stats.Series_ID == DIM.Series_ID).all()


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
