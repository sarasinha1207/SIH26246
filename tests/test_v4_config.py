"""v4 phase 0 tests: the scope in src/v4/config.py is what the project brief asks for and matches the district list on disk.
Runs under pytest or standalone: python tests/test_v4_config.py"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "v4"))
sys.path.insert(0, str(ROOT / "tests"))
import _guard  # noqa: E402
import config as C  # noqa: E402

_guard.skip_module_unless(C.NCO_CROSSWALK, C.LGD_FILE, why="needs the NCO crosswalk and the v4 district list")
LGD = pd.read_csv(C.LGD_FILE)
TRADES = C.load_trades()


def test_ten_states_and_317_districts():
    assert len(C.STATES) == 10 and C.N_DISTRICTS == 317 == sum(C.DISTRICTS_PER_STATE.values())
    assert set(C.STATES) == set(C.DISTRICTS_PER_STATE)
    assert {"Gujarat", "Uttar Pradesh", "Karnataka", "Telangana", "Kerala", "Punjab", "Maharashtra", "Tamil Nadu", "Delhi", "West Bengal"} == set(C.STATES)


def test_district_list_matches_the_config():
    assert len(LGD) == 317 and LGD.dist_lgd.is_unique
    by_state = LGD.groupby("stname").size()
    assert {k.title().replace("Nct Of ", ""): v for k, v in by_state.items()} == C.DISTRICTS_PER_STATE
    codes = LGD.groupby("stname").state_lgd.first()
    assert {k.title(): int(v) for k, v in codes.items()} == C.STATES


def test_five_sectors_with_five_trades_each():
    assert len(C.SECTORS) == 5 and len(TRADES) == 25 == len(C.SECTORS) * C.TRADES_PER_SECTOR
    assert (TRADES.groupby("Sector_Name").size() == 5).all() and TRADES.Trade_Code.is_unique
    assert set(TRADES.Sector_Name) == set(C.SECTORS)


def test_series_count():
    assert C.n_series() == 7925 == C.N_DISTRICTS * len(TRADES)
    assert C.series_id(489, "MFG-7223") == "489-MFG-7223"


def test_history_and_forecast_calendar():
    assert len(C.MONTHS) == C.N_MONTHS == 312 and str(C.MONTHS[0]) == "2000-01" and str(C.MONTHS[-1]) == "2025-12"
    assert C.ORIGIN == "2025-12" and len(C.HORIZONS) == 60 and C.HORIZONS[-1] == 60
    assert len(C.FORECAST_MONTHS) == 60 and str(C.FORECAST_MONTHS[0]) == "2026-01" and str(C.FORECAST_MONTHS[-1]) == "2030-12"
    assert C.FORECAST_MONTHS[0] == C.MONTHS[-1] + 1


def test_sector_state_weights_follow_the_brief():
    assert C.sector_state_weight("Manufacturing", "Gujarat") == 1.6 and C.sector_state_weight("Manufacturing", "Tamil Nadu") == 1.25
    assert C.sector_state_weight("Construction", "Uttar Pradesh") == 1.6 and C.sector_state_weight("IT-ITeS", "Karnataka") == 1.6
    assert C.sector_state_weight("Healthcare", "Tamil Nadu") == 1.6 and C.sector_state_weight("Textiles and Apparel", "Tamil Nadu") == 1.6
    assert C.sector_state_weight("Textiles and Apparel", "Punjab") == 1.25 and C.sector_state_weight("Manufacturing", "Kerala") == 1.0
    assert all(C.DOMINANT[s] in C.STATES and set(C.RUNNERS_UP[s]) <= set(C.STATES) for s in C.SECTORS)
    assert all(C.sector_state_weight(s, st) == 1.0 for s in C.SECTORS for st in ("Delhi", "West Bengal"))


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
