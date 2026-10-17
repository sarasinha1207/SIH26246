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
CATALOG = RAW / "district_catalog.csv"
CROSSWALK = RAW / "sector_nco_crosswalk.csv"
LEGACY_ROOT_COPY = ROOT / "lmis_employment_monthly_2016_2025.csv"   # duplicate of the archived dataset; off limits
EXPECTED = {"monthly": (53760, 41), "quarterly": (17920, 40)}
N_DISTRICTS, N_STATES, N_SECTORS, N_MONTHS, N_QUARTERS = 56, 4, 5, 192, 64

DESCRIPTIONS = {
    "State_Name": ("key", "text", "State / UT name"),
    "State_LGD_Code": ("key", "text", "State LGD code (27, 33, 07, 19)"),
    "District_Name": ("key", "text", "District name"),
    "District_LGD_Code": ("key", "text", "Official LGD district code (source in district_catalog.csv)"),
    "District_Total_Population_Est": ("covariate", "persons", "Census-2011 population projected at the district growth rate"),
    "Timestamp": ("key", "YYYY-MM or YYYY-Qn", "Period identifier"),
    "Timestamp_Month": ("key", "YYYY-MM", "Month identifier (monthly file only)"),
    "Timestamp_Quarter": ("key", "YYYY-Qn", "Quarter identifier"),
    "Year": ("key", "year", "Calendar year"),
    "Month": ("key", "1-12", "Calendar month (monthly file only)"),
    "Quarter": ("key", "1-4", "Calendar quarter (quarterly file only)"),
    "Sector_Name": ("key", "text", "One of 5 target sectors"),
    "NIC_Code": ("key", "text", "NIC-2008 division range of the sector (Manufacturing excludes textiles/apparel)"),
    "NCO_Code": ("key", "NCO-2015 family", "Anchor NCO-2015 4-digit family of the sector; full list in sector_nco_crosswalk.csv"),
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
    "eShram_Registered_Seekers": ("target", "persons",
                                  "Registered job-seeker / worker pool (supply proxy). Structural break at the Aug-2021 e-Shram launch"),
    "Avg_Monthly_Wage_INR": ("covariate", "INR / month", "Nominal average monthly wage"),
    "Unemployment_Rate_Pct": ("covariate", "%", "Sector unemployment rate (bounded 3.5-12)"),
    "Training_Seats_Sanctioned": ("supply-capacity", "seats / year",
                                  "Annual sanctioned formal skilling seats (ITI, diploma, short-term NSQF centres) for the sector in the district; constant within a financial year"),
    "Trainees_Certified_Monthly": ("supply-capacity", "persons / month", "Candidates certified in the month (training outturn)"),
    "Trainees_Certified_Quarterly": ("supply-capacity", "persons / quarter", "Candidates certified in the quarter (quarterly file only)"),
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


def fy_of(df):
    return np.where(df.Month >= 4, df.Year, df.Year - 1)


def main():
    for p in (MONTHLY, QUARTERLY, NCO_XLSX, CATALOG, CROSSWALK):
        assert p.exists(), f"missing {p}"
    assert "Archived" not in str(MONTHLY), "Archived data must not be used"
    c = Checks()
    as_of = pd.Timestamp.today().normalize()

    m = pd.read_csv(MONTHLY, dtype={"State_LGD_Code": str, "District_LGD_Code": str})
    q = pd.read_csv(QUARTERLY, dtype={"State_LGD_Code": str, "District_LGD_Code": str})

    # ---- manifest ---------------------------------------------------------------------------------------------
    files = {}
    for p, df in ((MONTHLY, m), (QUARTERLY, q), (NCO_XLSX, None), (CATALOG, None), (CROSSWALK, None)):
        files[p.name] = dict(path=str(p.relative_to(ROOT)).replace("\\", "/"), bytes=p.stat().st_size, sha256=sha256(p),
                             **({"rows": len(df), "columns": df.shape[1]} if df is not None else {}))
    manifest_path = RAW / "DATA_MANIFEST.json"
    if manifest_path.exists() and "--refresh-manifest" not in sys.argv:
        saved = json.load(open(manifest_path))["files"]
        changed = [n for n, f in files.items() if saved.get(n, {}).get("sha256") != f["sha256"]]
        c.add("C00", "raw files match recorded checksums", "PASS" if not changed else "FAIL",
              f"all {len(files)} files unchanged since manifest" if not changed else f"changed or new: {changed} "
              "(re-run with --refresh-manifest only if the change is intentional)")
    else:
        json.dump(dict(generated_on=str(as_of.date()),
                       source="synthetic - src/data_generation/generate_lmis_master_dataset.py v2 (seed 42)",
                       files=files), open(manifest_path, "w"), indent=2)
        c.add("C00", "raw file manifest written", "PASS", f"{len(files)} files recorded in {manifest_path.name}")

    # ---- data dictionary --------------------------------------------------------------------------------------
    dd = []
    for col in list(m.columns) + [x for x in q.columns if x not in m.columns]:
        src = m if col in m.columns else q
        role, unit, desc = DESCRIPTIONS[col]
        num = pd.api.types.is_numeric_dtype(src[col])
        dd.append(dict(column=col, dtype=str(src[col].dtype), role=role, unit=unit, description=desc,
                       in_monthly=col in m.columns, in_quarterly=col in q.columns, nulls=int(src[col].isna().sum()),
                       min=src[col].min() if num else "", max=src[col].max() if num else "", n_unique=int(src[col].nunique())))
    pd.DataFrame(dd).to_csv(ROOT / "docs" / "reference" / "DATA_DICTIONARY.csv", index=False)

    # ---- structure --------------------------------------------------------------------------------------------
    for name, df in (("monthly", m), ("quarterly", q)):
        ok = df.shape == EXPECTED[name]
        c.add(f"C01-{name[0]}", f"{name} shape", "PASS" if ok else "FAIL", f"{df.shape} (expected {EXPECTED[name]})")
        c.add(f"C02-{name[0]}", f"{name} nulls", "PASS" if df.isna().sum().sum() == 0 else "FAIL",
              f"{int(df.isna().sum().sum())} null cells")
        dups = int(df.duplicated(["District_Name", "Sector_Name", "Timestamp"]).sum())
        n_per = df.groupby(["District_Name", "Sector_Name"]).size()
        full = N_MONTHS if name == "monthly" else N_QUARTERS
        c.add(f"C03-{name[0]}", f"{name} unique keys + complete grid",
              "PASS" if dups == 0 and (n_per == full).all() and len(n_per) == N_DISTRICTS * N_SECTORS else "FAIL",
              f"{dups} duplicate keys; {len(n_per)} series, each {n_per.min()}-{n_per.max()} periods (expected {full})")

    c.add("C04", "geography / sector inventory",
          "PASS" if (m.District_Name.nunique(), m.State_Name.nunique(), m.Sector_Name.nunique()) == (N_DISTRICTS, N_STATES, N_SECTORS) else "FAIL",
          f"{m.District_Name.nunique()} districts, {m.State_Name.nunique()} states, {m.Sector_Name.nunique()} sectors")

    cat = pd.read_csv(CATALOG, dtype={"District_LGD_Code": str, "State_LGD_Code": str})
    lgd = m[["District_Name", "District_LGD_Code"]].drop_duplicates()
    merged = lgd.merge(cat[["District_Name", "District_LGD_Code"]], on="District_Name", suffixes=("", "_cat"))
    bad = lgd[~lgd.District_LGD_Code.str.fullmatch(r"\d{2,3}")]
    c.add("C05", "district LGD codes unique, numeric and match the catalog",
          "PASS" if lgd.District_LGD_Code.is_unique and bad.empty and (merged.District_LGD_Code == merged.District_LGD_Code_cat).all() else "FAIL",
          f"unique={lgd.District_LGD_Code.is_unique}; non-numeric={len(bad)}; sources: {cat.LGD_Code_Source.value_counts().to_dict()}")

    # ---- internal consistency ---------------------------------------------------------------------------------
    g = m[["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"]].sum(axis=1) - m.Total_Employed_Workers
    a = m[["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"]].sum(axis=1) - m.Total_Employed_Workers
    e = m[["Edu_Below_Primary_Count", "Edu_Secondary_HigherSecondary_Count", "Qualification_Vocational_ITI_Certified_Count",
           "Edu_Graduate_and_Above_Count"]].sum(axis=1) - m.Total_Employed_Workers
    mx = int(max(g.abs().max(), a.abs().max(), e.abs().max()))
    c.add("C06", "gender / age / education counts sum to total", "PASS" if mx == 0 else "FAIL", f"max abs error = {mx}")

    shares = [m[[f"{p}_Pct" for p in grp]].sum(axis=1) for grp in
              (["Male_Share", "Female_Share", "Transgender_Share"], ["Age_15_24", "Age_25_54", "Age_55_Plus"],
               ["Edu_Below_Primary", "Edu_Secondary_HigherSecondary", "Qualification_Vocational_ITI_Certified", "Edu_Graduate_and_Above"])]
    worst = max(float((s - 100).abs().max()) for s in shares)
    c.add("C07", "share columns sum to 100%", "PASS" if worst <= 0.05 else "FAIL", f"max deviation = {worst:.3f} pp")

    eq = q.Total_Employed_Workers
    q_err = int(max((q[cols].sum(axis=1) - eq).abs().max() for cols in (
        ["Male_Employed_Count", "Female_Employed_Count", "Transgender_Employed_Count"],
        ["Age_15_24_Count", "Age_25_54_Count", "Age_55_Plus_Count"],
        ["Edu_Below_Primary_Count", "Edu_Secondary_HigherSecondary_Count", "Qualification_Vocational_ITI_Certified_Count",
         "Edu_Graduate_and_Above_Count"])))
    q_dev = float((q[["Male_Share_Pct", "Female_Share_Pct", "Transgender_Share_Pct"]].sum(axis=1) - 100).abs().max())
    c.add("C07q", "quarterly counts sum to total and shares to 100%", "PASS" if q_err == 0 and q_dev <= 0.05 else "FAIL",
          f"max count error = {q_err}; max share deviation = {q_dev:.3f} pp")

    num = m.select_dtypes("number").drop(columns=["Year", "Month"])
    c.add("C08", "no negative values; unemployment within 3.5-12%",
          "PASS" if (num >= 0).all().all() and m.Unemployment_Rate_Pct.between(3.5, 12).all() else "FAIL",
          f"min value {num.min().min():.2f}; UR range {m.Unemployment_Rate_Pct.min()}-{m.Unemployment_Rate_Pct.max()}")

    mq = m.groupby(["District_Name", "Sector_Name", "Timestamp_Quarter"])[
        ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Training_Seats_Sanctioned"]].mean()
    qq = q.set_index(["District_Name", "Sector_Name", "Timestamp_Quarter"])
    diff = (mq - qq.loc[mq.index, mq.columns]).abs().max().max()
    c.add("C09", "quarterly file reconciles with monthly means", "PASS" if diff < 1 else "FAIL", f"max abs difference = {diff:.3f}")

    last = pd.Timestamp(m.Timestamp.max() + "-01")
    ahead = int(((pd.PeriodIndex(m.Timestamp.unique(), freq="M").to_timestamp()) > as_of).sum())
    c.add("C10", "history does not extend beyond today", "PASS" if ahead == 0 else "WARN",
          f"data ends {last:%Y-%m}; {ahead} month(s) lie after {as_of.date()} (simulated, not observed)")

    # ---- taxonomy ---------------------------------------------------------------------------------------------
    fams = nco_families(NCO_XLSX)
    cw = pd.read_csv(CROSSWALK, dtype={"NCO_2015_Family": str})
    miss = cw[~cw.NCO_2015_Family.isin(fams)]
    wrong_title = cw[cw.NCO_2015_Family.isin(fams) & (cw.NCO_2015_Family.map(fams) != cw.NCO_2015_Title)]
    anchors = cw[cw.Is_Anchor_Code].set_index("Sector_Name").NCO_2015_Family
    anchor_ok = all(str(r.NCO_Code) == anchors[r.Sector_Name] for r in m[["Sector_Name", "NCO_Code"]].drop_duplicates().itertuples())
    c.add("C11", "NCO codes exist in NCO-2015 workbook (anchor + crosswalk)",
          "PASS" if miss.empty and wrong_title.empty and anchor_ok else "FAIL",
          f"{len(cw) - len(miss)}/{len(cw)} crosswalk families found; title mismatches={len(wrong_title)}; anchors match data={anchor_ok}")

    # ---- calibration against the spec --------------------------------------------------------------------------
    nat = m.groupby(["Sector_Name", "Timestamp"])[["Total_Employed_Workers", "Active_Job_Vacancies"]].sum()

    def chg(col, sec):
        return 100 * (nat.loc[(sec, "2020-04"), col] / nat.loc[(sec, "2020-02"), col] - 1)

    spec = {"Construction": -52, "Manufacturing": -38, "Textiles and Apparel": -42}
    dev = {k: round(float(chg("Total_Employed_Workers", k)), 1) for k in spec}
    hv, itv = chg("Active_Job_Vacancies", "Healthcare"), chg("Active_Job_Vacancies", "IT-ITeS")
    ok = all(abs(dev[k] - v) <= 5 for k, v in spec.items()) and 36 <= hv <= 52 and 5 <= itv <= 20
    c.add("C12", "COVID shock matches spec", "PASS" if ok else "FAIL",
          f"employment {dev} (spec {spec}); vacancies Healthcare {hv:+.1f}% (spec +44), IT-ITeS {itv:+.1f}% (spec +12)")

    y25 = m[m.Year == 2025]
    dens = (y25.Total_Employed_Workers / y25.District_Total_Population_Est).groupby([y25.Sector_Name, y25.District_Name]).mean().unstack(0)
    hubs = ["Pune", "Mumbai Suburban", "Chennai", "South Delhi", "North 24 Parganas"]
    peri = ["Gadchiroli", "Nandurbar", "Washim"]
    ratio = (dens.loc[hubs].mean() / dens.loc[peri].mean()).round(1)
    mf = ratio["Manufacturing"]
    c.add("C13", "hub / peripheral per-capita density 4-8x (Manufacturing)", "PASS" if 4 <= mf <= 8 else "FAIL",
          f"Manufacturing {mf}x; others {ratio.drop('Manufacturing').to_dict()}")
    c.add("C13b", "IT-ITeS disparity vs the 4-8x spec", "WARN" if ratio["IT-ITeS"] > 8 else "PASS",
          f"{ratio['IT-ITeS']}x - documented deviation: real IT concentration is far steeper than 8x")

    fem = m.groupby("Sector_Name").Female_Share_Pct.mean()
    bands = {"Manufacturing": (15, 20), "Construction": (10, 15), "IT-ITeS": (32, 38), "Healthcare": (45, 52), "Textiles and Apparel": (40, 48)}
    it_grad = m[m.Sector_Name == "IT-ITeS"].Edu_Graduate_and_Above_Pct
    c.add("C14", "female share bands; IT-ITeS graduate share > 80% in every row",
          "PASS" if all(bands[k][0] <= fem[k] <= bands[k][1] for k in bands) and it_grad.min() > 80 else "FAIL",
          f"female {fem.round(1).to_dict()}; IT graduates mean {it_grad.mean():.1f}%, row minimum {it_grad.min():.1f}%")

    mix = (m.groupby(["Timestamp", "District_Name"]).Total_Employed_Workers.sum()
           / (m.drop_duplicates(["Timestamp", "District_Name"]).set_index(["Timestamp", "District_Name"]).District_Total_Population_Est * 0.665))
    at_bound = float(m.Unemployment_Rate_Pct.isin([3.5, 12.0]).mean())
    cnt_cols = ["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers", "Training_Seats_Sanctioned"]
    on_floor = int((m[cnt_cols] <= 1).sum().sum())
    c.add("C15", "no clipping artefacts", "PASS" if mix.max() < 0.45 and at_bound < 0.02 and on_floor == 0 else "FAIL",
          f"max five-sector employment = {mix.max():.1%} of working-age population; {at_bound:.1%} of unemployment values at the "
          f"3.5/12.0 bounds; {on_floor} count values on the generator's minimum of 1")

    cov = (y25.Active_Job_Vacancies / y25.eShram_Registered_Seekers).groupby([y25.Sector_Name, y25.District_Name]).mean().unstack(0)
    spread = np.log(cov).std().round(2)
    c.add("C16", "district-level variation in vacancy/seeker coverage within each sector", "PASS" if (spread > 0.15).all() else "FAIL",
          f"std of log coverage across districts: {spread.to_dict()}")

    fy = pd.Series(fy_of(m), index=m.index, name="FY")
    grp = m.groupby(["District_Name", "Sector_Name", fy])
    seats_const = bool((grp.Training_Seats_Sanctioned.nunique() == 1).all())
    full = grp.agg(seats=("Training_Seats_Sanctioned", "first"), cert=("Trainees_Certified_Monthly", "sum"), n=("Month", "size"))
    full = full[full.n == 12]
    cert_ok = bool((full.cert <= full.seats).all())
    c.add("C17", "training capacity columns coherent", "PASS" if seats_const and cert_ok else "FAIL",
          f"seats constant within financial year={seats_const}; certified <= seats in every full FY={cert_ok}")
    mq2 = m.groupby(["District_Name", "Sector_Name", "Timestamp_Quarter"]).Trainees_Certified_Monthly.sum()
    match = bool((qq.Trainees_Certified_Quarterly.loc[mq2.index] == mq2).all())
    c.add("C18", "quarterly certified = sum of monthly", "PASS" if match else "FAIL", "exact match" if match else "mismatch")

    ms = m.sort_values(["District_Name", "Sector_Name", "Timestamp"])
    jump = ms.groupby(["District_Name", "Sector_Name"]).eShram_Registered_Seekers.pct_change().abs() > 0.25
    j11, jref = int(jump[ms.Year == 2011].sum()), float(jump[(ms.Year >= 2012) & (ms.Year <= 2019)].groupby(ms.Year).sum().mean())
    c.add("C20", "no start-up transient in 2011 (seekers month-on-month jumps > 25%)", "PASS" if j11 <= 2 * max(jref, 1) else "FAIL",
          f"{j11} jumps in 2011 vs {jref:.1f} per year in 2012-2019")

    c.add("C19", "legacy dataset kept out of the pipeline", "WARN" if LEGACY_ROOT_COPY.exists() else "PASS",
          f"{LEGACY_ROOT_COPY.name} still in repo root (identical to Archived copy); not read by any script"
          if LEGACY_ROOT_COPY.exists() else "no legacy copy in repo root")

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    summary = {s: sum(r["status"] == s for r in c.rows) for s in ("PASS", "WARN", "FAIL")}
    json.dump(dict(as_of=str(as_of.date()), summary=summary, checks=c.rows), open(out / "phase2_raw_data_checks.json", "w"), indent=2)
    print("\nsummary:", summary)


if __name__ == "__main__":
    main()
