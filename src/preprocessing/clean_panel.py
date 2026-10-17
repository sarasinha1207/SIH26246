#!/usr/bin/env python3
"""
Phase 3 - Data Cleaning & Preprocessing.

Turns the immutable raw panel (data/raw) into a typed, flagged, model-ready base table (data/processed).
Principles
  * Never alter an observed value.  Missing/duplicate/impossible values are checked and would be *removed or reported*,
    never imputed or winsorised; real shocks (COVID, policy, the e-Shram launch) are FLAGGED, not smoothed away.
  * No feature engineering here (lags, logs, scaling and encodings belong to Phase 5).
  * Time-ordered split roles are written into the table now, so later phases cannot leak the hold-out period.

Inputs : data/raw/lmis_district_monthly_2011_2026.csv, lmis_district_quarterly_2011_2026.csv, district_catalog.csv
Outputs: data/processed/panel_monthly.parquet, panel_quarterly.parquet, dim_sector.csv, dim_district.csv, dim_series.csv, SCHEMA.json
         docs/reference/PROCESSED_DATA_DICTIONARY.csv
         reports/phase3_cleaning_report.json, phase3_column_profile.csv, phase3_anomalies.csv

Run:  python src/preprocessing/clean_panel.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC, REPORTS = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "reports"

AS_OF = pd.Period("2026-10", "M")                 # last month that is not later than today's date (2026-10-18)
TRAIN_END, VALID_END = pd.Period("2023-12", "M"), pd.Period("2024-12", "M")
COVID = (pd.Period("2020-03", "M"), pd.Period("2022-02", "M"))
POLICY = [(pd.Period("2016-11", "M"), pd.Period("2017-01", "M")),      # demonetisation
          (pd.Period("2017-07", "M"), pd.Period("2017-10", "M"))]      # GST roll-out
ESHRAM_LAUNCH = pd.Period("2021-08", "M")
SECTOR_CODE = {"Manufacturing": "MFG", "Construction": "CON", "IT-ITeS": "ITS", "Healthcare": "HLT", "Textiles and Apparel": "TXT"}
DROP_RAW = ["Timestamp_Month", "NIC_Code", "NCO_Code", "NSQF_Level"]    # duplicate / constant-per-sector (kept in dim_sector)
MEASURES = ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Avg_Monthly_Wage_INR",
            "Unemployment_Rate_Pct"]
ANOMALY_Z = 6.0
LOW_VOLUME_VACANCIES = 50      # series whose median monthly vacancies over the last 24 training months are below this are 'low volume'
RAMP_GROWTH = 0.025        # sustained national seeker growth (3-month average, log points per month) that marks the e-Shram ramp
LGD_STR = {"State_LGD_Code": str, "District_LGD_Code": str}


class Log:
    def __init__(self):
        self.steps = []

    def add(self, step, action, **kw):
        self.steps.append(dict(step=step, action=action, **kw))
        print(f"- {step}: {action} " + " ".join(f"{k}={v}" for k, v in kw.items()))


def in_window(p, lo, hi):
    return (p >= lo) & (p <= hi)


def detect_eshram_ramp(monthly):
    """Data-driven e-Shram ramp: from the launch month until the 3-month average of national seeker growth first falls below
    RAMP_GROWTH (2.5% a month, ~8x the pre-launch median of 0.33%).  Later seasonal October bumps are not part of the contiguous run."""
    g = np.log(monthly.groupby("Period").eShram_Registered_Seekers.sum()).diff()
    pre = g[g.index < ESHRAM_LAUNCH]
    avg3 = g.rolling(3).mean()
    end, mean_growth = ESHRAM_LAUNCH, []
    for p, v in avg3[avg3.index >= ESHRAM_LAUNCH].items():       # contiguous run from launch only
        if v <= RAMP_GROWTH:
            break
        end = p
        mean_growth.append(v)
    return ESHRAM_LAUNCH, end, float(pre.median()), float(np.mean(mean_growth)) if mean_growth else 0.0


def anomaly_scan(df, explained_mask):
    """Unexplained statistical outliers: |z| > 6 against a centred 13-month rolling median per series, outside the
    COVID and policy-shock windows (those are real, explained events and are flagged separately)."""
    rows = []
    flag = pd.Series(False, index=df.index)
    keys = [df.Series_ID.values]
    for c in MEASURES:
        x = np.log(df[c]) if c != "Unemployment_Rate_Pct" else df[c].astype(float)
        grp = x.groupby(df.Series_ID, sort=False)
        resid = x - grp.transform(lambda v: v.rolling(13, center=True, min_periods=7).median())
        gr = resid.groupby(df.Series_ID, sort=False)
        sigma = gr.transform(lambda v: (v - v.median()).abs().median() * 1.4826).replace(0, np.nan)
        z = resid / sigma
        hit = (z.abs() > ANOMALY_Z) & ~explained_mask
        flag |= hit
        for i in df.index[hit]:
            rows.append(dict(Series_ID=df.at[i, "Series_ID"], Date=df.at[i, "Date"].date(), Measure=c,
                             Value=float(df.at[i, c]), Robust_Z=round(float(z[i]), 1)))
    return flag, pd.DataFrame(rows)


def common_flags(df, p_start, p_end, as_of_last):
    """Window flags for any period span [p_start, p_end] (a month, or a quarter's first/last month)."""
    ov = lambda lo, hi: (p_start <= hi) & (p_end >= lo)
    df["Is_Covid_Window"] = ov(*COVID)
    df["Is_Policy_Shock"] = np.logical_or.reduce([ov(lo, hi) for lo, hi in POLICY])
    df["Is_Simulated_Future"] = p_end > as_of_last
    return df


def split_role(p_end):
    return np.where(p_end <= TRAIN_END, "train", np.where(p_end <= VALID_END, "validation", "test"))


def main():
    PROC.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    log = Log()
    raw_m = pd.read_csv(RAW / "lmis_district_monthly_2011_2026.csv", dtype=LGD_STR)
    raw_q = pd.read_csv(RAW / "lmis_district_quarterly_2011_2026.csv", dtype=LGD_STR)
    cat = pd.read_csv(RAW / "district_catalog.csv", dtype=LGD_STR)
    n0 = len(raw_m)

    # ---- 1. integrity gates (nothing to repair is the expected result; any hit would stop the pipeline) -------------
    miss, dup = int(raw_m.isna().sum().sum()), int(raw_m.duplicated(["District_LGD_Code", "Sector_Name", "Timestamp"]).sum())
    neg = int((raw_m.select_dtypes("number").drop(columns=["Year", "Month"]) < 0).sum().sum())
    ident = int(max((raw_m[["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"]].sum(axis=1)
                     - raw_m.Total_Employed_Workers).abs().max(),
                    (raw_m[["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"]].sum(axis=1)
                     - raw_m.Total_Employed_Workers).abs().max()))
    log.add("integrity", "checked", missing=miss, duplicate_keys=dup, negative_values=neg, count_identity_errors=ident)
    assert miss == dup == neg == ident == 0, "raw data failed an integrity gate; do not proceed"

    # ---- 2. typing, keys, structure -----------------------------------------------------------------------------------
    m = raw_m.copy()
    m["Period"] = pd.PeriodIndex(m.Timestamp, freq="M")
    m["Date"] = m.Period.dt.to_timestamp()
    m["Sector_Code"] = m.Sector_Name.map(SECTOR_CODE)
    m["Series_ID"] = m.District_LGD_Code + "-" + m.Sector_Code
    m["Quarter_ID"] = m.Timestamp_Quarter
    m["Quarter"] = m.Period.dt.quarter
    m = m.merge(cat[["District_Name", "Econ_Tier"]], on="District_Name", how="left", validate="m:1")
    assert m.Econ_Tier.notna().all(), "district catalog join failed"
    log.add("typing/keys", "built Series_ID, Date, Sector_Code, Quarter_ID; joined Econ_Tier from district catalog",
            rows_before=n0, rows_after=len(m), series=m.Series_ID.nunique())

    # ---- 3. flags -----------------------------------------------------------------------------------------------------
    m = common_flags(m, m.Period, m.Period, AS_OF)
    ramp_lo, ramp_hi, med, sig = detect_eshram_ramp(m)
    m["Is_Eshram_Ramp"] = in_window(m.Period, ramp_lo, ramp_hi)
    log.add("structural breaks", "flagged (not smoothed)", covid=f"{COVID[0]}..{COVID[1]}",
            policy="2016-11..2017-01, 2017-07..2017-10", eshram_ramp=f"{ramp_lo}..{ramp_hi} (data-driven end)",
            simulated_future_months=int(m[m.Is_Simulated_Future].Period.nunique()))

    # ---- 4. anomaly scan ----------------------------------------------------------------------------------------------
    m = m.sort_values(["Series_ID", "Date"]).reset_index(drop=True)
    flag, anomalies = anomaly_scan(m, m.Is_Covid_Window | m.Is_Policy_Shock)
    m["Anomaly_Flag"] = flag
    by_measure = anomalies.groupby("Measure").size().to_dict() if len(anomalies) else {}
    log.add("anomaly scan", "flagged, retained (no winsorising/imputation)", rule=f"|robust z|>{ANOMALY_Z:g} vs 13-month median, outside covid/policy windows",
            rows_flagged=int(flag.sum()), share_pct=round(100 * flag.mean(), 3), by_measure=by_measure)

    # ---- 5. split roles (time-ordered; the test period is locked) ------------------------------------------------------
    m["Split_Role"] = split_role(m.Period)
    log.add("split", "assigned time-ordered roles", train="<=2023-12", validation="2024", test="2025-01..2026-12",
            counts=m.Split_Role.value_counts().to_dict())

    # ---- 6. final column order -------------------------------------------------------------------------------------
    meta = ["Series_ID", "Date", "Year", "Month", "Quarter", "Quarter_ID", "State_Name", "State_LGD_Code", "District_Name",
            "District_LGD_Code", "Econ_Tier", "Sector_Name", "Sector_Code"]
    flags = ["Is_Covid_Window", "Is_Policy_Shock", "Is_Eshram_Ramp", "Is_Simulated_Future", "Anomaly_Flag", "Split_Role"]
    measures = [c for c in raw_m.columns if c not in DROP_RAW + meta + ["Timestamp", "Timestamp_Quarter"]]
    clean_m = m[meta + measures + flags].copy()
    for c in ["State_Name", "State_LGD_Code", "District_Name", "District_LGD_Code", "Econ_Tier", "Sector_Name", "Sector_Code",
              "Quarter_ID", "Split_Role", "Series_ID"]:
        clean_m[c] = clean_m[c].astype("category")
    clean_m["Year"], clean_m["Month"], clean_m["Quarter"] = clean_m.Year.astype("int16"), clean_m.Month.astype("int8"), clean_m.Quarter.astype("int8")

    # value-preservation proof: every retained measure equals the raw value after re-aligning by key
    raw_idx = raw_m.set_index(["District_LGD_Code", "Sector_Name", "Timestamp"])
    chk = clean_m.assign(Timestamp=clean_m.Date.dt.strftime("%Y-%m")).set_index(["District_LGD_Code", "Sector_Name", "Timestamp"])
    changed = int(sum((chk[c].astype(raw_idx[c].dtype).values != raw_idx.loc[chk.index, c].values).sum() for c in measures))
    log.add("value preservation", "compared every retained measure with raw", values_modified=changed, columns_compared=len(measures))
    assert changed == 0

    # ---- 7. quarterly --------------------------------------------------------------------------------------------------
    q = raw_q.copy()
    q["Period"] = pd.PeriodIndex(q.Timestamp_Quarter, freq="Q")
    q["Quarter_Start"] = q.Period.dt.start_time
    q["Sector_Code"] = q.Sector_Name.map(SECTOR_CODE)
    q["Series_ID"] = q.District_LGD_Code + "-" + q.Sector_Code
    q = q.merge(cat[["District_Name", "Econ_Tier"]], on="District_Name", how="left", validate="m:1")
    q_first, q_last = q.Period.dt.asfreq("M", "s"), q.Period.dt.asfreq("M", "e")
    q = common_flags(q, q_first, q_last, AS_OF)
    q["Is_Eshram_Ramp"] = (q_first <= ramp_hi) & (q_last >= ramp_lo)
    q["Split_Role"] = split_role(q_last)
    anom_q = m.groupby(["Series_ID", "Quarter_ID"], observed=True).Anomaly_Flag.any().rename("Anomaly_Flag").reset_index()
    q = q.merge(anom_q, left_on=["Series_ID", "Timestamp_Quarter"], right_on=["Series_ID", "Quarter_ID"], how="left", validate="1:1")
    qmeta = ["Series_ID", "Quarter_Start", "Year", "Quarter", "Timestamp_Quarter", "State_Name", "State_LGD_Code", "District_Name",
             "District_LGD_Code", "Econ_Tier", "Sector_Name", "Sector_Code"]
    qmeas = [c for c in raw_q.columns if c not in DROP_RAW + qmeta + ["Timestamp"]]
    clean_q = q.sort_values(["Series_ID", "Quarter_Start"])[qmeta + qmeas + flags].reset_index(drop=True)
    for c in ["State_Name", "State_LGD_Code", "District_Name", "District_LGD_Code", "Econ_Tier", "Sector_Name", "Sector_Code",
              "Timestamp_Quarter", "Split_Role", "Series_ID"]:
        clean_q[c] = clean_q[c].astype("category")
    clean_q["Year"], clean_q["Quarter"] = clean_q.Year.astype("int16"), clean_q.Quarter.astype("int8")
    log.add("quarterly", "same typing/keys/flags applied", rows=len(clean_q), series=clean_q.Series_ID.nunique(),
            simulated_future_quarters=int(clean_q[clean_q.Is_Simulated_Future].Timestamp_Quarter.nunique()))

    # ---- 8. dimensions + write ---------------------------------------------------------------------------------------
    cw = pd.read_csv(RAW / "sector_nco_crosswalk.csv", dtype={"NCO_2015_Family": str})
    dim_sector = (raw_m[["Sector_Name", "NIC_Code", "NCO_Code", "NSQF_Level"]].drop_duplicates()
                  .assign(Sector_Code=lambda d: d.Sector_Name.map(SECTOR_CODE))
                  .rename(columns={"NCO_Code": "NCO_Anchor_Code"})
                  .merge(cw.groupby("Sector_Name").NCO_2015_Family.apply(";".join).rename("NCO_Families"), on="Sector_Name"))
    dim_sector.to_csv(PROC / "dim_sector.csv", index=False)
    cat.to_csv(PROC / "dim_district.csv", index=False)
    recent = clean_m[(clean_m.Split_Role == "train") & (clean_m.Date >= "2022-01-01")]
    dim_series = (recent.groupby("Series_ID", observed=True)
                  .agg(Train_Median_Employed=("Total_Employed_Workers", "median"), Train_Median_Vacancies=("Active_Job_Vacancies", "median"),
                       Train_Median_Seekers=("eShram_Registered_Seekers", "median")).reset_index())
    dim_series["Low_Volume"] = dim_series.Train_Median_Vacancies < LOW_VOLUME_VACANCIES
    ident = clean_m.drop_duplicates("Series_ID")[["Series_ID", "District_LGD_Code", "District_Name", "State_Name", "Econ_Tier",
                                                  "Sector_Code", "Sector_Name"]]
    dim_series = ident.merge(dim_series, on="Series_ID", validate="1:1")
    dim_series.to_csv(PROC / "dim_series.csv", index=False)
    log.add("series volume", "computed from the last 24 training months only (no validation/test data)",
            low_volume_series=int(dim_series.Low_Volume.sum()), rule=f"median vacancies < {LOW_VOLUME_VACANCIES}")

    raw_dd = pd.read_csv(ROOT / "docs" / "reference" / "DATA_DICTIONARY.csv").set_index("column")
    new_cols = {
        "Series_ID": ("key", "id", "N", "District LGD code + sector code; one id per district x sector series"),
        "Date": ("key", "date", "N", "First day of the month"),
        "Quarter_ID": ("key", "YYYY-Qn", "N", "Calendar quarter of the month (for aggregation)"),
        "Quarter_Start": ("key", "date", "N", "First day of the quarter (quarterly table only)"),
        "Econ_Tier": ("covariate", "category", "Y", "District economic tier from the district catalog (static)"),
        "Sector_Code": ("key", "id", "Y", "Short sector code (MFG, CON, ITS, HLT, TXT)"),
        "Is_Covid_Window": ("flag", "bool", "N", "2020-03..2022-02. Known in advance of nothing: use only to mask training windows"),
        "Is_Policy_Shock": ("flag", "bool", "N", "Demonetisation and GST windows; use to mask, not as a feature"),
        "Is_Eshram_Ramp": ("flag", "bool", "N", "e-Shram registration ramp (data-driven window)"),
        "Is_Simulated_Future": ("flag", "bool", "N", "Period after 2026-10 (simulated, not observed)"),
        "Anomaly_Flag": ("flag", "bool", "N", "DIAGNOSTIC ONLY: built from a centred window and full-sample scale, so using it as a feature would leak"),
        "Split_Role": ("flag", "category", "N", "train (<=2023-12) | validation (2024) | test (2025+, locked until Phase 8)"),
    }
    rows = []
    for c in list(clean_m.columns) + [x for x in clean_q.columns if x not in clean_m.columns]:
        if c in new_cols:
            role, unit, usable, desc = new_cols[c]
        else:
            role, unit, desc = raw_dd.at[c, "role"], raw_dd.at[c, "unit"], raw_dd.at[c, "description"]
            usable = "N" if role == "key" else "Y"
        usable = {"Month": "Y", "Quarter": "Y", "Year": "N", "State_LGD_Code": "N", "District_LGD_Code": "N",
                  "State_Name": "categorical", "District_Name": "categorical", "Sector_Name": "categorical",
                  "Sector_Code": "categorical", "Econ_Tier": "categorical", "Timestamp_Quarter": "N"}.get(c, usable)
        rows.append(dict(column=c, role=role, unit=unit, usable_as_model_input=usable, in_monthly=c in clean_m.columns,
                         in_quarterly=c in clean_q.columns, description=desc))
    pd.DataFrame(rows).to_csv(ROOT / "docs" / "reference" / "PROCESSED_DATA_DICTIONARY.csv", index=False)
    clean_m.to_parquet(PROC / "panel_monthly.parquet", index=False)
    clean_q.to_parquet(PROC / "panel_quarterly.parquet", index=False)

    # read-back gate
    back = pd.read_parquet(PROC / "panel_monthly.parquet")
    assert back.shape == clean_m.shape and back.Series_ID.nunique() == 280
    assert (back.groupby("Series_ID", observed=True).size() == 192).all()
    assert back.State_LGD_Code.astype(str).isin(["27", "33", "07", "19"]).all()

    # ---- 9. reports ---------------------------------------------------------------------------------------------------
    prof = []
    for c in clean_m.columns:
        s = clean_m[c]
        num = pd.api.types.is_numeric_dtype(s) and s.dtype != bool
        prof.append(dict(column=c, dtype=str(s.dtype), nulls=int(s.isna().sum()), n_unique=int(s.nunique()),
                         zeros=int((s == 0).sum()) if num else "", min=s.min() if num else "", max=s.max() if num else "",
                         skew=round(float(s.skew()), 2) if num and s.nunique() > 2 else ""))
    pd.DataFrame(prof).to_csv(REPORTS / "phase3_column_profile.csv", index=False)
    anomalies.to_csv(REPORTS / "phase3_anomalies.csv", index=False)
    schema = {"monthly": {c: str(t) for c, t in clean_m.dtypes.items()}, "quarterly": {c: str(t) for c, t in clean_q.dtypes.items()},
              "flags": {
                  "Is_Covid_Window": f"{COVID[0]}..{COVID[1]}", "Is_Policy_Shock": "demonetisation + GST windows",
                  "Is_Eshram_Ramp": f"{ramp_lo}..{ramp_hi}", "Is_Simulated_Future": f"periods after {AS_OF}",
                  "Anomaly_Flag": f"|robust z| > {ANOMALY_Z:g}, outside COVID and policy windows (diagnostic only: uses a centred window and full-sample scale, never a model input)", "Split_Role": "train<=2023-12 | validation 2024 | test 2025+"},
              "model_input_blocklist": flags + ["Series_ID", "Date", "Quarter_ID"],
              "notes": "Counts with zeros (Transgender, Edu_Below_Primary, Trainees_Certified) need log1p, not log, in Phase 5. Flags are for masking and reporting, never features."}
    json.dump(schema, open(PROC / "SCHEMA.json", "w"), indent=2)
    json.dump(dict(as_of=str(AS_OF), steps=log.steps,
                   outputs={"monthly": list(clean_m.shape), "quarterly": list(clean_q.shape)}),
              open(REPORTS / "phase3_cleaning_report.json", "w"), indent=2, default=str)
    print(f"\nmonthly {clean_m.shape}, quarterly {clean_q.shape}; wrote data/processed/ and reports/phase3_*")


if __name__ == "__main__":
    main()
