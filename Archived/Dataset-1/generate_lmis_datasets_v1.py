import os
import numpy as np
import pandas as pd

# Set deterministic random seed
np.random.seed(42)

# Output directory
output_dir = r"e:\LMIS Data"
os.makedirs(output_dir, exist_ok=True)

# 1. Geographic Hierarchy
# Focused on: Maharashtra, Tamil Nadu (Chennai), NCT of Delhi, West Bengal (Kolkata)
geographies = [
    # Maharashtra (State Code 27)
    {"state_name": "Maharashtra", "state_code": "MH", "district_name": "Pune", "district_type": "Industrial/IT/Auto Hub", "base_pop_k": 9429, "pop_growth_rate": 0.016},
    {"state_name": "Maharashtra", "state_code": "MH", "district_name": "Mumbai Suburban", "district_type": "Metropolitan/Financial/Services", "base_pop_k": 9356, "pop_growth_rate": 0.009},
    {"state_name": "Maharashtra", "state_code": "MH", "district_name": "Thane", "district_type": "Manufacturing/Chemical/Services", "base_pop_k": 11060, "pop_growth_rate": 0.021},
    {"state_name": "Maharashtra", "state_code": "MH", "district_name": "Nagpur", "district_type": "Logistics/Engineering/Central Hub", "base_pop_k": 4653, "pop_growth_rate": 0.012},
    {"state_name": "Maharashtra", "state_code": "MH", "district_name": "Chhatrapati Sambhajinagar", "district_type": "Auto/Engineering/Textiles", "base_pop_k": 3701, "pop_growth_rate": 0.014},
    
    # Tamil Nadu - Chennai Focus (State Code 33)
    {"state_name": "Tamil Nadu", "state_code": "TN", "district_name": "Chennai", "district_type": "Automotive/Healthcare/IT Hub", "base_pop_k": 7088, "pop_growth_rate": 0.011},
    
    # NCT of Delhi (State/UT Code 07)
    {"state_name": "Delhi", "state_code": "DL", "district_name": "New Delhi", "district_type": "Administrative/Services Hub", "base_pop_k": 1420, "pop_growth_rate": 0.008},
    {"state_name": "Delhi", "state_code": "DL", "district_name": "South Delhi", "district_type": "Commercial/IT/Healthcare", "base_pop_k": 2731, "pop_growth_rate": 0.013},
    {"state_name": "Delhi", "state_code": "DL", "district_name": "North Delhi", "district_type": "Manufacturing/Trade/MSME", "base_pop_k": 1887, "pop_growth_rate": 0.010},
    
    # West Bengal - Kolkata Focus (State Code 19)
    {"state_name": "West Bengal", "state_code": "WB", "district_name": "Kolkata", "district_type": "Metropolitan/IT-ITeS/Healthcare", "base_pop_k": 4496, "pop_growth_rate": 0.005},
    {"state_name": "West Bengal", "state_code": "WB", "district_name": "Howrah", "district_type": "Industrial/Foundry/Manufacturing", "base_pop_k": 4850, "pop_growth_rate": 0.009},
]

# 2. Five Target Sectors & NCO Standards
sectors = [
    {
        "sector_name": "Manufacturing",
        "nic_2008_div": "10-33",
        "nco_family_code": "7223",
        "nco_family_name": "Metal Working Machine Tool Setters and Operators",
        "nco_secondary_code": "3122",
        "nco_secondary_name": "Manufacturing Supervisors",
        "base_wage_2016": 16500,
        "wage_annual_growth": 0.062,
        "base_female_share": 0.16,
        "edu_profile": {"below_sec": 0.38, "sec_higher_sec": 0.34, "diploma_iti": 0.20, "grad_above": 0.08},
        "age_profile": {"age_15_29": 0.32, "age_30_44": 0.42, "age_45_59": 0.22, "age_60_plus": 0.04},
        "cyclicality": 0.08,
        "covid_impact": -0.32 # Shock in Q2 2020
    },
    {
        "sector_name": "Construction",
        "nic_2008_div": "41-43",
        "nco_family_code": "7112",
        "nco_family_name": "Bricklayers and Related Workers",
        "nco_secondary_code": "3123",
        "nco_secondary_name": "Construction Supervisors",
        "base_wage_2016": 12800,
        "wage_annual_growth": 0.055,
        "base_female_share": 0.12,
        "edu_profile": {"below_sec": 0.62, "sec_higher_sec": 0.26, "diploma_iti": 0.09, "grad_above": 0.03},
        "age_profile": {"age_15_29": 0.35, "age_30_44": 0.40, "age_45_59": 0.21, "age_60_plus": 0.04},
        "cyclicality": 0.15, # High monsoon drop (July-Sept)
        "covid_impact": -0.55 # Severe migrant shutdown
    },
    {
        "sector_name": "IT-ITeS",
        "nic_2008_div": "62-63",
        "nco_family_code": "2512",
        "nco_family_name": "Software Developers",
        "nco_secondary_code": "1330",
        "nco_secondary_name": "Information and Communication Technology Services",
        "base_wage_2016": 38000,
        "wage_annual_growth": 0.085,
        "base_female_share": 0.34,
        "edu_profile": {"below_sec": 0.02, "sec_higher_sec": 0.08, "diploma_iti": 0.15, "grad_above": 0.75},
        "age_profile": {"age_15_29": 0.48, "age_30_44": 0.42, "age_45_59": 0.09, "age_60_plus": 0.01},
        "cyclicality": 0.03,
        "covid_impact": 0.12 # Strong demand surge during digitisation
    },
    {
        "sector_name": "Healthcare",
        "nic_2008_div": "86-88",
        "nco_family_code": "2211",
        "nco_family_name": "Generalist Medical Practitioners",
        "nco_secondary_code": "3221",
        "nco_secondary_name": "Nursing Associate Professionals",
        "base_wage_2016": 24500,
        "wage_annual_growth": 0.070,
        "base_female_share": 0.52,
        "edu_profile": {"below_sec": 0.10, "sec_higher_sec": 0.20, "diploma_iti": 0.40, "grad_above": 0.30},
        "age_profile": {"age_15_29": 0.38, "age_30_44": 0.38, "age_45_59": 0.20, "age_60_plus": 0.04},
        "cyclicality": 0.02,
        "covid_impact": 0.45 # Massive hospital/care demand surge
    },
    {
        "sector_name": "Textiles and apparel",
        "nic_2008_div": "13-15",
        "nco_family_code": "7531",
        "nco_family_name": "Tailors, Dressmakers, Furriers and Hatters",
        "nco_secondary_code": "8153",
        "nco_secondary_name": "Sewing Machine Operators",
        "base_wage_2016": 13200,
        "wage_annual_growth": 0.052,
        "base_female_share": 0.44,
        "edu_profile": {"below_sec": 0.54, "sec_higher_sec": 0.32, "diploma_iti": 0.11, "grad_above": 0.03},
        "age_profile": {"age_15_29": 0.36, "age_30_44": 0.41, "age_45_59": 0.19, "age_60_plus": 0.04},
        "cyclicality": 0.10, # Festive surge (Q3/Q4)
        "covid_impact": -0.38 # Retail store closure shock
    }
]

# District sector affinity multipliers (reflecting actual industrial composition)
# e.g., Pune is heavy in Manufacturing and IT; Chennai is Auto and Healthcare; Kolkata is Trade and Textiles
affinity_map = {
    ("Pune", "Manufacturing"): 1.45,
    ("Pune", "Construction"): 1.10,
    ("Pune", "IT-ITeS"): 1.55,
    ("Pune", "Healthcare"): 1.05,
    ("Pune", "Textiles and apparel"): 0.70,
    
    ("Mumbai Suburban", "Manufacturing"): 0.90,
    ("Mumbai Suburban", "Construction"): 1.25,
    ("Mumbai Suburban", "IT-ITeS"): 1.40,
    ("Mumbai Suburban", "Healthcare"): 1.35,
    ("Mumbai Suburban", "Textiles and apparel"): 0.95,
    
    ("Thane", "Manufacturing"): 1.50,
    ("Thane", "Construction"): 1.30,
    ("Thane", "IT-ITeS"): 1.05,
    ("Thane", "Healthcare"): 1.10,
    ("Thane", "Textiles and apparel"): 1.15,
    
    ("Nagpur", "Manufacturing"): 1.15,
    ("Nagpur", "Construction"): 1.15,
    ("Nagpur", "IT-ITeS"): 0.85,
    ("Nagpur", "Healthcare"): 1.10,
    ("Nagpur", "Textiles and apparel"): 0.95,
    
    ("Chhatrapati Sambhajinagar", "Manufacturing"): 1.55,
    ("Chhatrapati Sambhajinagar", "Construction"): 0.95,
    ("Chhatrapati Sambhajinagar", "IT-ITeS"): 0.65,
    ("Chhatrapati Sambhajinagar", "Healthcare"): 0.85,
    ("Chhatrapati Sambhajinagar", "Textiles and apparel"): 1.35,
    
    ("Chennai", "Manufacturing"): 1.60, # Detroit of Asia
    ("Chennai", "Construction"): 1.15,
    ("Chennai", "IT-ITeS"): 1.45,
    ("Chennai", "Healthcare"): 1.65, # Health Capital of India
    ("Chennai", "Textiles and apparel"): 1.10,
    
    ("New Delhi", "Manufacturing"): 0.40,
    ("New Delhi", "Construction"): 0.75,
    ("New Delhi", "IT-ITeS"): 1.25,
    ("New Delhi", "Healthcare"): 1.30,
    ("New Delhi", "Textiles and apparel"): 0.60,
    
    ("South Delhi", "Manufacturing"): 0.60,
    ("South Delhi", "Construction"): 1.10,
    ("South Delhi", "IT-ITeS"): 1.50,
    ("South Delhi", "Healthcare"): 1.40,
    ("South Delhi", "Textiles and apparel"): 0.90,
    
    ("North Delhi", "Manufacturing"): 1.40,
    ("North Delhi", "Construction"): 1.15,
    ("North Delhi", "IT-ITeS"): 0.75,
    ("North Delhi", "Healthcare"): 0.90,
    ("North Delhi", "Textiles and apparel"): 1.25,
    
    ("Kolkata", "Manufacturing"): 0.95,
    ("Kolkata", "Construction"): 1.10,
    ("Kolkata", "IT-ITeS"): 1.20,
    ("Kolkata", "Healthcare"): 1.30,
    ("Kolkata", "Textiles and apparel"): 1.35,
    
    ("Howrah", "Manufacturing"): 1.65,
    ("Howrah", "Construction"): 1.10,
    ("Howrah", "IT-ITeS"): 0.50,
    ("Howrah", "Healthcare"): 0.80,
    ("Howrah", "Textiles and apparel"): 1.40,
}

# 3. Generate 10-Year Continuous Monthly Series (2016-01 to 2025-12 = 120 months)
months_list = pd.date_range(start="2016-01-01", end="2025-12-01", freq="MS")
total_months = len(months_list)
print(f"Generating continuous monthly series for {total_months} months across {len(geographies)} districts and {len(sectors)} sectors...")

monthly_records = []

for t_idx, dt in enumerate(months_list):
    year = dt.year
    month = dt.month
    period_month = dt.strftime("%Y-%m")
    quarter_num = (month - 1) // 3 + 1
    period_quarter = f"{year}Q{quarter_num}"
    
    # Macroeconomic & Event Multipliers
    # COVID-19 pandemic shock curve
    covid_factor = 0.0
    if year == 2020:
        if month in [3, 4, 5]: # Lockdown wave 1
            covid_factor = 1.0
        elif month in [6, 7, 8]:
            covid_factor = 0.65
        elif month in [9, 10, 11, 12]:
            covid_factor = 0.35
    elif year == 2021:
        if month in [4, 5, 6]: # Delta wave 2
            covid_factor = 0.75
        elif month in [7, 8, 9]:
            covid_factor = 0.30
        else:
            covid_factor = 0.15
    elif year == 2022 and month <= 2: # Omicron wave 3
        covid_factor = 0.10
        
    # Seasonal factors
    # Construction dips during monsoons (June-Sept)
    monsoon_factor = 1.0 if month in [6, 7, 8, 9] else 0.0
    # Festive hiring surge (Oct-Nov: Diwali, Durga Puja)
    festive_factor = 1.0 if month in [10, 11] else 0.0
    # Year-end corporate appraisals & IT hiring cycles (April-May & Oct-Nov)
    it_hiring_surge = 1.0 if month in [4, 5, 10] else 0.0

    for geo in geographies:
        d_name = geo["district_name"]
        s_name = geo["state_name"]
        s_code = geo["state_code"]
        
        # Population projected forward
        pop_k = geo["base_pop_k"] * ((1.0 + geo["pop_growth_rate"]) ** (t_idx / 12.0))
        # Working age population (15-64 years) is approx 66% in urban India
        working_age_pop_k = pop_k * 0.665
        
        # Base LFPR for urban district (~48% - 54% based on PLFS)
        base_lfpr = 0.505 + 0.015 * np.sin(2 * np.pi * t_idx / 12) + (0.003 * (year - 2016))
        # Total Labour Force in district
        total_labour_force_k = working_age_pop_k * base_lfpr

        for sec in sectors:
            sec_name = sec["sector_name"]
            affinity = affinity_map.get((d_name, sec_name), 1.0)
            
            # Baseline employment share of this sector in this district
            # Normalized so all sectors make realistic sense
            base_share_dict = {
                "Manufacturing": 0.18,
                "Construction": 0.14,
                "IT-ITeS": 0.12,
                "Healthcare": 0.08,
                "Textiles and apparel": 0.09
            }
            sector_share = base_share_dict[sec_name] * affinity
            
            # Trend growth per sector
            # IT-ITeS grew fast (~7-8% p.a.), Healthcare (~6%), Manufacturing (~4.5%), Construction (~4.2%), Textiles (~3.0%)
            growth_rates = {
                "Manufacturing": 0.048,
                "Construction": 0.044,
                "IT-ITeS": 0.078,
                "Healthcare": 0.065,
                "Textiles and apparel": 0.032
            }
            annual_g = growth_rates[sec_name]
            trend_multiplier = (1.0 + annual_g) ** (t_idx / 12.0)
            
            # Seasonal impact
            season_mult = 1.0
            if sec_name == "Construction":
                season_mult -= 0.18 * monsoon_factor
                season_mult += 0.06 * (1.0 - monsoon_factor)
            elif sec_name == "Textiles and apparel":
                season_mult += 0.12 * festive_factor
            elif sec_name == "IT-ITeS":
                season_mult += 0.05 * it_hiring_surge
            elif sec_name == "Manufacturing":
                season_mult += 0.04 * festive_factor - 0.03 * monsoon_factor
            elif sec_name == "Healthcare":
                season_mult += 0.03 * monsoon_factor # Monsoon ailments increase clinical intake
            
            # COVID Shock application
            shock_mult = 1.0 + (sec["covid_impact"] * covid_factor)
            
            # Stochastic macro noise (+/- 2%)
            noise = np.random.normal(1.0, 0.018)
            
            # Final Employed Workforce in sector
            employed_k = total_labour_force_k * sector_share * trend_multiplier * season_mult * shock_mult * noise
            employed_count = int(employed_k * 1000) # Exact integer headcount
            
            # Sector-specific Unemployment Rate (PLFS calibrated: ranges between 4.5% to 11.5%)
            # Construction & Textiles have higher frictional UR; IT & Healthcare lower
            base_ur = {
                "Manufacturing": 6.8,
                "Construction": 9.2,
                "IT-ITeS": 5.4,
                "Healthcare": 4.6,
                "Textiles and apparel": 8.1
            }[sec_name]
            
            # UR spiked during COVID
            ur_shock = covid_factor * (12.5 if sec["covid_impact"] < 0 else -1.2)
            unemployment_rate_pct = round(float(np.clip(base_ur + ur_shock + np.random.normal(0, 0.4), 2.8, 26.5)), 2)
            
            # WPR and LFPR
            wpr_pct = round(float(base_lfpr * (1.0 - unemployment_rate_pct / 100.0) * 100.0), 2)
            lfpr_pct = round(float(base_lfpr * 100.0), 2)
            
            # Gender Breakdown
            female_trend = 0.004 * (t_idx / 12.0) # Rising female labour force participation
            female_share = np.clip(sec["base_female_share"] + female_trend + np.random.normal(0, 0.005), 0.05, 0.70)
            male_share = 1.0 - female_share
            
            female_count = int(employed_count * female_share)
            male_count = employed_count - female_count
            
            female_pct = round(female_share * 100.0, 2)
            male_pct = round(male_share * 100.0, 2)
            
            # Age Group Breakdown (% and counts)
            age_p = sec["age_profile"]
            # Small random variation that still sums exactly to 100
            a1 = np.clip(age_p["age_15_29"] + np.random.normal(0, 0.008), 0.15, 0.60)
            a2 = np.clip(age_p["age_30_44"] + np.random.normal(0, 0.008), 0.20, 0.55)
            a3 = np.clip(age_p["age_45_59"] + np.random.normal(0, 0.006), 0.05, 0.35)
            a_sum = a1 + a2 + a3
            if a_sum >= 0.96:
                a1, a2, a3 = a1 * 0.95 / a_sum, a2 * 0.95 / a_sum, a3 * 0.95 / a_sum
            a4 = 1.0 - (a1 + a2 + a3)
            
            pct_age_15_29 = round(a1 * 100.0, 2)
            pct_age_30_44 = round(a2 * 100.0, 2)
            pct_age_45_59 = round(a3 * 100.0, 2)
            pct_age_60_plus = round(a4 * 100.0, 2)
            
            count_age_15_29 = int(employed_count * a1)
            count_age_30_44 = int(employed_count * a2)
            count_age_45_59 = int(employed_count * a3)
            count_age_60_plus = employed_count - (count_age_15_29 + count_age_30_44 + count_age_45_59)
            
            # Education Attainment Breakdown (% and counts)
            edu_p = sec["edu_profile"]
            e1 = np.clip(edu_p["below_sec"] + np.random.normal(0, 0.006), 0.01, 0.75)
            e2 = np.clip(edu_p["sec_higher_sec"] + np.random.normal(0, 0.006), 0.05, 0.50)
            e3 = np.clip(edu_p["diploma_iti"] + np.random.normal(0, 0.006), 0.05, 0.50)
            e_sum = e1 + e2 + e3
            if e_sum >= 0.98:
                e1, e2, e3 = e1 * 0.96 / e_sum, e2 * 0.96 / e_sum, e3 * 0.96 / e_sum
            e4 = 1.0 - (e1 + e2 + e3)
            
            pct_edu_below_sec = round(e1 * 100.0, 2)
            pct_edu_sec_higher_sec = round(e2 * 100.0, 2)
            pct_edu_diploma_iti = round(e3 * 100.0, 2)
            pct_edu_grad_above = round(e4 * 100.0, 2)
            
            count_edu_below_sec = int(employed_count * e1)
            count_edu_sec_higher_sec = int(employed_count * e2)
            count_edu_diploma_iti = int(employed_count * e3)
            count_edu_grad_above = employed_count - (count_edu_below_sec + count_edu_sec_higher_sec + count_edu_diploma_iti)
            
            # Wages (compounded nominal monthly earnings in INR)
            annual_wage_inflation = sec["wage_annual_growth"]
            compounded_wage = sec["base_wage_2016"] * ((1.0 + annual_wage_inflation) ** (t_idx / 12.0))
            # Metro district wage premium (Mumbai/Delhi/Pune/Chennai higher than Howrah/Aurangabad)
            metro_mult = 1.22 if d_name in ["Mumbai Suburban", "New Delhi", "South Delhi"] else (1.12 if d_name in ["Pune", "Chennai", "Thane"] else 1.0)
            avg_monthly_wage_inr = int(compounded_wage * metro_mult * np.random.normal(1.0, 0.012))
            
            # Vacancies / Employer Demand Index (0-100 scale, NCS & Naukri job postings proxy)
            base_vacancy = {
                "Manufacturing": 62.0,
                "Construction": 55.0,
                "IT-ITeS": 78.0,
                "Healthcare": 72.0,
                "Textiles and apparel": 48.0
            }[sec_name]
            vacancy_shock = (sec["covid_impact"] * 45.0 * covid_factor)
            vacancy_index = round(float(np.clip(base_vacancy + vacancy_shock + 6.0 * (t_idx / 120.0) + np.random.normal(0, 3.2), 15.0, 99.0)), 1)
            
            # Formal EPFO Net Payroll Additions (Monthly proxy)
            # Higher in IT & Manufacturing, lower in Construction
            epfo_rate = {"Manufacturing": 0.007, "Construction": 0.002, "IT-ITeS": 0.012, "Healthcare": 0.006, "Textiles and apparel": 0.004}[sec_name]
            net_epfo_payroll = int(max(0, employed_count * epfo_rate * (1.0 - 0.7 * covid_factor) * np.random.normal(1.0, 0.05)))
            
            # Training Supply Capacity (DGT/ITI sanctioned + PMKVY short-term certified cohort proxy)
            training_intensity = {"Manufacturing": 0.038, "Construction": 0.022, "IT-ITeS": 0.045, "Healthcare": 0.035, "Textiles and apparel": 0.028}[sec_name]
            annual_training_seats = int(employed_count * training_intensity)
            monthly_training_outturn = int(annual_training_seats / 12.0 * np.random.normal(1.0, 0.08))
            
            # Demand-Supply Mismatch Gap Index G in [-1, +1]
            # Derived from relative growth of vacancies vs training outturn
            demand_signal = (vacancy_index / 50.0)
            supply_signal = (monthly_training_outturn / (annual_training_seats / 12.0 + 1e-5))
            gap_raw = (demand_signal - supply_signal) / max(demand_signal, supply_signal)
            gap_index = round(float(np.clip(gap_raw * 0.45 + np.random.normal(0, 0.04), -0.85, 0.85)), 3)
            
            # Early-Warning Indicator status
            if gap_index > 0.35:
                skill_shortage_status = "Acute Shortage (High Demand)"
            elif gap_index > 0.10:
                skill_shortage_status = "Moderate Shortage"
            elif gap_index >= -0.15:
                skill_shortage_status = "Balanced Equilibrium"
            elif gap_index >= -0.40:
                skill_shortage_status = "Approaching Saturation"
            else:
                skill_shortage_status = "Acute Oversupply (Saturation)"

            monthly_records.append({
                "period_month": period_month,
                "period_quarter": period_quarter,
                "year": year,
                "month": month,
                "state_code": s_code,
                "state_name": s_name,
                "district_name": d_name,
                "district_type": geo["district_type"],
                "sector_name": sec_name,
                "nic_2008_div": sec["nic_2008_div"],
                "nco_family_code": sec["nco_family_code"],
                "nco_family_name": sec["nco_family_name"],
                "nco_secondary_code": sec["nco_secondary_code"],
                "nco_secondary_name": sec["nco_secondary_name"],
                
                # Core Labour & Economic Features
                "total_working_age_pop": int(working_age_pop_k * 1000),
                "employed_workforce_count": employed_count,
                "labour_force_participation_rate_pct": lfpr_pct,
                "worker_population_ratio_pct": wpr_pct,
                "unemployment_rate_pct": unemployment_rate_pct,
                "avg_monthly_wage_inr": avg_monthly_wage_inr,
                "active_job_vacancies_index": vacancy_index,
                "net_epfo_payroll_additions": net_epfo_payroll,
                "monthly_training_outturn_supply": monthly_training_outturn,
                "demand_supply_gap_index": gap_index,
                "skill_shortage_status": skill_shortage_status,
                
                # Gender Breakdown
                "male_workforce_pct": male_pct,
                "female_workforce_pct": female_pct,
                "male_employed_count": male_count,
                "female_employed_count": female_count,
                
                # Age Breakdown
                "pct_age_15_29_youth": pct_age_15_29,
                "pct_age_30_44_prime": pct_age_30_44,
                "pct_age_45_59_mature": pct_age_45_59,
                "pct_age_60_plus_senior": pct_age_60_plus,
                "count_age_15_29": count_age_15_29,
                "count_age_30_44": count_age_30_44,
                "count_age_45_59": count_age_45_59,
                "count_age_60_plus": count_age_60_plus,
                
                # Education Breakdown
                "pct_edu_below_secondary": pct_edu_below_sec,
                "pct_edu_secondary_higher_secondary": pct_edu_sec_higher_sec,
                "pct_edu_diploma_vocational_iti": pct_edu_diploma_iti,
                "pct_edu_graduate_and_above": pct_edu_grad_above,
                "count_edu_below_secondary": count_edu_below_sec,
                "count_edu_secondary_higher_secondary": count_edu_sec_higher_sec,
                "count_edu_diploma_vocational_iti": count_edu_diploma_iti,
                "count_edu_graduate_and_above": count_edu_grad_above
            })

df_monthly = pd.DataFrame(monthly_records)
print(f"Monthly DataFrame created: {df_monthly.shape[0]} rows, {df_monthly.shape[1]} columns.")

# Save Monthly CSV
monthly_csv_path = os.path.join(output_dir, "lmis_employment_monthly_2016_2025.csv")
df_monthly.to_csv(monthly_csv_path, index=False)
print(f"Saved monthly dataset to: {monthly_csv_path}")

# 4. Generate Quarterly Aggregation Dataset (2016Q1 to 2025Q4 = 40 continuous quarters)
# Group by period_quarter, state, district, sector
quarterly_records = []
q_groups = df_monthly.groupby(["period_quarter", "state_code", "state_name", "district_name", "sector_name"])

for (p_quarter, s_code, s_name, d_name, sec_name), group in q_groups:
    year = int(p_quarter[:4])
    quarter = int(p_quarter[-1])
    
    # Static metadata from group
    first_row = group.iloc[0]
    
    quarterly_records.append({
        "period_quarter": p_quarter,
        "year": year,
        "quarter": quarter,
        "state_code": s_code,
        "state_name": s_name,
        "district_name": d_name,
        "district_type": first_row["district_type"],
        "sector_name": sec_name,
        "nic_2008_div": first_row["nic_2008_div"],
        "nco_family_code": first_row["nco_family_code"],
        "nco_family_name": first_row["nco_family_name"],
        "nco_secondary_code": first_row["nco_secondary_code"],
        "nco_secondary_name": first_row["nco_secondary_name"],
        
        # Aggregated Metrics (Mean or Sum)
        "total_working_age_pop": int(group["total_working_age_pop"].mean()),
        "employed_workforce_count_q_avg": int(group["employed_workforce_count"].mean()),
        "labour_force_participation_rate_pct": round(group["labour_force_participation_rate_pct"].mean(), 2),
        "worker_population_ratio_pct": round(group["worker_population_ratio_pct"].mean(), 2),
        "unemployment_rate_pct": round(group["unemployment_rate_pct"].mean(), 2),
        "avg_monthly_wage_inr": int(group["avg_monthly_wage_inr"].mean()),
        "active_job_vacancies_index_q_avg": round(group["active_job_vacancies_index"].mean(), 1),
        "quarterly_total_net_epfo_payroll": int(group["net_epfo_payroll_additions"].sum()),
        "quarterly_training_outturn_supply": int(group["monthly_training_outturn_supply"].sum()),
        "demand_supply_gap_index": round(group["demand_supply_gap_index"].mean(), 3),
        "skill_shortage_status": group.iloc[-1]["skill_shortage_status"],
        
        # Gender Distribution
        "male_workforce_pct": round(group["male_workforce_pct"].mean(), 2),
        "female_workforce_pct": round(group["female_workforce_pct"].mean(), 2),
        "male_employed_count_q_avg": int(group["male_employed_count"].mean()),
        "female_employed_count_q_avg": int(group["female_employed_count"].mean()),
        
        # Age Distribution
        "pct_age_15_29_youth": round(group["pct_age_15_29_youth"].mean(), 2),
        "pct_age_30_44_prime": round(group["pct_age_30_44_prime"].mean(), 2),
        "pct_age_45_59_mature": round(group["pct_age_45_59_mature"].mean(), 2),
        "pct_age_60_plus_senior": round(group["pct_age_60_plus_senior"].mean(), 2),
        "count_age_15_29_q_avg": int(group["count_age_15_29"].mean()),
        "count_age_30_44_q_avg": int(group["count_age_30_44"].mean()),
        "count_age_45_59_q_avg": int(group["count_age_45_59"].mean()),
        "count_age_60_plus_q_avg": int(group["count_age_60_plus"].mean()),
        
        # Education Distribution
        "pct_edu_below_secondary": round(group["pct_edu_below_secondary"].mean(), 2),
        "pct_edu_secondary_higher_secondary": round(group["pct_edu_secondary_higher_secondary"].mean(), 2),
        "pct_edu_diploma_vocational_iti": round(group["pct_edu_diploma_vocational_iti"].mean(), 2),
        "pct_edu_graduate_and_above": round(group["pct_edu_graduate_and_above"].mean(), 2),
        "count_edu_below_secondary_q_avg": int(group["count_edu_below_secondary"].mean()),
        "count_edu_secondary_higher_secondary_q_avg": int(group["count_edu_secondary_higher_secondary"].mean()),
        "count_edu_diploma_vocational_iti_q_avg": int(group["count_edu_diploma_vocational_iti"].mean()),
        "count_edu_graduate_and_above_q_avg": int(group["count_edu_graduate_and_above"].mean())
    })

df_quarterly = pd.DataFrame(quarterly_records)
# Sort in chronological order
df_quarterly.sort_values(by=["period_quarter", "state_name", "district_name", "sector_name"], inplace=True)
print(f"Quarterly DataFrame created: {df_quarterly.shape[0]} rows, {df_quarterly.shape[1]} columns.")

# Save Quarterly CSV
quarterly_csv_path = os.path.join(output_dir, "lmis_employment_quarterly_2016_2025.csv")
df_quarterly.to_csv(quarterly_csv_path, index=False)
print(f"Saved quarterly dataset to: {quarterly_csv_path}")

# 5. Create State-Level Aggregated Dataset for fast macro-forecasting
state_monthly_records = []
state_groups = df_monthly.groupby(["period_month", "period_quarter", "year", "month", "state_code", "state_name", "sector_name"])

for (p_month, p_qtr, yr, mn, s_code, s_name, sec_name), grp in state_groups:
    first_r = grp.iloc[0]
    total_emp = grp["employed_workforce_count"].sum()
    male_emp = grp["male_employed_count"].sum()
    female_emp = grp["female_employed_count"].sum()
    
    state_monthly_records.append({
        "period_month": p_month,
        "period_quarter": p_qtr,
        "year": yr,
        "month": mn,
        "state_code": s_code,
        "state_name": s_name,
        "sector_name": sec_name,
        "nco_family_code": first_r["nco_family_code"],
        "nco_family_name": first_r["nco_family_name"],
        "total_employed_workforce": total_emp,
        "male_employed_count": male_emp,
        "female_employed_count": female_emp,
        "female_workforce_pct": round(female_emp / total_emp * 100.0, 2),
        "labour_force_participation_rate_pct": round(grp["labour_force_participation_rate_pct"].mean(), 2),
        "worker_population_ratio_pct": round(grp["worker_population_ratio_pct"].mean(), 2),
        "unemployment_rate_pct": round(grp["unemployment_rate_pct"].mean(), 2),
        "avg_monthly_wage_inr": int(grp["avg_monthly_wage_inr"].mean()),
        "active_job_vacancies_index": round(grp["active_job_vacancies_index"].mean(), 1),
        "net_epfo_payroll_additions": grp["net_epfo_payroll_additions"].sum(),
        "training_outturn_supply": grp["monthly_training_outturn_supply"].sum(),
        "demand_supply_gap_index": round(grp["demand_supply_gap_index"].mean(), 3),
        "count_age_15_29": grp["count_age_15_29"].sum(),
        "count_age_30_44": grp["count_age_30_44"].sum(),
        "count_age_45_59": grp["count_age_45_59"].sum(),
        "count_age_60_plus": grp["count_age_60_plus"].sum(),
        "count_edu_below_secondary": grp["count_edu_below_secondary"].sum(),
        "count_edu_secondary_higher_secondary": grp["count_edu_secondary_higher_secondary"].sum(),
        "count_edu_diploma_vocational_iti": grp["count_edu_diploma_vocational_iti"].sum(),
        "count_edu_graduate_and_above": grp["count_edu_graduate_and_above"].sum()
    })

df_state_monthly = pd.DataFrame(state_monthly_records)
state_monthly_csv_path = os.path.join(output_dir, "lmis_employment_state_monthly_2016_2025.csv")
df_state_monthly.to_csv(state_monthly_csv_path, index=False)
print(f"Saved state monthly dataset to: {state_monthly_csv_path}")

print("All datasets generated successfully!")
