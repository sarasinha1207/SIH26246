"""Phase 3 acceptance tests for data/processed.  Runs under pytest, or standalone: python tests/test_processed_panel.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
LGD = {"State_LGD_Code": str, "District_LGD_Code": str}

monthly = pd.read_parquet(PROC / "panel_monthly.parquet")
quarterly = pd.read_parquet(PROC / "panel_quarterly.parquet")
raw_m = pd.read_csv(RAW / "lmis_district_monthly_2011_2026.csv", dtype=LGD)


def test_raw_data_is_untouched():
    manifest = json.load(open(RAW / "DATA_MANIFEST.json"))["files"]
    for name, meta in manifest.items():
        h = hashlib.sha256((RAW / name).read_bytes()).hexdigest()
        assert h == meta["sha256"], f"{name} changed since the Phase 2 manifest"


def test_shape_keys_and_order():
    assert monthly.shape[0] == 53760 and quarterly.shape[0] == 17920
    assert monthly.Series_ID.nunique() == 280 and quarterly.Series_ID.nunique() == 280
    assert not monthly.duplicated(["Series_ID", "Date"]).any()
    assert not quarterly.duplicated(["Series_ID", "Quarter_Start"]).any()
    assert (monthly.groupby("Series_ID", observed=True).size() == 192).all()
    assert (quarterly.groupby("Series_ID", observed=True).size() == 64).all()
    for df, col in ((monthly, "Date"), (quarterly, "Quarter_Start")):
        assert df.groupby("Series_ID", observed=True)[col].apply(lambda s: s.is_monotonic_increasing).all()


def test_ids_keep_leading_zeros_and_no_nulls():
    assert set(monthly.State_LGD_Code.astype(str)) == {"27", "33", "07", "19"}
    assert monthly.isna().sum().sum() == 0 and quarterly.isna().sum().sum() == 0


def test_no_value_was_modified():
    key = ["District_LGD_Code", "Sector_Name"]
    a = monthly.assign(Timestamp=monthly.Date.dt.strftime("%Y-%m")).astype({"District_LGD_Code": str, "Sector_Name": str})
    a = a.set_index(key + ["Timestamp"]).sort_index()
    b = raw_m.set_index(key + ["Timestamp"]).sort_index()
    assert a.index.equals(b.index)
    for c in a.columns.intersection(b.columns):
        if pd.api.types.is_numeric_dtype(b[c]):
            assert np.array_equal(a[c].to_numpy(dtype=float), b[c].to_numpy(dtype=float)), f"{c} differs from raw"


def test_count_identities_hold():
    emp = monthly.Total_Employed_Workers
    for cols in (["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"],
                 ["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"],
                 ["Edu_Below_Primary_Count", "Edu_Secondary_HigherSecondary_Count",
                  "Qualification_Vocational_ITI_Certified_Count", "Edu_Graduate_and_Above_Count"]):
        assert (monthly[cols].sum(axis=1) == emp).all()


def test_split_roles_are_time_ordered_and_locked():
    r = monthly.groupby("Split_Role", observed=True).Date.agg(["min", "max"])
    assert r.loc["train", "max"] == pd.Timestamp("2023-12-01")
    assert r.loc["validation", "min"] == pd.Timestamp("2024-01-01") and r.loc["validation", "max"] == pd.Timestamp("2024-12-01")
    assert r.loc["test", "min"] == pd.Timestamp("2025-01-01") and r.loc["test", "max"] == pd.Timestamp("2026-12-01")
    qr = quarterly.groupby("Split_Role", observed=True).Quarter_Start.agg(["min", "max"])
    assert qr.loc["train", "max"] == pd.Timestamp("2023-10-01") and qr.loc["test", "min"] == pd.Timestamp("2025-01-01")


def test_flag_windows():
    span = lambda f: (monthly[monthly[f]].Date.min().strftime("%Y-%m"), monthly[monthly[f]].Date.max().strftime("%Y-%m"))
    assert span("Is_Covid_Window") == ("2020-03", "2022-02")
    assert span("Is_Policy_Shock") == ("2016-11", "2017-10")
    assert span("Is_Simulated_Future") == ("2026-11", "2026-12")
    lo, hi = span("Is_Eshram_Ramp")
    assert lo == "2021-08" and "2022-06" <= hi <= "2023-06"
    assert quarterly[quarterly.Is_Simulated_Future].Timestamp_Quarter.astype(str).unique().tolist() == ["2026-Q4"]


def test_monthly_quarterly_reconcile():
    q = monthly.groupby(["Series_ID", "Quarter_ID"], observed=True)[["Total_Employed_Workers", "Active_Job_Vacancies"]].mean()
    qq = quarterly.set_index(["Series_ID", "Timestamp_Quarter"])[q.columns]
    assert (q - qq.loc[q.index]).abs().max().max() < 1


def test_dimensions_join():
    dd, ds = pd.read_csv(PROC / "dim_district.csv", dtype=LGD), pd.read_csv(PROC / "dim_sector.csv")
    assert len(dd) == 56 and len(ds) == 5 and ds.NCO_Families.str.count(";").eq(4).all()
    assert monthly.Econ_Tier.notna().all() and set(monthly.Econ_Tier.astype(str)) == set(dd.Econ_Tier)


def test_schema_file_matches_tables():
    sch = json.load(open(PROC / "SCHEMA.json"))
    assert list(sch["monthly"]) == list(monthly.columns) and list(sch["quarterly"]) == list(quarterly.columns)


def test_quarterly_identities_and_shares():
    e = quarterly.Total_Employed_Workers
    for cols in (["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"],
                 ["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"],
                 ["Edu_Below_Primary_Count", "Edu_Secondary_HigherSecondary_Count",
                  "Qualification_Vocational_ITI_Certified_Count", "Edu_Graduate_and_Above_Count"]):
        assert (quarterly[cols].sum(axis=1) == e).all()
    assert ((quarterly[["Male_Share_Pct", "Female_Share_Pct", "Transgender_Share_Pct"]].sum(axis=1) - 100).abs() <= 0.05).all()


def test_quarterly_flags_equal_any_month():
    flags = ["Is_Covid_Window", "Is_Policy_Shock", "Is_Eshram_Ramp", "Is_Simulated_Future", "Anomaly_Flag"]
    mm = monthly.groupby(["Series_ID", "Quarter_ID"], observed=True)[flags].any().reset_index()
    qq = quarterly.merge(mm, left_on=["Series_ID", "Timestamp_Quarter"], right_on=["Series_ID", "Quarter_ID"], suffixes=("", "_m"))
    assert len(qq) == len(quarterly)
    for f in flags:
        assert (qq[f] == qq[f + "_m"]).all(), f


def test_test_period_is_locked_in_the_access_helper():
    sys.path.insert(0, str(ROOT / "src" / "common"))
    from data_access import load_panel
    df = load_panel("monthly")
    assert set(df.Split_Role.astype(str)) == {"train", "validation"} and df.Date.max() == pd.Timestamp("2024-12-01")
    try:
        load_panel("monthly", roles=("train", "test"))
        raise AssertionError("test rows were returned without unlock_test")
    except PermissionError:
        pass
    assert load_panel("quarterly", roles=("test",), unlock_test=True).Quarter_Start.min() == pd.Timestamp("2025-01-01")
    clean = load_panel("monthly", drop_blocklisted=True)
    assert not {"Anomaly_Flag", "Split_Role", "Series_ID", "Date", "Is_Covid_Window"} & set(clean.columns)


def test_series_dimension_uses_training_data_only():
    ds = pd.read_csv(PROC / "dim_series.csv", dtype={"District_LGD_Code": str})
    assert len(ds) == 280 and ds.Series_ID.is_unique and ds.Low_Volume.dtype == bool
    recent = monthly[(monthly.Split_Role == "train") & (monthly.Date >= "2022-01-01")]
    expect = recent.groupby("Series_ID", observed=True).Active_Job_Vacancies.median()
    assert np.allclose(ds.set_index("Series_ID").Train_Median_Vacancies.loc[expect.index], expect)
    assert ds.Low_Volume.sum() == (expect < 50).sum()


def test_processed_dictionary_covers_every_column():
    dd = pd.read_csv(ROOT / "docs" / "reference" / "PROCESSED_DATA_DICTIONARY.csv")
    assert set(monthly.columns) | set(quarterly.columns) == set(dd.column)
    assert dd.description.notna().all() and set(dd.usable_as_model_input) <= {"Y", "N", "categorical"}
    assert (dd[dd.role == "flag"].usable_as_model_input == "N").all()


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
