#!/usr/bin/env python3
"""
Phase 2 - Data Collection: raw-data audit.

Catalogues the raw files (checksums, shapes), builds the data dictionary and runs acceptance checks on the
raw LMIS panel. It never modifies raw data and never reads anything under Archived/.

Writes:
    data/raw/DATA_MANIFEST.json            file inventory + checksums; written on first run, afterwards VERIFIED
                                           against (add --refresh-manifest to overwrite after an intentional change)
    docs/reference/DATA_DICTIONARY.csv     one row per column
    reports/phase2_raw_data_checks.json    PASS / WARN / FAIL results

Run:  python src/data_collection/validate_raw_data.py
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MONTHLY = RAW / "lmis_district_monthly_2011_2026.csv"
QUARTERLY = RAW / "lmis_district_quarterly_2011_2026.csv"
NCO_XLSX = RAW / "NCO-Codes.xlsx"
LEGACY_ROOT_COPY = ROOT / "lmis_employment_monthly_2016_2025.csv"   # duplicate of the archived dataset; off limits
EXPECTED = {"monthly": (53760, 39), "quarterly": (17920, 38)}
N_DISTRICTS, N_STATES, N_SECTORS, N_MONTHS, N_QUARTERS = 56, 4, 5, 192, 64
RATE_CAP = 0.42           # generator clips sector employment at 42% of the district labour force

DESCRIPTIONS = {
    "State_Name": ("key", "text", "State / UT name"),
    "State_LGD_Code": ("key", "text", "State LGD code (27, 33, 07, 19)"),
    "District_Name": ("key", "text", "District name"),
    "District_LGD_Code": ("key", "text", "District LGD code as supplied by the generator"),
    "District_Total_Population_Est": ("covariate", "persons", "Census-2011 population projected at the district growth rate"),
    "Timestamp": ("key", "YYYY-MM or YYYY-Qn", "Period identifier"),
    "Timestamp_Month": ("key", "YYYY-MM", "Month identifier (monthly file only)"),
    "Timestamp_Quarter": ("key", "YYYY-Qn", "Quarter identifier"),
    "Year": ("key", "year", "Calendar year"),
    "Month": ("key", "1-12", "Calendar month (monthly file only)"),
    "Quarter": ("key", "1-4", "Calendar quarter (quarterly file only)"),
    "Sector_Name": ("key", "text", "One of 5 target sectors"),
    "NIC_Code": ("key", "text", "NIC-2008 division range of the sector"),
    "NCO_Code": ("key", "NCO-2015 family", "Single NCO-2015 4-digit family assigned to the sector"),
    "NSQF_Level": ("key", "text", "NSQF level band of the sector"),
    "Male_Employed_Count": ("covariate", "persons", "Employed males"),
    "Female_Employed_Count": ("covariate", "persons", "Employed females"),
    "Transgender_Employed_Count": ("covariate", "persons", "Employed transgender persons"),
    "Male_Share_Pct": ("covariate", "%", "Male share of employment"),
    "Female_Share_Pct": ("covariate", "%", "Female share of employment"),
    "Transgender_Share_Pct": ("covariate", "%", "Transgender share of employment"),
    "Age_15_24_Count": ("covariate", "persons", "Employed aged 15-24"),
    "Age_25_54_Count": ("covariate", "persons", "Employed aged 25-54"),
    "Age_55_Plus_Count": ("covariate", "persons", "Employed aged 55+"),
    "Age_15_24_Pct": ("covariate", "%", "Share aged 15-24"),
    "Age_25_54_Pct": ("covariate", "%", "Share aged 25-54"),
    "Age_55_Plus_Pct": ("covariate", "%", "Share aged 55+"),
    "Edu_Below_Primary_Count": ("covariate", "persons", "Employed with below-primary education"),
    "Edu_Secondary_HigherSecondary_Count": ("covariate", "persons", "Employed with secondary / higher secondary"),
    "Qualification_Vocational_ITI_Certified_Count": ("covariate", "persons", "Employed with vocational / ITI certification"),
    "Edu_Graduate_and_Above_Count": ("covariate", "persons", "Employed graduates and above"),
    "Edu_Below_Primary_Pct": ("covariate", "%", "Share with below-primary education"),
    "Edu_Secondary_HigherSecondary_Pct": ("covariate", "%", "Share with secondary / higher secondary"),
    "Qualification_Vocational_ITI_Certified_Pct": ("covariate", "%", "Share with vocational / ITI certification"),
    "Edu_Graduate_and_Above_Pct": ("covariate", "%", "Share graduate and above"),
    "Active_Job_Vacancies": ("target", "openings", "Open job vacancies (demand signal)"),
    "Total_Employed_Workers": ("target", "persons", "Employed stock in the sector (demand outlook)"),
    "eShram_Registered_Seekers": ("target", "persons", "e-Shram registered seekers (supply proxy)"),
    "Avg_Monthly_Wage_INR": ("covariate", "INR / month", "Nominal average monthly wage"),
    "Unemployment_Rate_Pct": ("covariate", "%", "Sector unemployment rate (bounded 3.5-12)"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def nco_families(xlsx):
    """4-digit NCO-2015 families present in the reference workbook (stdlib parse; no openpyxl needed)."""
    z = zipfile.ZipFile(xlsx)
    shared = [re.sub(r"<[^>]+>", "", s) for s in
              re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf8"), flags=re.S)]
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf8")
    fams = {}
    for row in re.findall(r"<row [^>]*>(.*?)</row>", sheet, flags=re.S)[1:]:
        cells = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row, flags=re.S):
            col, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body or "")
            if v:
                cells[col] = shared[int(v.group(1))] if 't="s"' in attrs else v.group(1)
        if "C" in cells:
            fams[cells["C"][:4]] = cells.get("H", "")
    return fams


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, cid, name, status, detail):
        self.rows.append(dict(id=cid, check=name, status=status, detail=detail))
        print(f"[{status:4}] {cid} {name}: {detail}")


def main():
    for p in (MONTHLY, QUARTERLY, NCO_XLSX):
        assert p.exists(), f"missing {p}"
    assert "Archived" not in str(MONTHLY), "Archived data must not be used"
    c = Checks()
    as_of = pd.Timestamp.today().normalize()
    m = pd.read_csv(MONTHLY, dtype={"State_LGD_Code": str, "District_LGD_Code": str})
    q = pd.read_csv(QUARTERLY, dtype={"State_LGD_Code": str, "District_LGD_Code": str})

    # ---- manifest ---------------------------------------------------------------------------------------------
    files = {}
    for p, df in ((MONTHLY, m), (QUARTERLY, q), (NCO_XLSX, None)):
        files[p.name] = dict(path=str(p.relative_to(ROOT)).replace("\\", "/"), bytes=p.stat().st_size, sha256=sha256(p),
                             **({"rows": len(df), "columns": df.shape[1]} if df is not None else {}))
    manifest_path = RAW / "DATA_MANIFEST.json"
    if manifest_path.exists() and "--refresh-manifest" not in sys.argv:
        saved = json.load(open(manifest_path))["files"]
        changed = [n for n, f in files.items() if saved.get(n, {}).get("sha256") != f["sha256"]]
        c.add("C00", "raw files match recorded checksums", "PASS" if not changed else "FAIL",
              "all 3 files unchanged since manifest" if not changed else f"changed or new: {changed} "
              "(re-run with --refresh-manifest only if the change is intentional)")
    else:
        json.dump(dict(generated_on=str(as_of.date()),
                       source="synthetic - src/data_generation/generate_lmis_master_dataset.py (seed 42)",
                       files=files), open(manifest_path, "w"), indent=2)
        c.add("C00", "raw file manifest written", "PASS", f"{len(files)} files recorded in {manifest_path.name}")

    # ---- data dictionary --------------------------------------------------------------------------------------
    dd = []
    for col in m.columns:
        role, unit, desc = DESCRIPTIONS[col]
        num = pd.api.types.is_numeric_dtype(m[col])
        dd.append(dict(column=col, dtype=str(m[col].dtype), role=role, unit=unit, description=desc,
                       in_monthly=True, in_quarterly=col in q.columns, nulls=int(m[col].isna().sum()),
                       min=m[col].min() if num else "", max=m[col].max() if num else "",
                       n_unique=int(m[col].nunique())))
    for col in q.columns.difference(m.columns):
        role, unit, desc = DESCRIPTIONS[col]
        dd.append(dict(column=col, dtype=str(q[col].dtype), role=role, unit=unit, description=desc, in_monthly=False,
                       in_quarterly=True, nulls=int(q[col].isna().sum()), min=q[col].min(), max=q[col].max(),
                       n_unique=int(q[col].nunique())))
    pd.DataFrame(dd).to_csv(ROOT / "docs" / "reference" / "DATA_DICTIONARY.csv", index=False)

    # ---- checks -----------------------------------------------------------------------------------------------
    for name, df in (("monthly", m), ("quarterly", q)):
        ok = df.shape == EXPECTED[name]
        c.add(f"C01-{name[0]}", f"{name} shape", "PASS" if ok else "FAIL", f"{df.shape} (expected {EXPECTED[name]})")
        c.add(f"C02-{name[0]}", f"{name} nulls", "PASS" if df.isna().sum().sum() == 0 else "FAIL",
              f"{int(df.isna().sum().sum())} null cells")
        key = ["District_Name", "Sector_Name", "Timestamp"]
        dups = int(df.duplicated(key).sum())
        n_per = df.groupby(["District_Name", "Sector_Name"]).size()
        full = N_MONTHS if name == "monthly" else N_QUARTERS
        c.add(f"C03-{name[0]}", f"{name} unique keys + complete grid",
              "PASS" if dups == 0 and (n_per == full).all() and len(n_per) == N_DISTRICTS * N_SECTORS else "FAIL",
              f"{dups} duplicate keys; {len(n_per)} series, each {n_per.min()}-{n_per.max()} periods (expected {full})")

    c.add("C04", "geography / sector inventory",
          "PASS" if (m.District_Name.nunique(), m.State_Name.nunique(), m.Sector_Name.nunique()) == (N_DISTRICTS, N_STATES, N_SECTORS) else "FAIL",
          f"{m.District_Name.nunique()} districts, {m.State_Name.nunique()} states, {m.Sector_Name.nunique()} sectors")

    lgd = m[["District_Name", "District_LGD_Code"]].drop_duplicates()
    bad = lgd[~lgd.District_LGD_Code.str.fullmatch(r"\d{3}")]
    c.add("C05", "district LGD codes unique and numeric", "PASS" if lgd.District_LGD_Code.is_unique and bad.empty else "WARN",
          f"unique={lgd.District_LGD_Code.is_unique}; non-numeric: {dict(zip(bad.District_Name, bad.District_LGD_Code)) or 'none'}")

    g = m[["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"]].sum(axis=1) - m.Total_Employed_Workers
    a = m[["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"]].sum(axis=1) - m.Total_Employed_Workers
    e = m[["Edu_Below_Primary_Count", "Edu_Secondary_HigherSecondary_Count", "Qualification_Vocational_ITI_Certified_Count",
           "Edu_Graduate_and_Above_Count"]].sum(axis=1) - m.Total_Employed_Workers
    mx = int(max(g.abs().max(), a.abs().max(), e.abs().max()))
    c.add("C06", "gender / age / education counts sum to total", "PASS" if mx == 0 else "FAIL", f"max abs error = {mx}")

    shares = [m[[f"{p}_Pct" for p in grp]].sum(axis=1) for grp in
              (["Male_Share", "Female_Share", "Transgender_Share"], ["Age_15_24", "Age_25_54", "Age_55_Plus"],
               ["Edu_Below_Primary", "Edu_Secondary_HigherSecondary", "Qualification_Vocational_ITI_Certified",
                "Edu_Graduate_and_Above"])]
    worst = max(float((s - 100).abs().max()) for s in shares)
    c.add("C07", "share columns sum to 100%", "PASS" if worst <= 0.05 else "FAIL", f"max deviation = {worst:.3f} pp")

    num = m.select_dtypes("number").drop(columns=["Year", "Month"])
    c.add("C08", "no negative values; unemployment within 3.5-12%",
          "PASS" if (num >= 0).all().all() and m.Unemployment_Rate_Pct.between(3.5, 12).all() else "FAIL",
          f"min value {num.min().min():.2f}; UR range {m.Unemployment_Rate_Pct.min()}-{m.Unemployment_Rate_Pct.max()}")

    # monthly -> quarterly reconciliation (quarterly = truncated mean of the three months)
    mq = m.groupby(["District_Name", "Sector_Name", "Timestamp_Quarter"])[
        ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"]].mean()
    qq = q.set_index(["District_Name", "Sector_Name", "Timestamp_Quarter"])[mq.columns]
    diff = (mq - qq.loc[mq.index]).abs().max().max()
    c.add("C09", "quarterly file reconciles with monthly means", "PASS" if diff < 1 else "FAIL", f"max abs difference = {diff:.3f}")

    last = pd.Timestamp(m.Timestamp.max() + "-01")
    ahead = int(((pd.PeriodIndex(m.Timestamp.unique(), freq="M").to_timestamp()) > as_of).sum())
    c.add("C10", "history does not extend beyond today", "PASS" if ahead == 0 else "WARN",
          f"data ends {last:%Y-%m}; {ahead} month(s) lie after {as_of.date()} (simulated, not observed)")

    fams = nco_families(NCO_XLSX)
    sector_nco = m[["Sector_Name", "NCO_Code"]].drop_duplicates().assign(NCO_Code=lambda d: d.NCO_Code.astype(str))
    missing = {r.Sector_Name: r.NCO_Code for r in sector_nco.itertuples() if r.NCO_Code not in fams}
    c.add("C11", "sector NCO codes exist in NCO-2015 workbook", "PASS" if not missing else "FAIL",
          f"{len(sector_nco) - len(missing)}/{len(sector_nco)} found; not in NCO-2015: {missing or 'none'}")

    lf = m.District_Total_Population_Est * 0.665 * (0.505 + 0.002 * ((m.Year - 2011) * 12 + m.Month - 1) / 12
                                                    + 0.008 * np.sin(2 * np.pi * ((m.Year - 2011) * 12 + m.Month - 1) / 12))
    at_cap = (m.Total_Employed_Workers / lf) > RATE_CAP - 0.002
    by_sec = at_cap.groupby(m.Sector_Name).mean().round(3).to_dict()
    c.add("C12", "employment-rate cap not binding", "PASS" if at_cap.mean() < 0.01 else "WARN",
          f"{at_cap.mean():.1%} of rows sit at the 42% generator cap; by sector: {by_sec}")

    c.add("C13", "legacy dataset kept out of the pipeline", "WARN" if LEGACY_ROOT_COPY.exists() else "PASS",
          f"{LEGACY_ROOT_COPY.name} still in repo root (identical to Archived copy); not read by any script"
          if LEGACY_ROOT_COPY.exists() else "no legacy copy in repo root")

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    json.dump(dict(as_of=str(as_of.date()), summary={s: sum(r["status"] == s for r in c.rows) for s in ("PASS", "WARN", "FAIL")},
                   checks=c.rows), open(out / "phase2_raw_data_checks.json", "w"), indent=2)
    print("\nsummary:", {s: sum(r["status"] == s for r in c.rows) for s in ("PASS", "WARN", "FAIL")})


if __name__ == "__main__":
    main()
