"""Dashboard data pack tests. Runs under pytest or standalone: python tests/test_dashboard_pack.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data" / "dashboard"
M = pd.read_csv(PACK / "monthly_metrics_2011_2024.csv", dtype={"district_lgd_code": str})
MAN = json.load(open(PACK / "data_pack_manifest.json"))


def test_pack_excludes_the_locked_and_simulated_months():
    assert M.Date.min() == "2011-01-01" and M.Date.max() == "2024-12-01" and len(M) == 47040 == MAN["rows"]


def test_pack_shape_and_keys():
    assert M.state.nunique() == 4 and M.district.nunique() == 56 and M.sector.nunique() == 5 and M.Series_ID.nunique() == 280
    assert not M.duplicated(["Series_ID", "Date"]).any()
    dd = pd.read_csv(PACK / "dim_district.csv", dtype=str)
    assert len(dd) == 56 and dd.groupby("state").size().to_dict() == {"Delhi": 11, "Maharashtra": 36, "Tamil Nadu": 4, "West Bengal": 5}
    assert set(dd.district_lgd_code) == set(M.district_lgd_code)
    assert len(pd.read_csv(PACK / "dim_sector.csv")) == 5


def test_pack_matches_the_processed_panel():
    sys.path.insert(0, str(ROOT / "src" / "common"))
    from data_access import load_panel
    p = load_panel("monthly")
    p["Series_ID"] = p.Series_ID.astype(str)
    a = M.assign(Date=pd.to_datetime(M.Date)).set_index(["Series_ID", "Date"]).sort_index()
    b = p.set_index(["Series_ID", "Date"]).sort_index()
    assert a.index.equals(b.index)
    for mine, theirs in (("employed", "Total_Employed_Workers"), ("vacancies", "Active_Job_Vacancies"), ("registered_seekers", "eShram_Registered_Seekers")):
        assert np.array_equal(a[mine].to_numpy(), b[theirs].to_numpy())
    assert np.array_equal(a.net_gap_persons.to_numpy(), (b.Active_Job_Vacancies - b.eShram_Registered_Seekers).to_numpy())


def test_relative_flags_are_in_range():
    ok = M.relative_status.notna() & (M.relative_status != "")
    assert set(M.relative_status[ok].unique()) <= set(MAN["relative_status_values"])
    pc = M.coverage_percentile_in_sector.dropna()
    assert pc.min() > 0 and pc.max() < 100
    assert set(M.absolute_context.dropna().unique()) - {""} <= {"openings exceed seekers", "moderate", "oversupplied", "deep surplus"}
    assert M[M.Date >= "2012-01-01"].relative_status.notna().all()


def test_brief_headline_numbers_match_the_pack():
    doc = (ROOT / "docs" / "DASHBOARD_BRIEF.md").read_text(encoding="utf-8")
    y = M[M.Date.str[:4] == "2024"]
    g = y.groupby("sector")[["employed", "vacancies", "registered_seekers"]].sum() / 12
    for sec, r in g.iterrows():
        assert f"{r.employed / 1e6:.1f} million" in doc, sec
        assert f"{r.vacancies / 1e3:.0f} thousand" in doc, sec
        assert f"{r.vacancies / r.registered_seekers:.2f}" in doc, sec
    st = y.groupby("state").employed.sum() / 12
    for name, v in st.items():
        assert f"{name} {v / 1e6:.1f} million" in doc, name
    assert "4 states / UTs, 56 districts" in doc and "280 series" in doc and "47,040 rows" in doc


def test_boundaries_match_the_districts_and_the_source_areas():
    g = json.load(open(PACK / "district_boundaries.geojson"))
    prov = json.load(open(PACK / "district_boundaries_provenance.json"))
    feats = g["features"]
    codes = [f["properties"]["district_lgd_code"] for f in feats]
    dd = pd.read_csv(PACK / "dim_district.csv", dtype=str)
    assert len(feats) == 56 and sorted(codes) == sorted(dd.district_lgd_code) and len(set(codes)) == 56
    state_box = {"Delhi": (28.3, 28.95, 76.8, 77.4), "Tamil Nadu": (12.4, 13.7, 79.5, 80.4), "West Bengal": (21.5, 23.3, 87.5, 89.2),
                 "Maharashtra": (15.5, 22.2, 72.5, 81.0)}
    for f in feats:
        geom, p = f["geometry"], f["properties"]
        assert geom["type"] in ("Polygon", "MultiPolygon")
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            for ring in poly:
                assert len(ring) >= 4 and ring[0] == ring[-1]
        lat0, lat1, lon0, lon1 = state_box[p["state"]]
        assert lat0 <= p["label_lat"] <= lat1 and lon0 <= p["label_lon"] <= lon1, p["district"]
        assert abs(p["approx_area_km2"] / p["source_area_km2_mercator_corrected"] - 1) < 0.03, p["district"]
    names = dd.set_index("district_lgd_code").district
    assert all(names[f["properties"]["district_lgd_code"]] == f["properties"]["district"] for f in feats)
    assert (PACK / "district_boundaries.geojson").stat().st_size < 2_000_000
    assert prov["districts"] == 56 and prov["source"]["licence"].startswith("CC0") and len(prov["source_sha256"]) == 64


def test_brief_describes_the_boundary_file():
    doc = (ROOT / "docs" / "DASHBOARD_BRIEF.md").read_text(encoding="utf-8")
    assert "district_boundaries.geojson" in doc and "properties.district_lgd_code" in doc and "no district boundaries are in the project" not in doc


if __name__ == "__main__":
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    bad = 0
    for n, f in fns:
        try:
            f(); print(f"[PASS] {n}")
        except AssertionError as e:
            bad += 1; print(f"[FAIL] {n}: {e}")
    print(f"\n{len(fns) - bad}/{len(fns)} passed"); sys.exit(1 if bad else 0)
