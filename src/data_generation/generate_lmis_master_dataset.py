#!/usr/bin/env python3
"""
LMIS synthetic labour-market panel generator - v2 (recalibrated to Indian statistics)
=====================================================================================
Project  : SIH26246 / MSDE - AI-Enabled Labour Market Intelligence & Skill Demand-Supply Forecasting
Output   : data/raw/lmis_district_monthly_2011_2026.csv       (56 districts x 5 sectors x 192 months)
           data/raw/lmis_district_quarterly_2011_2026.csv     (64 quarters)
           data/raw/district_catalog.csv                      (district dimension table: LGD code, tier, population)
           data/raw/sector_nco_crosswalk.csv                  (sector -> NCO-2015 families)
Seed     : 42 (fully reproducible)

What changed from v1 (see docs/phases/PHASE_2_DATA_COLLECTION.md for the audit that motivated each item)
  * Employment is a SHARE OF DISTRICT WORKERS (tier-specific) x national sector index, not labour force x density
    multiplier with a 42% clip.  No clipping anywhere, so the COVID shocks and district disparity are not distorted.
  * Manufacturing excludes textiles/apparel (v1 double-counted NIC 13-14).
  * District LGD codes are the real ones (Maharashtra: state land-records LGD directory; Delhi/Tamil Nadu/West
    Bengal: LGD district export; all 56 cross-checked); Nandurbar's invalid '497A' is gone.  Census-2011 populations corrected for
    Chennai, Kanchipuram/Chengalpattu and Delhi (v1 double counted).
  * NCO codes are valid NCO-2015 families (v1's 8110 and 8261 do not exist).
  * Vacancies/seekers are driven by hiring-climate, unemployment and registry dynamics with persistent district
    effects (v1 used fixed ratios of employment).  e-Shram launch (Aug-2021) is modelled as a logistic ramp.
  * New supply-side columns: Training_Seats_Sanctioned and Trainees_Certified_Monthly (ITI/skilling capacity).
  * Demographic splits are smooth (persistent district profile + small Dirichlet noise), integer-conserving.

IMPORTANT: this is still SIMULATED data.  Level calibrations are approximate anchors (listed in the Phase 2 doc), not
observed district statistics.
"""
import os

import numpy as np
import pandas as pd

SEED = 42
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUTPUT_DIR = os.path.join(ROOT, "data", "raw")
N = 192                                     # 2011-01 .. 2026-12
MONTHS = pd.date_range("2011-01-01", periods=N, freq="MS")
T = np.arange(N)
YEAR, MONTH = MONTHS.year.to_numpy(), MONTHS.month.to_numpy()

# ==================================================================================================================
# 1. GEOGRAPHY  (LGD codes verified; see lgd_source)
# ==================================================================================================================
SRC_MH = "Maharashtra land-records LGD directory (mahavillages.mahabhumi.gov.in)"
SRC_EXP = "LGD district export (gist planemad/cd6b5237...); Kolkata also West Bengal State Health Society LGD list"
STATES = {"Maharashtra": "27", "Tamil Nadu": "33", "Delhi": "07", "West Bengal": "19"}
# (state, district, lgd, source, pop_2011, annual_growth, tier)
DISTRICTS = [
    ("Maharashtra", "Mumbai City", 482, SRC_MH, 3085411, 0.003, "metro_core"),
    ("Maharashtra", "Mumbai Suburban", 483, SRC_MH, 9356962, 0.009, "metro_core"),
    ("Maharashtra", "Thane", 497, SRC_MH, 8070032, 0.019, "industrial_hub"),
    ("Maharashtra", "Palghar", 665, SRC_MH, 2990116, 0.018, "industrial_msme"),
    ("Maharashtra", "Pune", 490, SRC_MH, 9429408, 0.017, "industrial_it_hub"),
    ("Maharashtra", "Nashik", 487, SRC_MH, 6107187, 0.015, "industrial_hub"),
    ("Maharashtra", "Chhatrapati Sambhajinagar", 469, SRC_MH, 3701282, 0.014, "industrial_hub"),
    ("Maharashtra", "Nagpur", 484, SRC_MH, 4653570, 0.012, "logistics_hub"),
    ("Maharashtra", "Kolhapur", 480, SRC_MH, 3876001, 0.010, "industrial_msme"),
    ("Maharashtra", "Solapur", 496, SRC_MH, 4317756, 0.011, "textile_cluster"),
    ("Maharashtra", "Raigad", 491, SRC_MH, 2634200, 0.014, "industrial_port"),
    ("Maharashtra", "Ahilyanagar", 466, SRC_MH, 4543159, 0.011, "semi_industrial"),
    ("Maharashtra", "Jalgaon", 478, SRC_MH, 4229917, 0.012, "semi_industrial"),
    ("Maharashtra", "Satara", 494, SRC_MH, 3003741, 0.009, "semi_industrial"),
    ("Maharashtra", "Sangli", 493, SRC_MH, 2822143, 0.009, "semi_industrial"),
    ("Maharashtra", "Amravati", 468, SRC_MH, 2888445, 0.010, "textile_cluster"),
    ("Maharashtra", "Nanded", 485, SRC_MH, 3361292, 0.012, "agrarian_developing"),
    ("Maharashtra", "Latur", 481, SRC_MH, 2455543, 0.011, "semi_industrial"),
    ("Maharashtra", "Dhule", 474, SRC_MH, 2050862, 0.011, "textile_cluster"),
    ("Maharashtra", "Chandrapur", 473, SRC_MH, 2204307, 0.008, "industrial_mining"),
    ("Maharashtra", "Buldhana", 472, SRC_MH, 2586258, 0.010, "agrarian_developing"),
    ("Maharashtra", "Yavatmal", 500, SRC_MH, 2772348, 0.010, "agrarian_developing"),
    ("Maharashtra", "Beed", 470, SRC_MH, 2585049, 0.011, "agrarian_migrant"),
    ("Maharashtra", "Parbhani", 489, SRC_MH, 1836086, 0.011, "agrarian_developing"),
    ("Maharashtra", "Jalna", 479, SRC_MH, 1959046, 0.012, "industrial_msme"),
    ("Maharashtra", "Akola", 467, SRC_MH, 1813906, 0.010, "semi_industrial"),
    ("Maharashtra", "Dharashiv", 488, SRC_MH, 1657576, 0.009, "agrarian_developing"),
    ("Maharashtra", "Nandurbar", 486, SRC_MH, 1648295, 0.013, "peripheral_tribal"),
    ("Maharashtra", "Ratnagiri", 492, SRC_MH, 1615069, 0.004, "peripheral_coastal"),
    ("Maharashtra", "Gondia", 476, SRC_MH, 1322507, 0.008, "peripheral_agrarian"),
    ("Maharashtra", "Wardha", 498, SRC_MH, 1300774, 0.006, "semi_industrial"),
    ("Maharashtra", "Bhandara", 471, SRC_MH, 1200334, 0.006, "peripheral_agrarian"),
    ("Maharashtra", "Washim", 499, SRC_MH, 1197160, 0.009, "peripheral_agrarian"),
    ("Maharashtra", "Hingoli", 477, SRC_MH, 1177345, 0.010, "peripheral_agrarian"),
    ("Maharashtra", "Gadchiroli", 475, SRC_MH, 1072942, 0.008, "peripheral_tribal"),
    ("Maharashtra", "Sindhudurg", 495, SRC_MH, 849651, -0.002, "peripheral_coastal"),
    ("Tamil Nadu", "Chennai", 568, SRC_EXP, 4646732, 0.011, "metro_core"),
    ("Tamil Nadu", "Tiruvallur", 589, SRC_EXP, 3728104, 0.023, "industrial_hub"),
    ("Tamil Nadu", "Kanchipuram", 574, SRC_EXP, 1442008, 0.021, "industrial_hub"),
    ("Tamil Nadu", "Chengalpattu", 730, SRC_EXP, 2556244, 0.024, "industrial_it_hub"),
    ("Delhi", "Central Delhi", 77, SRC_EXP, 582320, 0.007, "metro_core"),
    ("Delhi", "East Delhi", 78, SRC_EXP, 1709346, 0.011, "metro_residential"),
    ("Delhi", "New Delhi", 79, SRC_EXP, 142004, 0.005, "metro_administrative"),
    ("Delhi", "North Delhi", 80, SRC_EXP, 887978, 0.009, "industrial_msme"),
    ("Delhi", "North East Delhi", 81, SRC_EXP, 2241624, 0.015, "metro_residential"),
    ("Delhi", "North West Delhi", 82, SRC_EXP, 3656539, 0.016, "industrial_msme"),
    ("Delhi", "South Delhi", 83, SRC_EXP, 2731929, 0.013, "metro_core"),
    ("Delhi", "South East Delhi", 670, SRC_EXP, 1420000, 0.014, "industrial_hub"),
    ("Delhi", "South West Delhi", 84, SRC_EXP, 2292958, 0.015, "metro_residential"),
    ("Delhi", "West Delhi", 85, SRC_EXP, 2543243, 0.012, "industrial_hub"),
    ("Delhi", "Shahdara", 671, SRC_EXP, 1520000, 0.013, "industrial_msme"),
    ("West Bengal", "Kolkata", 315, SRC_EXP, 4496694, 0.004, "metro_core"),
    ("West Bengal", "North 24 Parganas", 303, SRC_EXP, 10009781, 0.012, "industrial_it_hub"),
    ("West Bengal", "South 24 Parganas", 304, SRC_EXP, 8161961, 0.014, "industrial_msme"),
    ("West Bengal", "Howrah", 313, SRC_EXP, 4850029, 0.009, "industrial_hub"),
    ("West Bengal", "Hooghly", 312, SRC_EXP, 5519145, 0.008, "industrial_hub"),
]
DELHI_CENSUS_TOTAL = 16787941   # Census 2011 was on 9 districts; the 11 post-2012 districts are re-apportioned to it

# state-level multipliers: labour-force participation, wage level, training capacity, covid stringency, female share
STATE_LFPR = {"Maharashtra": 1.02, "Tamil Nadu": 1.03, "Delhi": 0.93, "West Bengal": 0.97}
STATE_WAGE = {"Maharashtra": 1.00, "Tamil Nadu": 0.97, "Delhi": 1.05, "West Bengal": 0.88}
STATE_SEATS = {"Maharashtra": 1.00, "Tamil Nadu": 1.35, "Delhi": 0.80, "West Bengal": 0.70}
STATE_COVID = {"Maharashtra": 1.00, "Tamil Nadu": 0.95, "Delhi": 1.00, "West Bengal": 0.90}
STATE_FEMALE = {"Maharashtra": 0.0, "Tamil Nadu": 0.015, "Delhi": -0.015, "West Bengal": -0.01}
STATE_UR = {"Maharashtra": 0.0, "Tamil Nadu": -0.3, "Delhi": 0.5, "West Bengal": 0.8}

# ==================================================================================================================
# 2. SECTORS
# ==================================================================================================================
SECTORS = ["Manufacturing", "Construction", "IT-ITeS", "Healthcare", "Textiles and Apparel"]
SECTOR = {
    "Manufacturing": dict(nic="Division 10-12, 15-33", nco=7223, nsqf="3-6", base_wage=12500, ur_off=0.0,
                          female=0.165, trans=0.0012, age=[0.24, 0.64, 0.12], edu=[0.22, 0.32, 0.34, 0.12],
                          informal=0.35, vac_rate=0.022, covid_emp=-0.38, covid_vac=-0.35, rec_beta=0.28,
                          dist_sigma=0.18, seat_rate=3.2, demon=-0.025, gst=-0.020),
    "Construction": dict(nic="Division 41-43", nco=7111, nsqf="2-5", base_wage=10200, ur_off=1.2,
                         female=0.125, trans=0.0008, age=[0.28, 0.62, 0.10], edu=[0.58, 0.16, 0.23, 0.03],
                         informal=0.90, vac_rate=0.012, covid_emp=-0.52, covid_vac=-0.45, rec_beta=0.33,
                         dist_sigma=0.12, seat_rate=0.8, demon=-0.040, gst=-0.010),
    "IT-ITeS": dict(nic="Division 62-63", nco=2511, nsqf="5-8", base_wage=28500, ur_off=-0.5,
                    female=0.345, trans=0.0018, age=[0.32, 0.65, 0.03], edu=[0.005, 0.045, 0.11, 0.84],
                    informal=0.03, vac_rate=0.045, covid_emp=0.03, covid_vac=0.09, rec_beta=0.0,
                    dist_sigma=0.30, seat_rate=1.2, demon=0.0, gst=0.0),
    "Healthcare": dict(nic="Division 86", nco=2211, nsqf="4-8", base_wage=18200, ur_off=-0.7,
                       female=0.485, trans=0.0015, age=[0.22, 0.66, 0.12], edu=[0.03, 0.15, 0.46, 0.36],
                       informal=0.40, vac_rate=0.030, covid_emp=0.08, covid_vac=0.36, rec_beta=0.0,
                       dist_sigma=0.12, seat_rate=1.6, demon=0.0, gst=0.0),
    "Textiles and Apparel": dict(nic="Division 13-14", nco=8153, nsqf="2-5", base_wage=9800, ur_off=0.6,
                                 female=0.425, trans=0.0010, age=[0.29, 0.61, 0.10], edu=[0.48, 0.18, 0.31, 0.03],
                                 informal=0.65, vac_rate=0.018, covid_emp=-0.42, covid_vac=-0.40, rec_beta=0.25,
                                 dist_sigma=0.25, seat_rate=0.7, demon=-0.040, gst=-0.020),
}
# national employment index by sector (2011 = 1.00, calendar-year anchors; trend only, COVID dip added separately)
IDX = {
    "Manufacturing": [1.00, 1.03, 1.06, 1.09, 1.12, 1.15, 1.17, 1.20, 1.23, 1.26, 1.28, 1.31, 1.35, 1.40, 1.45, 1.49],
    "Construction": [1.00, 1.05, 1.10, 1.15, 1.19, 1.23, 1.28, 1.33, 1.38, 1.42, 1.45, 1.52, 1.60, 1.68, 1.75, 1.81],
    "IT-ITeS": [1.00, 1.12, 1.20, 1.28, 1.40, 1.48, 1.55, 1.64, 1.66, 1.74, 1.80, 2.00, 2.16, 2.17, 2.30, 2.40],
    "Healthcare": [1.00, 1.05, 1.10, 1.16, 1.22, 1.28, 1.34, 1.40, 1.47, 1.54, 1.60, 1.68, 1.77, 1.86, 1.95, 2.04],
    "Textiles and Apparel": [1.00, 1.02, 1.04, 1.06, 1.07, 1.08, 1.08, 1.09, 1.10, 1.10, 1.10, 1.13, 1.16, 1.18, 1.20, 1.22],
}
# employer hiring climate (multiplier on the vacancy rate)
HIRING = {s: [1.0] * 16 for s in SECTORS}
HIRING["IT-ITeS"] = [1.0] * 10 + [1.15, 1.35, 1.00, 0.80, 0.90, 0.98]
HIRING["Construction"] = [1.0] * 11 + [1.10, 1.12, 1.10, 1.05, 1.00]
# macro paths (calendar-year anchors 2011..2026)
LFPR_WAP = [0.535, 0.530, 0.525, 0.520, 0.515, 0.512, 0.510, 0.515, 0.520, 0.520, 0.530, 0.545, 0.560, 0.570, 0.575, 0.580]
URBAN_UR = [4.8, 4.7, 4.6, 4.7, 4.8, 5.0, 7.2, 7.7, 7.0, 6.3, 6.7, 6.3, 5.4, 5.1, 5.0, 4.9]
SEATS_PATH = [0.50, 0.58, 0.66, 0.74, 0.82, 0.90, 0.96, 1.00, 1.02, 1.03, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07]

# share of district workers (%) in 2011 by tier: Manufacturing(ex textiles), Construction, IT-ITeS, Healthcare, Textiles.
# IT-ITeS and Healthcare baselines are set so that 2025 sector totals across the 56 districts stay plausible against national
# totals (IT-BPM workforce ~5.8M nationally; these districts hold roughly 40%).
TIER_SHARE = {
    "metro_core":           [11.0, 9.0, 3.5, 3.3, 3.5],
    "industrial_it_hub":    [18.0, 8.0, 7.5, 2.7, 3.5],
    "industrial_hub":       [21.0, 8.0, 1.2, 2.4, 5.0],
    "industrial_msme":      [17.0, 8.0, 0.8, 2.1, 7.0],
    "textile_cluster":      [11.0, 7.0, 0.5, 1.8, 14.0],
    "industrial_port":      [18.0, 8.0, 0.8, 2.1, 3.0],
    "logistics_hub":        [12.0, 9.0, 1.4, 3.0, 2.5],
    "metro_residential":    [8.0, 8.0, 1.6, 3.0, 5.5],
    "metro_administrative": [3.0, 5.0, 3.5, 3.6, 1.0],
    "industrial_mining":    [11.0, 9.0, 0.5, 1.8, 1.0],
    "semi_industrial":      [9.0, 7.0, 0.6, 2.1, 3.0],
    "agrarian_developing":  [4.0, 6.0, 0.35, 1.6, 2.5],
    "agrarian_migrant":     [3.0, 6.0, 0.3, 1.3, 2.0],
    "peripheral_tribal":    [2.5, 5.0, 0.2, 1.1, 1.2],
    "peripheral_agrarian":  [3.0, 5.0, 0.25, 1.2, 1.5],
    "peripheral_coastal":   [4.0, 6.5, 0.35, 1.6, 1.5],
}
# known IT-ITeS concentrations that the tier averages miss (Hinjewadi/Pune, OMR/Chennai; Kolkata IT sits mostly in
# Bidhannagar/Rajarhat so North 24 Parganas is below its tier average).  Multipliers on the 2011 baseline share.
DISTRICT_SECTOR_ADJ = {("Pune", "IT-ITeS"): 1.25, ("Chennai", "IT-ITeS"): 1.50, ("North 24 Parganas", "IT-ITeS"): 0.45}

# sector -> NCO-2015 families (all verified present in data/raw/NCO-Codes.xlsx; the first is the anchor code)
CROSSWALK = {
    "Manufacturing": [(7223, "Metal Working Machine Tool Setters and Operators"), (8212, "Electrical and Electronic Equipment Assemblers"),
                      (8131, "Chemical Products Plant and Machine Operators"), (7233, "Agricultural and Industrial Machinery Mechanics and Repairers"),
                      (7212, "Welders and Flame Cutters")],
    "Construction": [(7111, "House Builders"), (7112, "Bricklayers and Related Workers"), (7115, "Carpenters and Joiners"),
                     (7126, "Plumbers and Pipe Fitters"), (9313, "Building Construction Labourers")],
    "IT-ITeS": [(2511, "System Analysts"), (2512, "Software Developers"), (2513, "Web and Multimedia Developers"),
                (2514, "Applications Programmers"), (3512, "Information and Communication Technology User Support Technicians")],
    "Healthcare": [(2211, "Generalist Medical Practitioners"), (2212, "Specialist Medical Practitioners"), (2221, "Nursing Professionals"),
                   (3221, "Nursing Associate Professionals"), (3212, "Medical and Pathology Laboratory Technicians")],
    "Textiles and Apparel": [(8153, "Sewing Machine Operators"), (8152, "Weaving and Knitting Machine Operators"),
                             (8151, "Fibre Preparing, Spinning and Winding Machine Operators"),
                             (7531, "Tailors, Dressmakers, Furriers and Hatters"), (7533, "Sewing, Embroiderers and Related Workers")],
}

# COVID-19 monthly intensity (1.0 = April/May 2020 national lockdown); the 2021 Delta wave hit employment far less
COVID = {(2020, 3): .35, (2020, 4): 1.0, (2020, 5): 1.0, (2020, 6): .70, (2020, 7): .55, (2020, 8): .45, (2020, 9): .35,
         (2020, 10): .25, (2020, 11): .20, (2020, 12): .15, (2021, 1): .10, (2021, 2): .08, (2021, 3): .12, (2021, 4): .25,
         (2021, 5): .35, (2021, 6): .20, (2021, 7): .08, (2021, 8): .05, (2021, 9): .04, (2021, 10): .03, (2022, 1): .08,
         (2022, 2): .05}
COVID_I = np.array([COVID.get((y, m), 0.0) for y, m in zip(YEAR, MONTH)])
IDX_RECOVERY_START = 126                     # 2021-07: post-wave recovery clock starts
IDX_ESHRAM_LAUNCH = 127                      # 2021-08


# ==================================================================================================================
# 3. HELPERS
# ==================================================================================================================
def path(anchors):
    """Monthly series from calendar-year anchors placed at mid-year (flat beyond the ends)."""
    return np.interp((T + 0.5) / 12 - 0.5, np.arange(len(anchors)), anchors)


def ar1(rng, n, phi, sigma_innov):
    """(n x N) stationary AR(1) paths."""
    x = np.zeros((n, N))
    x[:, 0] = rng.normal(0, sigma_innov / np.sqrt(1 - phi ** 2), n)
    eps = rng.normal(0, sigma_innov, (n, N))
    for i in range(1, N):
        x[:, i] = phi * x[:, i - 1] + eps[:, i]
    return x


def seasonal(sector, state):
    s = np.zeros(12)
    m = np.arange(1, 13)
    if sector == "Construction":
        monsoon = {"Maharashtra": (6, 9, .10), "West Bengal": (6, 9, .10), "Delhi": (7, 9, .07), "Tamil Nadu": (10, 12, .05)}[state]
        s += np.where((m >= monsoon[0]) & (m <= monsoon[1]), -monsoon[2], 0.03)
    elif sector == "Textiles and Apparel":
        s += np.where((m >= 9) & (m <= 11), 0.09 if state == "West Bengal" else 0.07, 0.0)
        s += np.where((m >= 4) & (m <= 5), -0.03, 0.0)
    elif sector == "Manufacturing":
        s += np.where((m >= 10) | (m <= 3), 0.02, 0.0) + np.where((m >= 6) & (m <= 8), -0.015, 0.0)
    elif sector == "Healthcare":
        s += np.where((m >= 7) & (m <= 10), 0.015, 0.0)
    else:
        s += np.where((m >= 7) & (m <= 9), 0.012, 0.0) + np.where(m <= 3, -0.005, 0.0)
    f = 1.0 + s
    return (f / f.mean())[MONTH - 1]


def largest_remainder(total, props):
    """Integer counts per category that sum exactly to `total` (rows)."""
    raw = props * total[:, None]
    base = np.floor(raw).astype(np.int64)
    rem = (total - base.sum(axis=1)).astype(int)
    order = np.argsort(-(raw - base), axis=1)
    rank = np.argsort(order, axis=1)
    return base + (rank < rem[:, None])


def dirichlet_rows(rng, p, conc):
    g = rng.gamma(np.maximum(p * conc, 1e-3))
    return g / g.sum(axis=1, keepdims=True)


# ==================================================================================================================
# 4. GENERATION
# ==================================================================================================================
def build_catalog():
    cat = pd.DataFrame(DISTRICTS, columns=["State_Name", "District_Name", "District_LGD_Code", "LGD_Code_Source",
                                           "Pop_2011", "Pop_Growth_Annual", "Econ_Tier"])
    cat["State_LGD_Code"] = cat["State_Name"].map(STATES)
    d = cat["State_Name"] == "Delhi"
    cat.loc[d, "Pop_2011"] = (cat.loc[d, "Pop_2011"] * DELHI_CENSUS_TOTAL / cat.loc[d, "Pop_2011"].sum()).round().astype(int)
    assert cat["District_LGD_Code"].is_unique and len(cat) == 56
    return cat


def generate():
    rng = np.random.default_rng(SEED)
    cat = build_catalog()
    nd = len(cat)
    yrs = T / 12.0
    pop = cat["Pop_2011"].to_numpy()[:, None] * (1 + cat["Pop_Growth_Annual"].to_numpy()[:, None]) ** yrs
    wap = pop * 0.665
    st = cat["State_Name"].to_numpy()
    lfpr = path(LFPR_WAP)[None, :] * np.array([STATE_LFPR[s] for s in st])[:, None]
    nat_ur = path(URBAN_UR)
    workers = wap * lfpr * (1 - nat_ur[None, :] / 100)                         # employed persons, all sectors
    idx_total = 1.015 ** yrs
    stringency = np.array([STATE_COVID[s] for s in st])[:, None]
    wage_idx = 1.055 ** yrs
    tier_prem = np.array([1.25 if t in ("metro_core", "metro_administrative") else 1.15 if "hub" in t else 1.0
                          for t in cat["Econ_Tier"]])[:, None]
    fy = np.where(MONTH >= 4, YEAR, YEAR - 1)                                   # financial year (Apr-Mar)
    fy_idx = fy - 2011
    cert_w = np.array([.06, .04, .05, .04, .05, .10, .26, .14, .07, .07, .06, .06])[MONTH - 1]
    util = np.where(fy == 2020, 0.55, np.where(fy == 2021, 0.85, 0.72))
    seat_mult = np.array(SEATS_PATH)[np.clip(fy_idx, 0, 15)]

    out = {}
    emp_density_ref = {}
    for sector in SECTORS:
        sp = SECTOR[sector]
        k = SECTORS.index(sector)
        share0 = np.array([TIER_SHARE[t][k] for t in cat["Econ_Tier"]])[:, None] / 100.0
        share0 = share0 * np.array([DISTRICT_SECTOR_ADJ.get((d, sector), 1.0) for d in cat["District_Name"]])[:, None]
        dist_eff = np.exp(rng.normal(0, sp["dist_sigma"], (nd, 1)))
        dist_eff /= dist_eff.mean()
        seas = np.vstack([seasonal(sector, s) for s in st])
        # ---- employment ------------------------------------------------------------------------------------------
        trend = path(IDX[sector])[None, :] / idx_total[None, :]
        shock = 1 + sp["covid_emp"] * COVID_I[None, :] * stringency
        tau = np.maximum(T - IDX_RECOVERY_START, 0)
        scar = np.zeros(N)
        if sp["covid_emp"] < 0:     # residual scar closing as beta * ln(1 + months since 2021-07)
            scar = np.where(T >= IDX_RECOVERY_START,
                            sp["covid_emp"] * 0.20 * np.clip(1 - sp["rec_beta"] * np.log1p(tau), 0, 1), 0.0)
        policy = 1 + sp["demon"] * ((YEAR == 2016) & (MONTH >= 11) | (YEAR == 2017) & (MONTH == 1)) \
                   + sp["gst"] * ((YEAR == 2017) & (MONTH >= 7) & (MONTH <= 10))
        noise = np.exp(ar1(rng, nd, 0.90, 0.006) + rng.normal(0, 0.008, (nd, N)))
        emp = workers * share0 * trend * dist_eff * seas * (shock + scar[None, :] * stringency) * policy[None, :] * noise
        emp = np.maximum(np.rint(emp), 1).astype(np.int64)

        # ---- unemployment rate -----------------------------------------------------------------------------------
        spike = (4.5 if sp["covid_emp"] < 0 else -0.8) * COVID_I[None, :]
        ur = (nat_ur[None, :] + sp["ur_off"] + np.array([STATE_UR[s] for s in st])[:, None] + spike
              + ar1(rng, nd, 0.90, 0.12) + rng.normal(0, 0.15, (nd, N)))
        ur = np.round(np.clip(ur, 3.5, 12.0), 2)

        # ---- vacancies (demand) ----------------------------------------------------------------------------------
        idx_path = path(IDX[sector])
        yoy = np.r_[np.full(12, idx_path[12] / idx_path[0] - 1), idx_path[12:] / idx_path[:-12] - 1]
        gbar = yoy[:120].mean()
        tight = np.clip(1 + 2.0 * (yoy - gbar), 0.5, 1.8)[None, :]
        covid_v = np.clip(1 + sp["covid_vac"] * COVID_I[None, :] * stringency, 0.1, None)
        vac_dist = np.exp(rng.normal(0, 0.20, (nd, 1)))
        vac = emp * sp["vac_rate"] * path(HIRING[sector])[None, :] * tight * covid_v * vac_dist \
            * np.exp(ar1(rng, nd, 0.93, 0.035) + rng.normal(0, 0.04, (nd, N)))
        vac = np.maximum(np.rint(vac), 1).astype(np.int64)

        # ---- training capacity (supply side) --------------------------------------------------------------------
        lag = np.clip(T - 36, 0, None)
        dens = emp[:, lag] / wap[:, lag]
        alloc = 0.5 * dens / dens.mean(axis=0, keepdims=True) + 0.5
        alloc_dist = np.exp(rng.normal(0, 0.25, (nd, 1)))
        seats_year = (wap / 1000.0) * sp["seat_rate"] * np.array([STATE_SEATS[s] for s in st])[:, None] \
            * seat_mult[None, :] * alloc * alloc_dist
        # seat capacity is a stock fixed for the financial year: take the April value of each FY
        seats = seats_year[:, np.clip((fy - 2011) * 12 + 3, 0, N - 1)]
        seats = np.maximum(np.rint(seats), 1).astype(np.int64)
        cert = seats * util[None, :] * 0.82 * cert_w[None, :] * np.exp(rng.normal(0, 0.06, (nd, N)))
        cert = np.rint(cert).astype(np.int64)
        # trailing-12-month outturn; months before 2011-01 are filled with a copy of 2011 so there is no start-up ramp
        cert_ext = np.hstack([cert[:, :12], cert])
        cert_12m = pd.DataFrame(cert_ext.T).rolling(12).sum().to_numpy().T[:, 12:]

        # ---- registered seekers (supply proxy) -------------------------------------------------------------------
        m = T - IDX_ESHRAM_LAUNCH
        reg = 0.02 + 0.33 / (1 + np.exp(-(m - 8) / 6.0))                        # e-Shram ramp-up from Aug-2021
        unemployed = emp * ur / (100 - ur)
        seek = (0.6 * unemployed + sp["informal"] * emp * reg[None, :] + 0.4 * cert_12m) * np.exp(rng.normal(0, 0.15, (nd, 1))) \
            * np.exp(ar1(rng, nd, 0.95, 0.02) + rng.normal(0, 0.035, (nd, N)))
        seek = np.maximum(np.rint(seek), 1).astype(np.int64)

        # ---- wage -----------------------------------------------------------------------------------------------
        wage = sp["base_wage"] * wage_idx[None, :] * tier_prem * np.array([STATE_WAGE[s] for s in st])[:, None] \
            * np.exp(rng.normal(0, 0.012, (nd, N)))
        wage = np.rint(wage).astype(np.int64)

        # ---- demographics (integer-conserving) -------------------------------------------------------------------
        tot = emp.ravel()
        f_share = np.clip(sp["female"] + 0.0015 * yrs[None, :] + np.array([STATE_FEMALE[s] for s in st])[:, None]
                          + rng.normal(0, 0.004, (nd, 1)) + rng.normal(0, 0.006, (nd, N)), 0.05, 0.60).ravel()
        tr_share = np.full(tot.shape, sp["trans"])
        gender_p = np.column_stack([1 - f_share - tr_share, f_share, tr_share])
        gender = largest_remainder(tot, gender_p)

        def smooth_group(weights, tilt=None, floor_last=None):
            base = np.tile(np.array(weights, float), (nd, 1))
            if tilt is not None:
                base = base * tilt
            base /= base.sum(axis=1, keepdims=True)
            persistent = dirichlet_rows(rng, base, 250.0)                     # district profile (fixed over time)
            rows = np.repeat(persistent, N, axis=0)
            p = dirichlet_rows(rng, rows, 1500.0)                              # small monthly sampling noise
            if floor_last is not None:                                         # hard floor on the last category
                last = np.maximum(p[:, -1], floor_last)
                p = np.column_stack([p[:, :-1] * ((1 - last) / p[:, :-1].sum(axis=1))[:, None], last])
            return p

        metro = np.array([1.0 if t.startswith("metro") or "it_hub" in t else 0.0 for t in cat["Econ_Tier"]])[:, None]
        periph = np.array([1.0 if t.startswith(("peripheral", "agrarian")) else 0.0 for t in cat["Econ_Tier"]])[:, None]
        edu_tilt = np.hstack([1 - 0.10 * metro + 0.10 * periph, np.ones((nd, 2)), 1 + 0.10 * metro - 0.10 * periph])
        age = largest_remainder(tot, smooth_group(sp["age"]))
        edu = largest_remainder(tot, smooth_group(sp["edu"], edu_tilt, floor_last=0.805 if sector == "IT-ITeS" else None))

        out[sector] = dict(emp=emp, ur=ur, vac=vac, seats=seats, cert=cert, seek=seek, wage=wage,
                           gender=gender, age=age, edu=edu)
    return cat, pop.astype(np.int64), out


def to_long(cat, pop, out):
    nd = len(cat)
    frames = []
    for sector in SECTORS:
        sp, o = SECTOR[sector], out[sector]
        n = nd * N
        tot = o["emp"].ravel()
        pct = lambda c: np.round(c / tot * 100.0, 2)
        df = pd.DataFrame({
            "State_Name": np.repeat(cat["State_Name"].to_numpy(), N),
            "State_LGD_Code": np.repeat(cat["State_LGD_Code"].to_numpy(), N),
            "District_Name": np.repeat(cat["District_Name"].to_numpy(), N),
            "District_LGD_Code": np.repeat(cat["District_LGD_Code"].astype(str).to_numpy(), N),
            "District_Total_Population_Est": pop.ravel(),
            "Timestamp": np.tile(MONTHS.strftime("%Y-%m"), nd),
            "Year": np.tile(YEAR, nd), "Month": np.tile(MONTH, nd),
            "Sector_Name": sector, "NIC_Code": sp["nic"], "NCO_Code": sp["nco"], "NSQF_Level": sp["nsqf"],
        })
        df["Timestamp_Month"] = df["Timestamp"]
        df["Timestamp_Quarter"] = df["Year"].astype(str) + "-Q" + ((df["Month"] - 1) // 3 + 1).astype(str)
        g, a, e = o["gender"], o["age"], o["edu"]
        cols = {
            "Male_Employed_Count": g[:, 0], "Female_Employed_Count": g[:, 1], "Transgender_Employed_Count": g[:, 2],
            "Male_Share_Pct": pct(g[:, 0]), "Female_Share_Pct": pct(g[:, 1]), "Transgender_Share_Pct": pct(g[:, 2]),
            "Age_15_24_Count": a[:, 0], "Age_25_54_Count": a[:, 1], "Age_55_Plus_Count": a[:, 2],
            "Age_15_24_Pct": pct(a[:, 0]), "Age_25_54_Pct": pct(a[:, 1]), "Age_55_Plus_Pct": pct(a[:, 2]),
            "Edu_Below_Primary_Count": e[:, 0], "Edu_Secondary_HigherSecondary_Count": e[:, 1],
            "Qualification_Vocational_ITI_Certified_Count": e[:, 2], "Edu_Graduate_and_Above_Count": e[:, 3],
            "Edu_Below_Primary_Pct": pct(e[:, 0]), "Edu_Secondary_HigherSecondary_Pct": pct(e[:, 1]),
            "Qualification_Vocational_ITI_Certified_Pct": pct(e[:, 2]), "Edu_Graduate_and_Above_Pct": pct(e[:, 3]),
            "Active_Job_Vacancies": o["vac"].ravel(), "Total_Employed_Workers": tot,
            "eShram_Registered_Seekers": o["seek"].ravel(), "Avg_Monthly_Wage_INR": o["wage"].ravel(),
            "Unemployment_Rate_Pct": o["ur"].ravel(),
            "Training_Seats_Sanctioned": o["seats"].ravel(), "Trainees_Certified_Monthly": o["cert"].ravel(),
        }
        frames.append(pd.concat([df, pd.DataFrame(cols)], axis=1))
    long = pd.concat(frames, ignore_index=True)
    long["_d"] = long["District_Name"].map({d: i for i, d in enumerate(cat["District_Name"])})
    long["_s"] = long["Sector_Name"].map({s: i for i, s in enumerate(SECTORS)})
    long = long.sort_values(["Timestamp", "_d", "_s"]).drop(columns=["_d", "_s"]).reset_index(drop=True)
    order = ["State_Name", "State_LGD_Code", "District_Name", "District_LGD_Code", "District_Total_Population_Est", "Timestamp",
             "Timestamp_Month", "Timestamp_Quarter", "Year", "Month", "Sector_Name", "NIC_Code", "NCO_Code", "NSQF_Level"]
    return long[order + [c for c in long.columns if c not in order]]


def to_quarterly(monthly):
    keys = ["State_Name", "State_LGD_Code", "District_Name", "District_LGD_Code", "Timestamp_Quarter", "Year", "Sector_Name",
            "NIC_Code", "NCO_Code", "NSQF_Level"]
    mean_cols = [c for c in monthly.columns if c.endswith("_Count") or c in (
        "District_Total_Population_Est", "Active_Job_Vacancies", "Total_Employed_Workers", "eShram_Registered_Seekers",
        "Avg_Monthly_Wage_INR", "Training_Seats_Sanctioned")]
    g = monthly.groupby(keys, sort=False)
    q = g[mean_cols].mean().astype(np.int64)
    q["Unemployment_Rate_Pct"] = g["Unemployment_Rate_Pct"].mean().round(2)
    q["Trainees_Certified_Quarterly"] = g["Trainees_Certified_Monthly"].sum()
    q = q.reset_index()
    emp = q["Total_Employed_Workers"]
    # keep the exact-sum identities after truncating the monthly means
    q["Female_Employed_Count"] = emp - q["Male_Employed_Count"] - q["Transgender_Employed_Count"]
    q["Age_55_Plus_Count"] = emp - q["Age_15_24_Count"] - q["Age_25_54_Count"]
    q["Edu_Graduate_and_Above_Count"] = emp - q["Edu_Below_Primary_Count"] - q["Edu_Secondary_HigherSecondary_Count"] \
        - q["Qualification_Vocational_ITI_Certified_Count"]
    pct_of = {"Male_Employed_Count": "Male_Share_Pct", "Female_Employed_Count": "Female_Share_Pct",
              "Transgender_Employed_Count": "Transgender_Share_Pct", "Age_15_24_Count": "Age_15_24_Pct",
              "Age_25_54_Count": "Age_25_54_Pct", "Age_55_Plus_Count": "Age_55_Plus_Pct",
              "Edu_Below_Primary_Count": "Edu_Below_Primary_Pct",
              "Edu_Secondary_HigherSecondary_Count": "Edu_Secondary_HigherSecondary_Pct",
              "Qualification_Vocational_ITI_Certified_Count": "Qualification_Vocational_ITI_Certified_Pct",
              "Edu_Graduate_and_Above_Count": "Edu_Graduate_and_Above_Pct"}
    for c, pc in pct_of.items():
        q[pc] = np.round(q[c] / emp * 100.0, 2)
    q["Timestamp"] = q["Timestamp_Quarter"]
    q["Quarter"] = q["Timestamp_Quarter"].str[-1].astype(int)
    cols = ["State_Name", "State_LGD_Code", "District_Name", "District_LGD_Code", "District_Total_Population_Est", "Timestamp",
            "Timestamp_Quarter", "Year", "Quarter", "Sector_Name", "NIC_Code", "NCO_Code", "NSQF_Level"]
    cols += [c for c in monthly.columns if c in q.columns and c not in cols] + ["Trainees_Certified_Quarterly"]
    return q.sort_values(["Year", "Quarter", "State_Name", "District_Name", "Sector_Name"])[cols].reset_index(drop=True)


def self_check(m, cat):
    """Quick generation-time sanity report (the formal audit is src/data_collection/validate_raw_data.py)."""
    print("\n--- generation-time sanity report ---")
    nat = m.groupby(["Sector_Name", "Timestamp"])["Total_Employed_Workers"].sum().unstack(0)
    print("National employment, Apr-2020 vs Feb-2020 (%):")
    print(((nat.loc["2020-04"] / nat.loc["2020-02"] - 1) * 100).round(1).to_string())
    vac = m.groupby(["Sector_Name", "Timestamp"])["Active_Job_Vacancies"].sum().unstack(0)
    print("National vacancies, Apr-2020 vs Feb-2020 (%):")
    print(((vac.loc["2020-04"] / vac.loc["2020-02"] - 1) * 100).round(1).to_string())
    last = m[m.Timestamp.between("2025-01", "2025-12")]
    dens = (last.assign(d=last.Total_Employed_Workers / last.District_Total_Population_Est)
            .groupby(["Sector_Name", "District_Name"])["d"].mean().unstack(0))
    hubs = ["Pune", "Mumbai Suburban", "Chennai", "South Delhi", "North 24 Parganas"]
    peri = ["Gadchiroli", "Nandurbar", "Washim"]
    print("Hub / peripheral per-capita employment density ratio (2025):")
    print((dens.loc[hubs].mean() / dens.loc[peri].mean()).round(1).to_string())
    print("Female share (%) by sector:", m.groupby("Sector_Name")["Female_Share_Pct"].mean().round(1).to_dict())
    print("IT-ITeS graduate share (%):", round(m[m.Sector_Name == "IT-ITeS"]["Edu_Graduate_and_Above_Pct"].mean(), 2))
    print("Unemployment range:", m["Unemployment_Rate_Pct"].min(), "-", m["Unemployment_Rate_Pct"].max(),
          "| share of rows at the 3.5/12.0 bounds:",
          round(float(m["Unemployment_Rate_Pct"].isin([3.5, 12.0]).mean()), 3))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(DISTRICTS)} districts x {len(SECTORS)} sectors x {N} months (seed {SEED})...")
    cat, pop, out = generate()
    monthly = to_long(cat, pop, out)
    quarterly = to_quarterly(monthly)
    monthly.to_csv(os.path.join(OUTPUT_DIR, "lmis_district_monthly_2011_2026.csv"), index=False)
    quarterly.to_csv(os.path.join(OUTPUT_DIR, "lmis_district_quarterly_2011_2026.csv"), index=False)
    cat.to_csv(os.path.join(OUTPUT_DIR, "district_catalog.csv"), index=False)
    cw = pd.DataFrame([(s, SECTOR[s]["nic"], i == 0, code, title) for s, fams in CROSSWALK.items()
                       for i, (code, title) in enumerate(fams)],
                      columns=["Sector_Name", "NIC_Code", "Is_Anchor_Code", "NCO_2015_Family", "NCO_2015_Title"])
    cw.to_csv(os.path.join(OUTPUT_DIR, "sector_nco_crosswalk.csv"), index=False)
    print(f"monthly {monthly.shape}, quarterly {quarterly.shape}")
    self_check(monthly, cat)


if __name__ == "__main__":
    main()
