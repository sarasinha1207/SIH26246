"""v4 phase 2 tests: the simulated trade-level panel (317 districts x 25 trades x 312 months) is complete, positive, reproducible and adds up from trades to sectors.
The first group builds a six-district panel on the fly (always runs); the second group checks the full panel written by src/v4/generate.py and is skipped when
that git-ignored file has not been built.   Runs under pytest or standalone: python tests/test_v4_data.py"""
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

_guard.skip_module_unless(C.DATA / "district_catalog.csv", C.DATA / "DATA_MANIFEST.json", C.DATA / "dim_series.csv", why="needs the v4 catalogue and manifest")
import generate as G  # noqa: E402

CAT = pd.read_csv(C.DATA / "district_catalog.csv")
SUB = CAT[CAT.District_Name.isin(["Bengaluru Urban", "Surat", "Lucknow", "Wayanad", "Pune", "The Dangs"])]
PANEL_FILE = C.DATA / "raw" / "trade_monthly_2000_2025.parquet"
CORE = ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Training_Seats_Sanctioned"]
_cache = {}


def sub():
    if "sub" not in _cache:
        _cache["sub"] = G.generate(SUB)
    return _cache["sub"]


def full():
    if not PANEL_FILE.exists():
        raise unittest.SkipTest("the full panel is not built (python src/v4/generate.py)")
    if "full" not in _cache:
        _cache["full"] = pd.read_parquet(PANEL_FILE), pd.read_csv(C.DATA / "dim_series.csv")
    return _cache["full"]


# ---- six-district panel (always) ------------------------------------------------------------------------------------------------------------------
def test_shape_and_ids():
    trade, sector, dim = sub()
    assert len(dim) == 6 * 25 and len(trade) == 6 * 25 * 312 and len(sector) == 6 * 5 * 312
    assert dim.Series_ID.is_unique and dim.Series_ID.is_monotonic_increasing and set(trade.Series_ID) == set(dim.Series_ID)
    assert (trade.groupby("Series_ID").size() == 312).all() and dim.groupby("Sector_Name").Trade_Code.nunique().eq(5).all()
    assert trade.Date.min() == pd.Timestamp("2000-01-01") and trade.Date.max() == pd.Timestamp("2025-12-01")
    assert dim.Series_ID.iloc[0].count("-") == 2 and dim.Trade_Code.str.match(r"^[A-Z]{3}-\d{4}$").all()


def test_targets_are_positive_and_complete():
    trade = sub()[0]
    assert (trade[CORE] >= 1).all().all() and (trade.Trainees_Certified_Monthly >= 0).all()
    core_cols = CORE + ["Trainees_Certified_Monthly", "Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "District_Total_Population_Est", "Female_Share_Pct"]
    assert not trade[core_cols].isna().any().any()
    assert trade.Unemployment_Rate_Pct.between(3.5, 12).all() and trade.Female_Share_Pct.between(0, 100).all()


def test_trades_add_up_to_their_sector_exactly():
    trade, sector, dim = sub()
    m = trade.merge(dim[["Series_ID", "District_LGD_Code", "Sector_Name"]], on="Series_ID")
    cols = CORE + ["Trainees_Certified_Monthly"]
    g = m.groupby(["District_LGD_Code", "Sector_Name", "Date"])[cols].sum().reset_index()
    x = g.merge(sector, on=["District_LGD_Code", "Sector_Name", "Date"], suffixes=("", "_s"))
    assert len(x) == len(sector)
    for c in cols:
        assert (x[c] == x[c + "_s"]).all(), c


def test_the_same_seed_gives_the_same_data():
    a = G.content_hash(sub()[0])
    b = G.content_hash(G.generate(SUB)[0])
    assert a == b
    assert a != G.content_hash(G.generate(SUB, seed=7)[0])


def test_source_channels_start_on_their_dates():
    trade = sub()[0]
    first = lambda c: trade.dropna(subset=[c]).Date.min()
    assert not trade.Sig_Portal_Postings.isna().any() and first("Sig_Hiring_Survey_Index") == pd.Timestamp("2009-01-01")
    assert first("Sig_NCS_Vacancies") == pd.Timestamp("2015-07-01") and first("Sig_Labour_Survey_Employment") == pd.Timestamp("2017-07-01")
    assert (trade.Sig_Portal_Postings.dropna() >= 0).all() and (trade.Sig_NCS_Vacancies.dropna() >= 0).all()


def test_covid_hits_sectors_in_the_modelled_direction():
    trade, _, dim = sub()
    m = trade.merge(dim[["Series_ID", "Sector_Name"]], on="Series_ID")
    e = m.groupby(["Sector_Name", "Date"]).Total_Employed_Workers.sum().unstack(0)
    chg = e.loc["2020-04-01"] / e.loc["2020-02-01"] - 1
    assert chg["Construction"] < -0.3 and chg["Manufacturing"] < -0.2 and chg["Textiles and Apparel"] < -0.2 and chg["Healthcare"] > 0 and chg["IT-ITeS"] > 0


def test_eshram_ramp_raises_registered_seekers():
    trade = sub()[0]
    s = trade.groupby("Date").eShram_Registered_Seekers.sum(); e = trade.groupby("Date").Total_Employed_Workers.sum()
    r = s / e
    assert r.loc["2024-12-01"] > 1.5 * r.loc["2021-06-01"]


def test_trade_mix_differs_between_trades_and_drifts():
    trade, _, dim = sub()
    m = trade.merge(dim[["Series_ID", "Trade_Code", "Sector_Name"]], on="Series_ID")
    q = m[(m.Sector_Name == "IT-ITeS") & m.Date.isin(pd.to_datetime(["2000-12-01", "2025-12-01"]))].groupby(["Date", "Trade_Code"]).Total_Employed_Workers.sum().unstack(0)
    share = q / q.sum()
    assert share.max().max() < 0.6 and share.min().min() > 0.03
    assert share.loc["ITS-2512", pd.Timestamp("2025-12-01")] > share.loc["ITS-2512", pd.Timestamp("2000-12-01")]          # software developers gain share
    assert share.loc["ITS-3512", pd.Timestamp("2025-12-01")] < share.loc["ITS-3512", pd.Timestamp("2000-12-01")]          # user-support technicians lose share


# ---- full panel (when built) --------------------------------------------------------------------------------------------------------------------
def test_full_panel_matches_the_manifest():
    trade, dim = full()
    man = json.loads((C.DATA / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
    assert len(trade) == man["rows"] == 7925 * 312 and trade.Series_ID.nunique() == man["series"] == len(dim) == 7925
    assert dim.District_LGD_Code.nunique() == 317 and dim.State_Name.nunique() == 10 and dim.Sector_Name.nunique() == 5 and dim.Trade_Code.nunique() == 25
    assert G.content_hash(trade) == man["content_sha256"]


def test_full_panel_is_complete_and_positive():
    trade, _ = full()
    assert (trade[CORE] >= 1).all().all() and not trade[CORE + ["Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "District_Total_Population_Est"]].isna().any().any()
    assert trade.groupby("Series_ID").size().eq(312).all()


def test_full_panel_levels_are_plausible():
    trade, dim = full()
    last = trade[trade.Date == "2025-12-01"].merge(dim[["Series_ID", "Sector_Name"]], on="Series_ID").groupby("Sector_Name").Total_Employed_Workers.sum() / 1e6
    assert 20 < last["Manufacturing"] < 35 and 30 < last["Construction"] < 50 and 3 < last["IT-ITeS"] < 7 and 5 < last["Healthcare"] < 11 and 8 < last["Textiles and Apparel"] < 16


def test_dominant_states_are_larger_per_head_than_the_rest():
    trade, dim = full()
    cat = CAT.set_index("District_LGD_Code")
    x = trade[trade.Date == "2025-12-01"].merge(dim[["Series_ID", "State_Name", "Sector_Name", "District_LGD_Code"]], on="Series_ID")
    e = x.groupby(["State_Name", "Sector_Name"]).Total_Employed_Workers.sum().unstack()
    pop = cat.groupby("State_Name").Pop_2011.sum()
    dens = e.div(pop, axis=0)
    for sector, state in C.DOMINANT.items():
        others = dens[sector].drop(["Delhi", "West Bengal", state])
        assert dens.loc[state, sector] > others.median(), (sector, state)


def test_every_trade_exists_in_every_district():
    trade, dim = full()
    assert dim.groupby("District_LGD_Code").size().eq(25).all() and dim.groupby(["District_LGD_Code", "Sector_Name"]).size().eq(5).all()


def test_survey_index_follows_vacancies_within_each_series():
    trade, _ = full()
    x = trade[trade.Date >= "2010-01-01"].dropna(subset=["Sig_Hiring_Survey_Index"])
    x = x.assign(lv=np.log(x.Active_Job_Vacancies), ls=np.log(x.Sig_Hiring_Survey_Index))
    dv = x.lv - x.groupby("Series_ID").lv.transform("mean"); ds = x.ls - x.groupby("Series_ID").ls.transform("mean")
    assert np.corrcoef(dv, ds)[0, 1] > 0.65                                           # about 0.77: quarterly, lagged and noisy


if __name__ == "__main__":
    fails = skips = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except unittest.SkipTest as e:
                skips += 1
                print("SKIP", name, e)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
