"""v4 phase 1 tests: the district catalogue covers every district of the 10 states, with Census 2011 populations that add up to the state totals.
Runs under pytest or standalone: python tests/test_v4_catalog.py"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "v4"))
sys.path.insert(0, str(ROOT / "tests"))
import _guard  # noqa: E402
import config as C  # noqa: E402

CAT_FILE, PROV_FILE = C.DATA / "district_catalog.csv", C.DATA / "district_catalog_provenance.json"
_guard.skip_module_unless(CAT_FILE, PROV_FILE, C.LGD_FILE, C.DATA / "census_2011_district_tables.csv", why="needs the v4 district catalogue")
CAT = pd.read_csv(CAT_FILE)
LGD = pd.read_csv(C.LGD_FILE)
V3 = pd.read_csv(ROOT / "data" / "raw" / "district_catalog.csv") if (ROOT / "data" / "raw" / "district_catalog.csv").exists() else None
PROV = json.loads(PROV_FILE.read_text(encoding="utf-8"))
CENSUS = {"Delhi": 16787941, "Gujarat": 60439692, "Karnataka": 61095297, "Kerala": 33406061, "Maharashtra": 112374333,
          "Punjab": 27743338, "Tamil Nadu": 72147030, "Telangana": 35003674, "Uttar Pradesh": 199812341, "West Bengal": 91276115}
TIERS = {"metro_core", "metro_residential", "metro_administrative", "industrial_it_hub", "industrial_hub", "industrial_msme", "industrial_port",
         "industrial_mining", "textile_cluster", "logistics_hub", "semi_industrial", "agrarian_developing", "agrarian_migrant",
         "peripheral_agrarian", "peripheral_coastal", "peripheral_tribal"}


def pop(name):
    return int(CAT[CAT.District_Name == name].Pop_2011.iloc[0])


def test_every_district_of_the_ten_states_is_present_once():
    assert len(CAT) == 317 and CAT.District_LGD_Code.is_unique and CAT.District_Name.is_unique
    assert set(CAT.District_LGD_Code) == set(LGD.dist_lgd)
    assert CAT.groupby("State_Name").size().to_dict() == C.DISTRICTS_PER_STATE
    assert CAT.groupby("State_Name").State_LGD_Code.first().to_dict() == C.STATES


def test_state_populations_add_up_to_census_2011():
    sums = CAT.groupby("State_Name").Pop_2011.sum()
    for state, total in CENSUS.items():
        assert abs(sums[state] / total - 1) < 0.001, (state, int(sums[state]), total)
    assert PROV["census_2011_state_totals"] == CENSUS


def test_every_population_has_a_census_source():
    assert CAT.Pop_2011.notna().all() and (CAT.Pop_2011 >= 100_000).all()
    assert CAT.Pop_Source.str.startswith("census_2011").all() and not CAT.Pop_Source.str.contains("ESTIMATE").any()
    assert set(PROV["population_sources"]) <= {"census_2011_table", "census_2011 (v3 catalogue)", "census_2011_table, reduced by the district created from it"}


def test_known_district_populations():
    assert pop("Bengaluru Urban") == 9621551 and pop("Hyderabad") == 3943323 and pop("Surat") == 6081322 and pop("Lucknow") == 4589838
    assert pop("Thiruvananthapuram") == 3301427 and pop("Prayagraj") == 5954391 and pop("Mumbai Suburban") == 9356962


def test_districts_split_after_the_census_are_reduced():
    assert abs(pop("Aravalli") + pop("Sabarkantha") - 2428589) < 30000                    # Sabar Kantha before Aravalli was created in 2013
    assert pop("Gurdaspur") + pop("Pathankot") == 2299026
    assert pop("Chhota Udaipur") + pop("Vadodara") == 4165626


def test_tiers_names_growth_and_area():
    assert set(CAT.Econ_Tier) <= TIERS and CAT.Econ_Tier.notna().all()
    assert CAT.Pop_Growth_Annual.between(-0.005, 0.03).all() and (CAT.Area_Km2 > 10).all()
    assert set(CAT.Tier_Source) <= {"v3 catalogue", "named list", "rule on population"}
    assert CAT[CAT.State_Name == "Kerala"].Pop_Growth_Annual.mean() < CAT[CAT.State_Name == "Uttar Pradesh"].Pop_Growth_Annual.mean()


def test_the_56_v3_districts_keep_their_v3_values():
    if V3 is None:
        return
    m = CAT.merge(V3, left_on="District_LGD_Code", right_on="District_LGD_Code", suffixes=("", "_v3"))
    assert len(m) == 56
    assert (m.District_Name == m.District_Name_v3).all() and (m.Econ_Tier == m.Econ_Tier_v3).all() and (m.Pop_Growth_Annual == m.Pop_Growth_Annual_v3.round(4)).all()
    assert (m.Pop_2011 == m.Pop_2011_v3).all() or (abs(m.Pop_2011 / m.Pop_2011_v3 - 1) < 0.001).all()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
