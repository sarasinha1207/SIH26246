#!/usr/bin/env python3
"""
v4 phase 1 - the district catalogue: every district of the 10 pilot states (317), keyed by its official LGD code.

Output: data/v4/district_catalog.csv  (+ data/v4/district_catalog_provenance.json)

Where each column comes from
  * names, LGD codes, state codes   the LGD 2024 district layer (data/v4/lgd_districts_10_states.csv); the display name of the 56 districts already in v3
                                    is kept, other districts use a common spelling (NAME_FIXES) and the LGD spelling stays in LGD_Name
  * Pop_2011                        Census 2011, in order of preference
                                      1. data/v4/census_2011_district_tables.csv   figures read from public Census 2011 district tables (source per row)
                                      2. data/raw/district_catalog.csv             the v3 catalogue (Maharashtra, Delhi, and four districts of Tamil Nadu)
                                    A district that lost territory to a district created after the Census (Gujarat 2013, Pathankot 2011) is reduced by the
                                    population of the new district (CARVE_OUT, with the shares an assumption where a new district drew on two parents).  In Gujarat and
                                    Punjab one district absorbs the small remaining difference so that the state equals the Census 2011 state total.
                                    Pop_Source says which rule gave each figure.
  * Pop_Growth_Annual               the state's 2001-2011 Census growth (annualised) x a factor for the economic tier (v3 value for the 56 v3 districts)
  * Econ_Tier                       v3 value for the 56 v3 districts; a named list for well-known hubs and peripheral districts; otherwise a rule on population
  * Area_Km2                        from the polygon in the LGD layer (equirectangular, so approximate)

The data built on this catalogue is SIMULATED.  Run: python src/v4/catalog.py
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import config as C  # noqa: E402
import build_boundaries as bb  # noqa: E402  (WKB reader and the polygon-area helper used for the v3 map)

LGD_LAYER = C.ROOT / "data" / "external" / "lgd_districts" / "LGD_Districts.parquet"
V3_CATALOG = C.ROOT / "data" / "raw" / "district_catalog.csv"
CENSUS_TABLES = C.DATA / "census_2011_district_tables.csv"
OUT = C.DATA / "district_catalog.csv"

# Census of India 2011, state populations (Telangana: the area of the present state)
CENSUS_2011_STATE_TOTAL = {
    "Delhi": 16787941, "Gujarat": 60439692, "Karnataka": 61095297, "Kerala": 33406061, "Maharashtra": 112374333,
    "Punjab": 27743338, "Tamil Nadu": 72147030, "Telangana": 35003674, "Uttar Pradesh": 199812341, "West Bengal": 91276115,
}
# 2001-2011 decadal growth of the state, annualised and rounded (Census of India 2011 provisional totals)
STATE_GROWTH = {"Delhi": 0.0180, "Gujarat": 0.0175, "Karnataka": 0.0145, "Kerala": 0.0050, "Maharashtra": 0.0150,
                "Punjab": 0.0130, "Tamil Nadu": 0.0145, "Telangana": 0.0128, "Uttar Pradesh": 0.0180, "West Bengal": 0.0125}
TIERS = ["metro_core", "metro_residential", "metro_administrative", "industrial_it_hub", "industrial_hub", "industrial_msme", "industrial_port",
         "industrial_mining", "textile_cluster", "logistics_hub", "semi_industrial", "agrarian_developing", "agrarian_migrant",
         "peripheral_agrarian", "peripheral_coastal", "peripheral_tribal"]                       # the 16 v3 tiers (kept so the v3 sector shares carry over)
GROWTH_FACTOR = {"metro_core": 0.6, "metro_residential": 1.1, "metro_administrative": 0.6, "industrial_it_hub": 1.35, "industrial_hub": 1.3,
                 "industrial_msme": 1.1, "industrial_port": 1.1, "industrial_mining": 0.8, "textile_cluster": 1.0, "logistics_hub": 1.0,
                 "semi_industrial": 0.95, "agrarian_developing": 0.9, "agrarian_migrant": 0.8, "peripheral_agrarian": 0.7,
                 "peripheral_coastal": 0.7, "peripheral_tribal": 0.7}
# well-known economic hubs and peripheral districts, by LGD code (every other district falls to the population rule below)
NAMED_TIER = {
    # Gujarat
    438: "metro_core", 459: "textile_cluster", 461: "industrial_hub", 457: "industrial_msme", 446: "industrial_it_hub", 442: "industrial_hub",
    462: "industrial_hub", 449: "industrial_port", 447: "industrial_port", 674: "industrial_port", 443: "industrial_port", 673: "industrial_msme",
    444: "peripheral_tribal", 641: "peripheral_tribal", 452: "peripheral_tribal", 668: "peripheral_tribal", 445: "peripheral_tribal",
    456: "peripheral_coastal", 675: "peripheral_coastal", 440: "semi_industrial", 451: "semi_industrial", 453: "semi_industrial",
    # Uttar Pradesh
    162: "metro_core", 157: "industrial_hub", 144: "industrial_it_hub", 145: "industrial_hub", 118: "industrial_msme", 169: "industrial_msme",
    119: "industrial_msme", 143: "industrial_msme", 171: "industrial_msme", 177: "industrial_msme", 179: "textile_cluster", 184: "industrial_mining",
    187: "semi_industrial", 120: "semi_industrial", 148: "semi_industrial", 661: "semi_industrial", 124: "semi_industrial", 172: "semi_industrial",
    125: "peripheral_agrarian", 127: "peripheral_agrarian", 181: "peripheral_agrarian", 182: "peripheral_agrarian", 164: "peripheral_agrarian",
    136: "peripheral_agrarian", 165: "peripheral_agrarian",
    # Karnataka
    525: "industrial_it_hub", 526: "industrial_hub", 631: "semi_industrial", 548: "industrial_msme", 545: "industrial_hub", 534: "industrial_port",
    528: "industrial_mining", 738: "industrial_mining", 527: "industrial_hub", 536: "industrial_hub", 542: "industrial_msme", 549: "peripheral_coastal",
    550: "peripheral_coastal", 541: "peripheral_agrarian", 532: "peripheral_agrarian", 535: "semi_industrial",
    # Kerala
    555: "industrial_it_hub", 565: "metro_administrative", 561: "semi_industrial", 566: "semi_industrial", 559: "peripheral_coastal", 554: "peripheral_coastal",
    562: "agrarian_migrant", 563: "semi_industrial", 557: "semi_industrial", 558: "peripheral_coastal", 567: "peripheral_agrarian",
    556: "peripheral_agrarian", 564: "peripheral_agrarian", 560: "semi_industrial",
    # Punjab
    36: "industrial_msme", 34: "industrial_msme", 27: "industrial_hub", 41: "semi_industrial", 608: "industrial_it_hub", 28: "semi_industrial",
    42: "industrial_hub", 30: "industrial_msme", 662: "semi_industrial", 33: "semi_industrial", 35: "semi_industrial", 40: "semi_industrial",
    # Tamil Nadu (beyond the four in v3)
    569: "industrial_hub", 634: "textile_cluster", 573: "textile_cluster", 576: "textile_cluster", 584: "industrial_msme", 580: "industrial_msme",
    578: "semi_industrial", 591: "industrial_hub", 595: "industrial_msme", 731: "industrial_msme", 732: "industrial_msme", 577: "industrial_hub",
    594: "industrial_port", 592: "semi_industrial", 575: "peripheral_coastal", 579: "peripheral_coastal", 735: "peripheral_agrarian",
    587: "peripheral_agrarian", 610: "industrial_mining", 570: "industrial_port", 590: "peripheral_agrarian", 581: "peripheral_agrarian",
    583: "peripheral_coastal", 597: "industrial_msme", 572: "industrial_msme",
    # Telangana
    507: "metro_core", 518: "industrial_it_hub", 700: "industrial_it_hub", 691: "industrial_hub", 522: "semi_industrial", 686: "semi_industrial",
    508: "semi_industrial", 516: "semi_industrial", 509: "semi_industrial", 690: "industrial_mining", 684: "industrial_mining", 682: "industrial_mining",
    501: "peripheral_tribal", 699: "peripheral_tribal", 720: "peripheral_tribal", 687: "peripheral_tribal",
    # West Bengal (beyond the five in v3)
    704: "industrial_mining", 306: "semi_industrial", 309: "peripheral_agrarian", 702: "peripheral_tribal", 664: "peripheral_tribal",
    314: "semi_industrial", 319: "agrarian_migrant", 320: "semi_industrial", 321: "peripheral_agrarian", 703: "peripheral_tribal", 317: "industrial_port",
}
DEFAULT_TIER, SMALL_POP, LARGE_POP = "agrarian_developing", 1_200_000, 3_200_000          # rule for a district that is not in NAMED_TIER: by 2011 population
# districts created after the Census took territory from older ones; new district -> {parent: share of the new district's population}
CARVE_OUT = {672: {458: 1.0}, 676: {443: 0.65, 438: 0.35}, 668: {461: 1.0}, 674: {447: 1.0}, 675: {448: 1.0},
             669: {454: 0.75, 450: 0.25}, 673: {457: 0.85, 460: 0.15}, 662: {32: 1.0}}            # the Botad, Mahisagar and Morbi shares are assumptions
ABSORB = {"Gujarat": 438, "Punjab": 31}                                                           # district that takes the small difference to the state total

# common spellings (the LGD spelling is kept in LGD_Name)
NAME_FIXES = {
    438: "Ahmedabad", 672: "Aravalli", 441: "Banaskantha", 668: "Chhota Udaipur", 444: "The Dangs", 445: "Dahod", 449: "Kutch", 451: "Mehsana",
    454: "Panchmahal", 458: "Sabarkantha", 160: "Kushinagar", 159: "Lakhimpur Kheri", 175: "Raebareli", 178: "Sant Kabir Nagar", 181: "Shrawasti",
    182: "Siddharthnagar", 524: "Bagalkot", 531: "Chamarajanagar", 630: "Chikkaballapur", 31: "Firozpur", 608: "SAS Nagar (Mohali)",
    40: "Shaheed Bhagat Singh Nagar", 575: "Kanyakumari", 587: "The Nilgiris", 594: "Thoothukudi", 596: "Viluppuram", 732: "Tirupattur",
    699: "Komaram Bheem Asifabad", 700: "Medchal-Malkajgiri", 518: "Rangareddy", 512: "Mahbubnagar", 303: "North 24 Parganas", 304: "South 24 Parganas",
    308: "Cooch Behar", 310: "Dakshin Dinajpur", 311: "Uttar Dinajpur", 316: "Malda", 317: "Purba Medinipur", 318: "Paschim Medinipur",
}


def load_lgd():
    """The 317 districts with an approximate area and boundary details from the polygon layer."""
    lgd = pd.read_csv(C.LGD_FILE)
    t = pq.read_table(LGD_LAYER, filters=[("dist_lgd", "in", [int(c) for c in lgd.dist_lgd])], columns=["dist_lgd", "dtname", "year_stat", "geometry"]).to_pandas()
    assert len(t) == 317, len(t)
    areas = {int(r.dist_lgd): bb.area_km2(bb.parse_wkb(bytes(r.geometry))) for r in t.itertuples()}
    out = lgd.rename(columns={"dtname": "LGD_Name", "stname": "State_Raw", "state_lgd": "State_LGD_Code", "dist_lgd": "District_LGD_Code"}).copy()
    out["State_Name"] = out.State_Raw.str.title()
    out["Area_Km2"] = out.District_LGD_Code.map(areas).round(1)
    out["Boundary_Vintage"] = out.year_stat.fillna("unknown")
    return out[["State_Name", "State_LGD_Code", "LGD_Name", "District_LGD_Code", "Area_Km2", "Boundary_Vintage"]]


def tiers_and_names(df, v3):
    df = df.merge(v3[["District_LGD_Code", "District_Name", "Econ_Tier", "Pop_2011", "Pop_Growth_Annual"]].rename(
        columns={"District_Name": "v3_name", "Econ_Tier": "v3_tier", "Pop_2011": "v3_pop", "Pop_Growth_Annual": "v3_growth"}), on="District_LGD_Code", how="left")
    df["District_Name"] = [r.v3_name if isinstance(r.v3_name, str) else NAME_FIXES.get(int(r.District_LGD_Code), r.LGD_Name) for r in df.itertuples()]
    return df


def populations(df, census):
    """Pop_2011 and Pop_Source for every district, with the corrections for later splits."""
    tab = census.set_index("District_LGD_Code")
    pop, src = {}, {}
    for r in df.itertuples():
        code = int(r.District_LGD_Code)
        if code in tab.index:
            row = tab.loc[code]
            pop[code] = float(row.Pop_2011_Old_Boundary) if pd.notna(row.Pop_2011_Old_Boundary) else float(row.Pop_2011_Listed)
            src[code] = "census_2011_table"
        elif pd.notna(r.v3_pop):
            pop[code], src[code] = float(r.v3_pop), "census_2011 (v3 catalogue)"
        else:
            raise SystemExit(f"no Census 2011 population for {r.District_Name} ({code})")
    for child, parents in CARVE_OUT.items():
        for parent, share in parents.items():
            pop[parent] -= share * pop[child]
            src[parent] = "census_2011_table, reduced by the district created from it"
    df["Pop_2011"] = [pop[int(c)] for c in df.District_LGD_Code]
    df["Pop_Source"] = [src[int(c)] for c in df.District_LGD_Code]
    for state, code in ABSORB.items():
        m = df.State_Name == state
        diff = CENSUS_2011_STATE_TOTAL[state] - df.loc[m, "Pop_2011"].sum()
        i = df.index[df.District_LGD_Code == code][0]
        assert abs(diff) < 0.15 * df.at[i, "Pop_2011"], (state, diff)          # the figure of the absorbing district is the least certain one
        df.at[i, "Pop_2011"] += diff
        df.at[i, "Pop_Source"] += "; absorbs the state-total difference"
    df["Pop_2011"] = df.Pop_2011.round().astype(np.int64)
    return df


def assign_tier(df):
    tier, src = [], []
    for r in df.itertuples():
        code = int(r.District_LGD_Code)
        if isinstance(r.v3_tier, str):
            tier.append(r.v3_tier), src.append("v3 catalogue")
        elif code in NAMED_TIER:
            tier.append(NAMED_TIER[code]), src.append("named list")
        else:
            tier.append("peripheral_agrarian" if r.Pop_2011 < SMALL_POP else "semi_industrial" if r.Pop_2011 > LARGE_POP else DEFAULT_TIER), src.append("rule on population")
    df["Econ_Tier"], df["Tier_Source"] = tier, src
    return df


def growth(df):
    base = df.State_Name.map(STATE_GROWTH) * df.Econ_Tier.map(GROWTH_FACTOR)
    df["Pop_Growth_Annual"] = [round(float(r.v3_growth), 4) if pd.notna(r.v3_growth) else round(float(b), 4) for r, b in zip(df.itertuples(), base)]
    return df


def build():
    v3 = pd.read_csv(V3_CATALOG)
    census = pd.read_csv(CENSUS_TABLES)
    df = tiers_and_names(load_lgd(), v3)
    df = growth(assign_tier(populations(df, census)))
    df = df.sort_values(["State_Name", "District_Name"]).reset_index(drop=True)
    cols = ["State_Name", "State_LGD_Code", "District_Name", "LGD_Name", "District_LGD_Code", "Pop_2011", "Pop_Source", "Pop_Growth_Annual",
            "Econ_Tier", "Tier_Source", "Area_Km2", "Boundary_Vintage"]
    return df[cols]


def main():
    df = build()
    df.to_csv(OUT, index=False)
    by_src = df.Pop_Source.str.split(";").str[0].value_counts().to_dict()
    prov = {"districts": len(df), "states": df.State_Name.nunique(), "population_sources": by_src,
            "census_2011_state_totals": CENSUS_2011_STATE_TOTAL, "state_sums": df.groupby("State_Name").Pop_2011.sum().to_dict(),
            "tiers": df.Econ_Tier.value_counts().to_dict(), "tier_sources": df.Tier_Source.value_counts().to_dict(),
            "lgd_layer_sha256": hashlib.sha256(LGD_LAYER.read_bytes()).hexdigest(), "census_tables_sha256": hashlib.sha256(CENSUS_TABLES.read_bytes()).hexdigest(),
            "note": "Pop_2011 is the Census 2011 population of the present district; where a district was split after 2011 the figure is reduced by the new district's population (see CARVE_OUT). The data built on this catalogue is simulated."}
    (C.DATA / "district_catalog_provenance.json").write_text(json.dumps(prov, indent=2, default=int), encoding="utf-8")
    print(f"{len(df)} districts in {df.State_Name.nunique()} states -> {OUT.relative_to(C.ROOT)}")
    print("population sources:", by_src)
    print(df.groupby("State_Name").agg(districts=("District_Name", "size"), pop=("Pop_2011", "sum")).assign(census=lambda d: d.index.map(CENSUS_2011_STATE_TOTAL)))


if __name__ == "__main__":
    main()
