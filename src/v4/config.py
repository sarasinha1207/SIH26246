"""
KaushalSetu v4 - single source of truth for the scope of the pilot.

10 states with every district, 5 sectors with 5 NCO-2015 trades each, monthly history 2000-01 to 2025-12 (312 months) and a
60-month forecast (2026-01 to 2030-12).  Every other v4 module imports its scope from here; nothing about states, sectors,
trades, dates or horizons is typed anywhere else.

The data is SIMULATED.  The weights below are modelling assumptions, not statistics.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "v4"
MODELS = ROOT / "models" / "v4"
OUTPUTS = ROOT / "outputs" / "v4"
REPORTS = ROOT / "reports" / "v4"
LGD_FILE = DATA / "lgd_districts_10_states.csv"              # district names, official LGD codes and areas (from the LGD 2024 layer)
NCO_CROSSWALK = ROOT / "data" / "raw" / "sector_nco_crosswalk.csv"

SEED = 42

# ---- time ------------------------------------------------------------------------------------------------------------
HISTORY_START, HISTORY_END = "2000-01", "2025-12"
N_MONTHS = 312                                               # 26 years
MONTHS = pd.period_range(HISTORY_START, HISTORY_END, freq="M")
ORIGIN = HISTORY_END                                         # forecast origin: the last observed month
HORIZONS = list(range(1, 61))                                # 1..60 months ahead
FORECAST_MONTHS = pd.period_range("2026-01", "2030-12", freq="M")
TARGETS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}

# ---- geography: the state name is the LGD name, the code is the LGD state code ---------------------------------------
STATES = {
    "Delhi": 7, "Gujarat": 24, "Karnataka": 29, "Kerala": 32, "Maharashtra": 27,
    "Punjab": 3, "Tamil Nadu": 33, "Telangana": 36, "Uttar Pradesh": 9, "West Bengal": 19,
}
DISTRICTS_PER_STATE = {                                      # LGD 2024 layer; checked against the file in tests
    "Delhi": 11, "Gujarat": 33, "Karnataka": 31, "Kerala": 14, "Maharashtra": 36,
    "Punjab": 23, "Tamil Nadu": 38, "Telangana": 33, "Uttar Pradesh": 75, "West Bengal": 23,
}
N_DISTRICTS = sum(DISTRICTS_PER_STATE.values())              # 317

# ---- sectors and trades ----------------------------------------------------------------------------------------------
SECTORS = {                                                  # name -> short code (as in v3)
    "Manufacturing": "MFG", "Construction": "CON", "IT-ITeS": "ITS", "Healthcare": "HLT", "Textiles and Apparel": "TXT",
}
TRADES_PER_SECTOR = 5


def load_trades():
    """The 25 trades: the NCO-2015 families of data/raw/sector_nco_crosswalk.csv (all verified present in NCO-Codes.xlsx)."""
    cw = pd.read_csv(NCO_CROSSWALK)
    rows = []
    for sector, code in SECTORS.items():
        for family, title in cw[cw.Sector_Name == sector][["NCO_2015_Family", "NCO_2015_Title"]].itertuples(index=False):
            rows.append({"Sector_Name": sector, "Sector_Code": code, "NCO_Code": int(family), "Trade_Name": title, "Trade_Code": f"{code}-{int(family)}"})
    return pd.DataFrame(rows)


# ---- state x sector weights (assumption) -----------------------------------------------------------------------------
# From the project brief: the dominant state and the runner-up states of each sector.  A sector's size in a state is multiplied by
# DOMINANT_WEIGHT, RUNNER_UP_WEIGHT or 1.0.  Delhi and West Bengal are not in the brief's table, so every sector there has weight 1.0.
DOMINANT = {"Manufacturing": "Gujarat", "Construction": "Uttar Pradesh", "IT-ITeS": "Karnataka", "Healthcare": "Tamil Nadu", "Textiles and Apparel": "Tamil Nadu"}
RUNNERS_UP = {
    "Manufacturing": ["Tamil Nadu", "Maharashtra"],
    "Construction": ["Maharashtra", "Karnataka", "Gujarat"],
    "IT-ITeS": ["Maharashtra", "Telangana", "Tamil Nadu"],
    "Healthcare": ["Kerala", "Maharashtra", "Telangana"],
    "Textiles and Apparel": ["Gujarat", "Maharashtra", "Punjab"],
}
DOMINANT_WEIGHT, RUNNER_UP_WEIGHT = 1.6, 1.25


def sector_state_weight(sector, state):
    if DOMINANT[sector] == state:
        return DOMINANT_WEIGHT
    return RUNNER_UP_WEIGHT if state in RUNNERS_UP[sector] else 1.0


def n_series():
    return N_DISTRICTS * len(SECTORS) * TRADES_PER_SECTOR


def series_id(lgd_code, trade_code):
    """Series id: official district LGD code + trade code, for example 489-MFG-7223."""
    return f"{int(lgd_code)}-{trade_code}"
