#!/usr/bin/env python3
"""
v4 phase 2 - the simulated labour-market panel: 317 districts x 5 sectors x 5 trades, monthly, 2000-01 to 2025-12.

Output (all rebuilt from the seed; the large panel is git-ignored, the small tables and the manifest are tracked)
    data/v4/raw/trade_monthly_2000_2025.parquet     7,925 series x 312 months
    data/v4/raw/sector_monthly_2000_2025.parquet    1,585 district-sector series; every trade count adds up to these exactly
    data/v4/dim_series.csv                          one row per series: district, state, tier, sector, trade (NCO-2015 code and title)
    data/v4/DATA_MANIFEST.json                      row counts, checksums and headline totals

How the data is made (a simulation, not observed statistics)
  1. District-sector level: the v3 model, extended to 2000-2025 and 10 states.  Employment = district workers x tier-specific sector share x state/sector
     weight x national sector index x district effect x seasonality x COVID-19, demonetisation/GST and 2008-09 slowdown effects.  Vacancies follow hiring
     climate and employment; registered seekers follow unemployment, the informal workforce and e-Shram (August 2021); training seats are an annual stock.
  2. Trade level: the five trades of a sector split each district-sector count with time-varying shares (own drift, seasonality, COVID sensitivity, persistent
     district and state tilts, random walks).  Integer counts add up exactly to the sector counts; each trade has at least 1 worker, opening and seeker.
  3. Source channels: demand is also "measured" by four imperfect sources (job-portal postings, a quarterly hiring survey, NCS vacancies, a labour-force
     survey estimate), each with its own coverage, lead/lag, noise and start date.  The Demand Index of phase 6 combines them.
Run: python src/v4/generate.py        (a few minutes; seed 42; the same seed gives the same data)
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import trades as TR  # noqa: E402

N = C.N_MONTHS
MONTHS = pd.date_range("2000-01-01", periods=N, freq="MS")
T = np.arange(N)
YEAR, MONTH = MONTHS.year.to_numpy(), MONTHS.month.to_numpy()
I2011 = 132                                                  # column of 2011-01 (the base of the national indices and of the district populations)
YRS = (T - I2011) / 12.0
FY = np.where(MONTH >= 4, YEAR, YEAR - 1)                    # financial year (April to March)
SECTORS = list(C.SECTORS)
OUT_RAW = C.DATA / "raw"

# ======================================================================================================================
# 1. ASSUMPTIONS (national and state level).  Calendar-year anchors 2000..2025 are interpolated to months.
# ======================================================================================================================
STATE_LFPR = {"Maharashtra": 1.02, "Tamil Nadu": 1.03, "Delhi": 0.93, "West Bengal": 0.97, "Gujarat": 1.01, "Uttar Pradesh": 0.93, "Karnataka": 1.02,
              "Telangana": 1.03, "Kerala": 0.95, "Punjab": 0.98}
STATE_WAGE = {"Maharashtra": 1.00, "Tamil Nadu": 0.97, "Delhi": 1.05, "West Bengal": 0.88, "Gujarat": 1.02, "Uttar Pradesh": 0.82, "Karnataka": 1.06,
              "Telangana": 1.03, "Kerala": 1.08, "Punjab": 0.98}
STATE_SEATS = {"Maharashtra": 1.00, "Tamil Nadu": 1.35, "Delhi": 0.80, "West Bengal": 0.70, "Gujarat": 1.15, "Uttar Pradesh": 0.65, "Karnataka": 1.05,
               "Telangana": 0.95, "Kerala": 1.10, "Punjab": 0.90}
STATE_COVID = {"Maharashtra": 1.00, "Tamil Nadu": 0.95, "Delhi": 1.00, "West Bengal": 0.90, "Gujarat": 0.95, "Uttar Pradesh": 0.90, "Karnataka": 0.98,
               "Telangana": 0.95, "Kerala": 0.90, "Punjab": 0.95}
STATE_FEMALE = {"Maharashtra": 0.0, "Tamil Nadu": 0.015, "Delhi": -0.015, "West Bengal": -0.01, "Gujarat": -0.02, "Uttar Pradesh": -0.03,
                "Karnataka": 0.01, "Telangana": 0.01, "Kerala": 0.03, "Punjab": -0.02}
STATE_UR = {"Maharashtra": 0.0, "Tamil Nadu": -0.3, "Delhi": 0.5, "West Bengal": 0.8, "Gujarat": -0.4, "Uttar Pradesh": 0.6, "Karnataka": -0.2,
            "Telangana": 0.0, "Kerala": 1.0, "Punjab": 0.6}
MONSOON = {"Maharashtra": (6, 9, .10), "West Bengal": (6, 9, .10), "Delhi": (7, 9, .07), "Tamil Nadu": (10, 12, .05), "Gujarat": (6, 9, .10),
           "Uttar Pradesh": (6, 9, .10), "Karnataka": (6, 9, .08), "Telangana": (6, 9, .08), "Kerala": (6, 9, .12), "Punjab": (7, 9, .07)}

SECTOR = {
    "Manufacturing": dict(base_wage=12500, ur_off=0.0, female=0.165, grad=0.12, youth=0.24, informal=0.35, vac_rate=0.022, covid_emp=-0.38, covid_vac=-0.35,
                          rec_beta=0.28, dist_sigma=0.18, seat_rate=3.2, demon=-0.025, gst=-0.020, gfc_emp=-0.04, gfc_vac=-0.30, cagr0010=0.033),
    "Construction": dict(base_wage=10200, ur_off=1.2, female=0.125, grad=0.03, youth=0.28, informal=0.90, vac_rate=0.012, covid_emp=-0.52, covid_vac=-0.45,
                         rec_beta=0.33, dist_sigma=0.12, seat_rate=0.8, demon=-0.040, gst=-0.010, gfc_emp=-0.03, gfc_vac=-0.20, cagr0010=0.045),
    "IT-ITeS": dict(base_wage=28500, ur_off=-0.5, female=0.345, grad=0.84, youth=0.32, informal=0.03, vac_rate=0.045, covid_emp=0.03, covid_vac=0.09,
                    rec_beta=0.0, dist_sigma=0.30, seat_rate=1.2, demon=0.0, gst=0.0, gfc_emp=-0.03, gfc_vac=-0.35, cagr0010=0.130),
    "Healthcare": dict(base_wage=18200, ur_off=-0.7, female=0.485, grad=0.36, youth=0.22, informal=0.40, vac_rate=0.030, covid_emp=0.08, covid_vac=0.36,
                       rec_beta=0.0, dist_sigma=0.12, seat_rate=1.6, demon=0.0, gst=0.0, gfc_emp=0.0, gfc_vac=-0.05, cagr0010=0.040),
    "Textiles and Apparel": dict(base_wage=9800, ur_off=0.6, female=0.425, grad=0.03, youth=0.29, informal=0.65, vac_rate=0.018, covid_emp=-0.42, covid_vac=-0.40,
                                 rec_beta=0.25, dist_sigma=0.25, seat_rate=0.7, demon=-0.040, gst=-0.020, gfc_emp=-0.05, gfc_vac=-0.30, cagr0010=0.008),
}
# national employment index by sector, 2011 = 1.00: 2011-2025 anchors as in v3; 2000-2010 is a back-cast at the sector's 2000-2011 growth rate
_IDX_V3 = {
    "Manufacturing": [1.00, 1.03, 1.06, 1.09, 1.12, 1.15, 1.17, 1.20, 1.23, 1.26, 1.28, 1.31, 1.35, 1.40, 1.45],
    "Construction": [1.00, 1.05, 1.10, 1.15, 1.19, 1.23, 1.28, 1.33, 1.38, 1.42, 1.45, 1.52, 1.60, 1.68, 1.75],
    "IT-ITeS": [1.00, 1.12, 1.20, 1.28, 1.40, 1.48, 1.55, 1.64, 1.66, 1.74, 1.80, 2.00, 2.16, 2.17, 2.30],
    "Healthcare": [1.00, 1.05, 1.10, 1.16, 1.22, 1.28, 1.34, 1.40, 1.47, 1.54, 1.60, 1.68, 1.77, 1.86, 1.95],
    "Textiles and Apparel": [1.00, 1.02, 1.04, 1.06, 1.07, 1.08, 1.08, 1.09, 1.10, 1.10, 1.10, 1.13, 1.16, 1.18, 1.20],
}
IDX = {s: [1.0 / (1 + SECTOR[s]["cagr0010"]) ** (2011 - y) for y in range(2000, 2011)] + _IDX_V3[s] for s in SECTORS}
HIRING = {s: [1.0] * 26 for s in SECTORS}                                                                  # employer hiring climate (multiplier on the vacancy rate)
HIRING["IT-ITeS"] = [1.15, .85, .80, .90, 1.00, 1.05, 1.10, 1.10, .95, .95, 1.00] + [1.0] * 10 + [1.15, 1.35, 1.00, .80, .90]
HIRING["Construction"] = [1.0] * 22 + [1.10, 1.12, 1.10, 1.05]
LFPR_WAP = [.520, .520, .525, .525, .530, .530, .530, .535, .535, .535, .535, .535, .530, .525, .520, .515, .512, .510, .515, .520, .520, .530, .545, .560, .570, .575]
URBAN_UR = [5.5, 5.6, 5.7, 5.6, 5.4, 5.2, 5.0, 4.8, 4.9, 5.1, 4.9, 4.8, 4.7, 4.6, 4.7, 4.8, 5.0, 7.2, 7.7, 7.0, 6.3, 6.7, 6.3, 5.4, 5.1, 5.0]
SEATS_PATH = [.18, .20, .22, .24, .26, .29, .32, .36, .40, .44, .47, .50, .58, .66, .74, .82, .90, .96, 1.00, 1.02, 1.03, 1.02, 1.03, 1.04, 1.05, 1.06]

# share of district workers (%) in 2011 by tier: Manufacturing (ex textiles), Construction, IT-ITeS, Healthcare, Textiles (as in v3)
TIER_SHARE = {
    "metro_core": [11.0, 9.0, 3.5, 3.3, 3.5], "industrial_it_hub": [18.0, 8.0, 7.5, 2.7, 3.5], "industrial_hub": [21.0, 8.0, 1.2, 2.4, 5.0],
    "industrial_msme": [17.0, 8.0, 0.8, 2.1, 7.0], "textile_cluster": [11.0, 7.0, 0.5, 1.8, 14.0], "industrial_port": [18.0, 8.0, 0.8, 2.1, 3.0],
    "logistics_hub": [12.0, 9.0, 1.4, 3.0, 2.5], "metro_residential": [8.0, 8.0, 1.6, 3.0, 5.5], "metro_administrative": [3.0, 5.0, 3.5, 3.6, 1.0],
    "industrial_mining": [11.0, 9.0, 0.5, 1.8, 1.0], "semi_industrial": [9.0, 7.0, 0.6, 2.1, 3.0], "agrarian_developing": [4.0, 6.0, 0.35, 1.6, 2.5],
    "agrarian_migrant": [3.0, 6.0, 0.3, 1.3, 2.0], "peripheral_tribal": [2.5, 5.0, 0.2, 1.1, 1.2], "peripheral_agrarian": [3.0, 5.0, 0.25, 1.2, 1.5],
    "peripheral_coastal": [4.0, 6.5, 0.35, 1.6, 1.5],
}
# known concentrations the tier averages miss: multipliers on the 2011 share, by LGD district code
DISTRICT_SECTOR_ADJ = {
    "IT-ITeS": {490: 1.25, 568: 1.50, 303: 0.45, 525: 2.60, 507: 1.90, 518: 1.70, 700: 1.50, 144: 1.70, 446: 1.40, 555: 1.50, 565: 1.60, 608: 1.50,
                569: 1.30, 545: 1.30, 691: 1.30},
    "Textiles and Apparel": {634: 3.0, 459: 2.0, 573: 1.6, 576: 1.6, 36: 1.6, 179: 2.0},
    "Manufacturing": {438: 1.15, 457: 1.20, 461: 1.15, 442: 1.20, 462: 1.30, 157: 1.10, 144: 1.10, 569: 1.20, 577: 1.30},
}

# Calibration of the sector levels: the 2011 tier shares above were set for the 56 districts of v3.  Over 317 districts they overshoot, so each sector is scaled so
# that the December 2025 totals for the ten states are of the same order as published national workforce figures (about 27 M manufacturing excluding textiles,
# 38 M construction, 5 M IT-ITeS, 8 M health care, 12 M textiles and apparel in these states).  An approximate anchor, not a statistic.
LEVEL_SCALE = {"Manufacturing": 0.62, "Construction": 1.0, "IT-ITeS": 0.43, "Healthcare": 0.72, "Textiles and Apparel": 0.85}

# shocks (monthly intensity; 1.0 = the April/May 2020 national lockdown)
COVID = {(2020, 3): .35, (2020, 4): 1.0, (2020, 5): 1.0, (2020, 6): .70, (2020, 7): .55, (2020, 8): .45, (2020, 9): .35, (2020, 10): .25, (2020, 11): .20,
         (2020, 12): .15, (2021, 1): .10, (2021, 2): .08, (2021, 3): .12, (2021, 4): .25, (2021, 5): .35, (2021, 6): .20, (2021, 7): .08, (2021, 8): .05,
         (2021, 9): .04, (2021, 10): .03, (2022, 1): .08, (2022, 2): .05}
GFC = {(2008, 10): .3, (2008, 11): .5, (2008, 12): .7, (2009, 1): .9, (2009, 2): 1.0, (2009, 3): 1.0, (2009, 4): .9, (2009, 5): .8, (2009, 6): .6,
       (2009, 7): .5, (2009, 8): .4, (2009, 9): .3, (2009, 10): .2, (2009, 11): .1}                          # the 2008-09 global slowdown
COVID_I = np.array([COVID.get((y, m), 0.0) for y, m in zip(YEAR, MONTH)])
GFC_I = np.array([GFC.get((y, m), 0.0) for y, m in zip(YEAR, MONTH)])
IDX_RECOVERY_START = (2021 - 2000) * 12 + 6                                                                  # 2021-07
IDX_ESHRAM_LAUNCH = (2021 - 2000) * 12 + 7                                                                   # 2021-08
NCS_LAUNCH, QES_START, PLFS_START = (2015 - 2000) * 12 + 6, (2009 - 2000) * 12, (2017 - 2000) * 12 + 6      # NCS 2015-07, hiring survey 2009-01, labour-force survey 2017-07
PORTAL_BASE = {"Manufacturing": .35, "Construction": .15, "IT-ITeS": .90, "Healthcare": .50, "Textiles and Apparel": .25}


# ======================================================================================================================
# 2. HELPERS
# ======================================================================================================================
def path(anchors):
    """Monthly series from calendar-year anchors (2000..2025) placed at mid-year, flat beyond the ends."""
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
    s, m = np.zeros(12), np.arange(1, 13)
    if sector == "Construction":
        a, b, amp = MONSOON[state]
        s += np.where((m >= a) & (m <= b), -amp, 0.03)
    elif sector == "Textiles and Apparel":
        s += np.where((m >= 9) & (m <= 11), 0.09 if state == "West Bengal" else 0.07, 0.0) + np.where((m >= 4) & (m <= 5), -0.03, 0.0)
    elif sector == "Manufacturing":
        s += np.where((m >= 10) | (m <= 3), 0.02, 0.0) + np.where((m >= 6) & (m <= 8), -0.015, 0.0)
    elif sector == "Healthcare":
        s += np.where((m >= 7) & (m <= 10), 0.015, 0.0)
    else:
        s += np.where((m >= 7) & (m <= 9), 0.012, 0.0) + np.where(m <= 3, -0.005, 0.0)
    f = 1.0 + s
    return (f / f.mean())[MONTH - 1]


def softmax0(logits):
    """Softmax over axis 1 of an (nd, K, N) array."""
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def split_int(total, share, floor):
    """Integer counts (nd, K, N) that add up exactly to `total` (nd, N); each is at least `floor` (0 or 1).  Rounding by largest remainder."""
    nd, K, n = share.shape
    rest = (total - K * floor).astype(np.int64)
    assert (rest >= 0).all()
    raw = share.transpose(0, 2, 1).reshape(-1, K) * rest.reshape(-1, 1)
    fl = np.floor(raw).astype(np.int64)
    rem = rest.reshape(-1) - fl.sum(axis=1)
    rank = np.argsort(np.argsort(-(raw - fl), axis=1), axis=1)
    out = fl + (rank < rem[:, None]) + floor
    return out.reshape(nd, n, K).transpose(0, 2, 1)


# ======================================================================================================================
# 3. GENERATION
# ======================================================================================================================
def sector_level(rng, k, sector, cat):
    """District-sector arrays (nd, N) for one sector: employment, unemployment, vacancies, seats, certified, seekers, wage and demographic shares."""
    sp = SECTOR[sector]
    nd = len(cat)
    st = cat.State_Name.to_numpy()
    pop = cat.Pop_2011.to_numpy()[:, None] * (1 + cat.Pop_Growth_Annual.to_numpy()[:, None]) ** YRS[None, :]
    wap = pop * 0.665
    lfpr = path(LFPR_WAP)[None, :] * np.array([STATE_LFPR[s] for s in st])[:, None]
    nat_ur = path(URBAN_UR)
    workers = wap * lfpr * (1 - nat_ur[None, :] / 100)
    idx_total = 1.015 ** YRS
    stringency = np.array([STATE_COVID[s] for s in st])[:, None]
    wage_idx = 1.055 ** YRS
    tier_prem = np.array([1.25 if t in ("metro_core", "metro_administrative") else 1.15 if "hub" in t else 1.0 for t in cat.Econ_Tier])[:, None]
    cert_w = np.array([.06, .04, .05, .04, .05, .10, .26, .14, .07, .07, .06, .06])[MONTH - 1]
    util = np.where(FY == 2020, 0.55, np.where(FY == 2021, 0.85, 0.72))
    seat_mult = np.array(SEATS_PATH)[np.clip(FY - 2000, 0, 25)]

    adj = DISTRICT_SECTOR_ADJ.get(sector, {})
    share0 = np.array([TIER_SHARE[t][k] for t in cat.Econ_Tier])[:, None] / 100.0
    share0 = share0 * np.array([adj.get(int(c), 1.0) * C.sector_state_weight(sector, s) for c, s in zip(cat.District_LGD_Code, st)])[:, None] * LEVEL_SCALE[sector]
    dist_eff = np.exp(rng.normal(0, sp["dist_sigma"], (nd, 1)))
    dist_eff /= dist_eff.mean()
    seas = np.vstack([seasonal(sector, s) for s in st])
    # ---- employment ---------------------------------------------------------------------------------------------------
    trend = path(IDX[sector])[None, :] / idx_total[None, :]
    shock = 1 + sp["covid_emp"] * COVID_I[None, :] * stringency + sp["gfc_emp"] * GFC_I[None, :]
    tau = np.maximum(T - IDX_RECOVERY_START, 0)
    scar = np.zeros(N)
    if sp["covid_emp"] < 0:                                   # residual scar closing as beta * ln(1 + months since 2021-07)
        scar = np.where(T >= IDX_RECOVERY_START, sp["covid_emp"] * 0.20 * np.clip(1 - sp["rec_beta"] * np.log1p(tau), 0, 1), 0.0)
    policy = 1 + sp["demon"] * ((YEAR == 2016) & (MONTH >= 11) | (YEAR == 2017) & (MONTH == 1)) + sp["gst"] * ((YEAR == 2017) & (MONTH >= 7) & (MONTH <= 10))
    noise = np.exp(ar1(rng, nd, 0.90, 0.006) + rng.normal(0, 0.008, (nd, N)))
    emp = workers * share0 * trend * dist_eff * seas * (shock + scar[None, :] * stringency) * policy[None, :] * noise
    emp = np.maximum(np.rint(emp), 5).astype(np.int64)
    # ---- unemployment rate ----------------------------------------------------------------------------------------------
    spike = (4.5 if sp["covid_emp"] < 0 else -0.8) * COVID_I[None, :]
    ur = (nat_ur[None, :] + sp["ur_off"] + np.array([STATE_UR[s] for s in st])[:, None] + spike + ar1(rng, nd, 0.90, 0.12) + rng.normal(0, 0.15, (nd, N)))
    ur = np.round(np.clip(ur, 3.5, 12.0), 2)
    # ---- vacancies (demand) ---------------------------------------------------------------------------------------------
    idx_path = path(IDX[sector])
    yoy = np.r_[np.full(12, idx_path[12] / idx_path[0] - 1), idx_path[12:] / idx_path[:-12] - 1]
    tight = np.clip(1 + 2.0 * (yoy - yoy[:240].mean()), 0.5, 1.8)[None, :]               # growth against the 2000-2019 average
    shock_v = np.clip(1 + sp["covid_vac"] * COVID_I[None, :] * stringency + sp["gfc_vac"] * GFC_I[None, :], 0.1, None)
    vac_dist = np.exp(rng.normal(0, 0.20, (nd, 1)))
    vac = emp * sp["vac_rate"] * path(HIRING[sector])[None, :] * tight * shock_v * vac_dist * np.exp(ar1(rng, nd, 0.93, 0.035) + rng.normal(0, 0.04, (nd, N)))
    vac = np.maximum(np.rint(vac), 5).astype(np.int64)
    # ---- training capacity (supply side) -----------------------------------------------------------------------------
    lag = np.clip(T - 36, 0, None)
    dens = emp[:, lag] / wap[:, lag]
    alloc = 0.5 * dens / dens.mean(axis=0, keepdims=True) + 0.5
    seats_year = (wap / 1000.0) * sp["seat_rate"] * np.array([STATE_SEATS[s] for s in st])[:, None] * seat_mult[None, :] * alloc * np.exp(rng.normal(0, 0.25, (nd, 1)))
    seats = np.maximum(np.rint(seats_year[:, np.clip((FY - 2000) * 12 + 3, 0, N - 1)]), 5).astype(np.int64)    # a stock fixed for the financial year (its April value)
    cert = np.rint(seats * util[None, :] * 0.82 * cert_w[None, :] * np.exp(rng.normal(0, 0.06, (nd, N)))).astype(np.int64)
    cert_ext = np.hstack([cert[:, :12], cert])
    cert_12m = pd.DataFrame(cert_ext.T).rolling(12).sum().to_numpy().T[:, 12:]
    # ---- registered seekers (supply proxy) --------------------------------------------------------------------------
    reg = 0.02 + 0.33 / (1 + np.exp(-((T - IDX_ESHRAM_LAUNCH) - 8) / 6.0))                # e-Shram ramp-up from August 2021
    unemployed = emp * ur / (100 - ur)
    seek = (0.6 * unemployed + sp["informal"] * emp * reg[None, :] + 0.4 * cert_12m) * np.exp(rng.normal(0, 0.15, (nd, 1))) * np.exp(ar1(rng, nd, 0.95, 0.02) + rng.normal(0, 0.035, (nd, N)))
    seek = np.maximum(np.rint(seek), 5).astype(np.int64)
    # ---- wage and demographic shares -------------------------------------------------------------------------------------
    wage = sp["base_wage"] * wage_idx[None, :] * tier_prem * np.array([STATE_WAGE[s] for s in st])[:, None] * np.exp(rng.normal(0, 0.012, (nd, N)))
    fem = sp["female"] + 0.0015 * YRS[None, :] + np.array([STATE_FEMALE[s] for s in st])[:, None] + rng.normal(0, 0.004, (nd, 1)) + rng.normal(0, 0.006, (nd, N))
    metro = np.array([1.0 if t.startswith("metro") or "it_hub" in t else 0.0 for t in cat.Econ_Tier])[:, None]
    grad = sp["grad"] + 0.10 * metro * (1 - sp["grad"]) * 0.3 + rng.normal(0, 0.004, (nd, 1)) + rng.normal(0, 0.004, (nd, N))
    youth = sp["youth"] + rng.normal(0, 0.005, (nd, 1)) + rng.normal(0, 0.006, (nd, N))
    return dict(emp=emp, ur=ur, vac=vac, seats=seats, cert=cert, seek=seek, wage=wage, fem=fem, grad=grad, youth=youth, seas=seas, pop=pop, stringency=stringency)


def trade_level(rng, sector, cat, S):
    """Split the district-sector counts of one sector into its five trades; returns arrays (nd, 5, N) that add up to the sector arrays exactly."""
    sp, P = SECTOR[sector], TR.arrays(sector)
    nd, K = len(cat), 5
    states = sorted(cat.State_Name.unique())
    sidx = np.array([states.index(s) for s in cat.State_Name])
    tilt = rng.normal(0, 0.12, (len(states), K))[sidx] + rng.normal(0, 0.18, (nd, K))                     # persistent state and district mix
    seas_term = (P["sm"] - 1)[None, :, None] * (S["seas"][:, None, :] - 1)
    covid_term = (P["cm"] - 1)[None, :, None] * (sp["covid_emp"] * COVID_I[None, :] * S["stringency"])[:, None, :] * 0.8
    base = np.log(P["e"])[None, :, None] + P["g"][None, :, None] * YRS[None, None, :] + tilt[:, :, None] + seas_term + covid_term
    walk = ar1(rng, nd * K, 0.97, 0.012).reshape(nd, K, N) + rng.normal(0, 0.01, (nd, K, N))
    LE = base + walk
    LV = LE + np.log(P["v"])[None, :, None] + ar1(rng, nd * K, 0.90, 0.03).reshape(nd, K, N)
    LS = 0.7 * (np.log(P["e"])[None, :, None] + tilt[:, :, None]) - 0.5 * np.log(P["wage"])[None, :, None] + ar1(rng, nd * K, 0.95, 0.02).reshape(nd, K, N)
    LT = np.log(P["seat"] * P["e"] ** 0.5)[None, :, None] + 0.5 * tilt[:, :, None] + ar1(rng, nd * K, 0.98, 0.01).reshape(nd, K, N)
    sE, sV, sS, sT = softmax0(LE), softmax0(LV), softmax0(LS), softmax0(LT)
    sC = softmax0(np.log(sT) + rng.normal(0, 0.05, (nd, K, N)))
    out = dict(emp=split_int(S["emp"], sE, 1), vac=split_int(S["vac"], sV, 1), seek=split_int(S["seek"], sS, 1),
               seats=split_int(S["seats"], sT, 1), cert=split_int(S["cert"], sC, 0))
    out["wage"] = S["wage"][:, None, :] * P["wage"][None, :, None] * np.exp(rng.normal(0, 0.008, (nd, K, N)))
    out["ur"] = np.repeat(S["ur"][:, None, :], K, axis=1)
    out["fem"] = np.clip(S["fem"][:, None, :] + P["fa"][None, :, None] + rng.normal(0, 0.004, (nd, K, N)), 0.02, 0.95)
    out["grad"] = np.clip(S["grad"][:, None, :] + P["ga"][None, :, None] + rng.normal(0, 0.004, (nd, K, N)), 0.0, 0.99)
    out["youth"] = np.clip(S["youth"][:, None, :] + P["ya"][None, :, None] + rng.normal(0, 0.005, (nd, K, N)), 0.02, 0.90)
    return out


def source_channels(rng, sector, emp, vac):
    """Four imperfect measurements of demand and employment for arrays (series, N): each has its own coverage, timing, noise and start date."""
    n = emp.shape[0]
    f = lambda x: x.astype(np.float64)
    cov = PORTAL_BASE[sector] * (0.05 + 0.95 / (1 + np.exp(-((YEAR + (MONTH - 1) / 12.0) - 2012) / 4.0)))      # job-portal share of all openings, rising with online hiring
    lead = np.hstack([vac[:, 1:], vac[:, -1:]])                                                                 # postings appear a month before the opening is counted
    portal = f(lead) * cov[None, :] * np.exp(ar1(rng, n, 0.80, 0.10) + rng.normal(0, 0.12, (n, N)))
    v3 = pd.DataFrame(f(vac).T).rolling(3, min_periods=1).mean().to_numpy().T
    ref = v3[:, 120:240].mean(axis=1, keepdims=True)                                                            # level of 2010-2019
    survey = 100.0 * (v3 / ref) ** 0.9 * np.exp(rng.normal(0, 0.12, (n, N)))
    qmask = (MONTH % 3 == 0)                                                                                    # one reading per quarter, held until the next
    survey = np.where(qmask[None, :], survey, np.nan)
    survey = pd.DataFrame(survey.T).ffill().to_numpy().T
    survey[:, :QES_START] = np.nan
    ncs_cov = np.clip(0.02 + 0.18 * (T - NCS_LAUNCH) / (N - 1 - NCS_LAUNCH), 0.0, None) * (1.4 if sector in ("Construction", "Textiles and Apparel") else 1.0)
    ncs = f(vac) * ncs_cov[None, :] * np.exp(rng.normal(0, 0.20, (n, N)))
    ncs[:, :NCS_LAUNCH] = np.nan
    sig = np.minimum(0.6, 0.08 + 0.5 / np.sqrt(np.maximum(f(emp), 1.0) / 100.0))                                 # small series are measured worse
    plfs = f(emp) * np.exp(rng.normal(0, 1, (n, N)) * sig)
    plfs = np.where(qmask[None, :], plfs, np.nan)
    plfs = pd.DataFrame(plfs.T).ffill().to_numpy().T
    plfs[:, :PLFS_START] = np.nan
    return {"Sig_Portal_Postings": np.rint(portal), "Sig_Hiring_Survey_Index": survey, "Sig_NCS_Vacancies": np.rint(ncs), "Sig_Labour_Survey_Employment": np.rint(plfs)}


def generate(cat, seed=C.SEED):
    """Returns (trade_frame, sector_frame, dim_series) for the districts in `cat`."""
    t0 = time.time()
    cat = cat.reset_index(drop=True)
    nd = len(cat)
    streams = np.random.SeedSequence(seed).spawn(len(SECTORS))
    trade_tabs = C.load_trades()
    series_blocks, sector_blocks, dims = [], [], []
    cols_t = ["emp", "vac", "seek", "seats", "cert", "wage", "ur", "fem", "grad", "youth"]
    for k, sector in enumerate(SECTORS):
        rng = np.random.default_rng(streams[k])
        S = sector_level(rng, k, sector, cat)
        Tt = trade_level(rng, sector, cat, S)
        tr = trade_tabs[trade_tabs.Sector_Name == sector].reset_index(drop=True)
        assert list(tr.NCO_Code) == TR.arrays(sector)["code"], sector
        blk = {c: Tt[c].reshape(nd * 5, N) for c in cols_t}
        blk.update(source_channels(rng, sector, blk["emp"], blk["vac"]))
        pop = np.repeat(S["pop"], 5, axis=0)
        blk["pop"] = pop
        series_blocks.append(blk)
        sector_blocks.append({c: S[c] for c in ("emp", "vac", "seek", "seats", "cert", "wage", "ur")})
        for d in range(nd):
            for j in range(5):
                dims.append((C.series_id(cat.District_LGD_Code[d], tr.Trade_Code[j]), int(cat.District_LGD_Code[d]), cat.District_Name[d], cat.State_Name[d], cat.Econ_Tier[d],
                             sector, tr.Sector_Code[j], tr.Trade_Code[j], int(tr.NCO_Code[j]), tr.Trade_Name[j]))
        print(f"  {sector}: done ({time.time() - t0:.0f} s)", flush=True)
    dim = pd.DataFrame(dims, columns=["Series_ID", "District_LGD_Code", "District_Name", "State_Name", "Econ_Tier", "Sector_Name", "Sector_Code", "Trade_Code", "NCO_Code", "Trade_Name"])
    order = np.argsort(dim.Series_ID.to_numpy(), kind="stable")
    dim = dim.iloc[order].reset_index(drop=True)
    names = {"emp": "Total_Employed_Workers", "vac": "Active_Job_Vacancies", "seek": "eShram_Registered_Seekers", "seats": "Training_Seats_Sanctioned",
             "cert": "Trainees_Certified_Monthly", "wage": "Avg_Monthly_Wage_INR", "ur": "Unemployment_Rate_Pct", "pop": "District_Total_Population_Est",
             "fem": "Female_Share_Pct", "grad": "Edu_Graduate_and_Above_Pct", "youth": "Age_15_24_Pct"}
    data = {"Series_ID": np.repeat(dim.Series_ID.to_numpy(), N), "Date": np.tile(MONTHS.to_numpy(), len(dim))}
    int_cols = {"emp", "vac", "seek", "seats", "cert", "wage", "pop"}
    for key in list(names) + ["Sig_Portal_Postings", "Sig_Hiring_Survey_Index", "Sig_NCS_Vacancies", "Sig_Labour_Survey_Employment"]:
        A = np.vstack([b[key] for b in series_blocks])[order]
        if key in int_cols:
            data[names.get(key, key)] = np.rint(A).astype(np.int32).ravel() if key in ("wage", "pop") else A.astype(np.int32).ravel()
        elif key in ("ur", "fem", "grad", "youth"):
            data[names[key]] = (np.round(A * (100 if key != "ur" else 1), 2)).astype(np.float32).ravel()
        else:
            data[key] = A.astype(np.float32).ravel()
    trade = pd.DataFrame(data)
    # sector table: the district-sector series (every trade count adds up to these)
    sec = []
    for k, sector in enumerate(SECTORS):
        b = sector_blocks[k]
        sec.append(pd.DataFrame({"District_LGD_Code": np.repeat(cat.District_LGD_Code.to_numpy().astype(np.int32), N), "Sector_Name": sector,
                                 "Date": np.tile(MONTHS.to_numpy(), nd), "Total_Employed_Workers": b["emp"].astype(np.int32).ravel(),
                                 "Active_Job_Vacancies": b["vac"].astype(np.int32).ravel(), "eShram_Registered_Seekers": b["seek"].astype(np.int32).ravel(),
                                 "Training_Seats_Sanctioned": b["seats"].astype(np.int32).ravel(), "Trainees_Certified_Monthly": b["cert"].astype(np.int32).ravel()}))
    sector_frame = pd.concat(sec, ignore_index=True)
    print(f"generated {len(dim):,} series x {N} months = {len(trade):,} rows in {time.time() - t0:.0f} s", flush=True)
    return trade, sector_frame, dim


def content_hash(trade):
    """SHA-256 over the model targets of the panel, in series/date order: the identity of the data independent of the file format."""
    h = hashlib.sha256()
    for c in ("Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Training_Seats_Sanctioned", "Trainees_Certified_Monthly"):
        h.update(np.ascontiguousarray(trade[c].to_numpy()).tobytes())
    return h.hexdigest()


def main():
    cat = pd.read_csv(C.DATA / "district_catalog.csv")
    assert len(cat) == C.N_DISTRICTS
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    trade, sector, dim = generate(cat)
    pt, ps = OUT_RAW / "trade_monthly_2000_2025.parquet", OUT_RAW / "sector_monthly_2000_2025.parquet"
    trade.to_parquet(pt, index=False, compression="zstd")
    sector.to_parquet(ps, index=False, compression="zstd")
    dim.to_csv(C.DATA / "dim_series.csv", index=False)
    last = trade[trade.Date == trade.Date.max()].merge(dim[["Series_ID", "Sector_Name"]], on="Series_ID")
    man = {"version": "v4", "seed": C.SEED, "series": int(dim.shape[0]), "months": N, "rows": int(len(trade)), "first_month": "2000-01", "last_month": "2025-12",
           "districts": int(dim.District_LGD_Code.nunique()), "states": int(dim.State_Name.nunique()), "sectors": int(dim.Sector_Name.nunique()), "trades": int(dim.Trade_Code.nunique()),
           "content_sha256": content_hash(trade), "trade_parquet_sha256": hashlib.sha256(pt.read_bytes()).hexdigest(), "trade_parquet_bytes": pt.stat().st_size,
           "sector_parquet_sha256": hashlib.sha256(ps.read_bytes()).hexdigest(), "district_catalog_sha256": hashlib.sha256((C.DATA / "district_catalog.csv").read_bytes()).hexdigest(),
           "employed_dec2025_by_sector": {s: int(v) for s, v in last.groupby("Sector_Name").Total_Employed_Workers.sum().items()},
           "note": "Simulated data. The parquet files are rebuilt with: python src/v4/generate.py"}
    (C.DATA / "DATA_MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("series", "rows", "content_sha256", "trade_parquet_bytes", "employed_dec2025_by_sector")}, indent=2))


if __name__ == "__main__":
    main()
