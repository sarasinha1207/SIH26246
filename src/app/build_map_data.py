#!/usr/bin/env python3
"""
Public site - build app/data/map_data.js: the map of India with the project's 56 districts, and the forecast values that colour it.

Geometry
  * The 56 project districts come from data/dashboard/district_boundaries.geojson (already built from the LGD layer, keyed by LGD code).
  * The other districts of the four project states (18 in West Bengal, 34 in Tamil Nadu) come from the same LGD layer
    (data/external/lgd_districts/LGD_Districts.parquet, 785 districts, CC0-1.0 / CC-BY-4.0, bharatlas).  They are drawn and highlighted but
    carry no forecast, so the page says "no forecast data" for them.
  * The faint India backdrop is every district of the other states, simplified to about 3 km.  It is a backdrop for orientation, not an authoritative boundary.
Values
  * For every district, sector and target (employed workers, vacancies, job seekers): the last observed value, the forecast 3, 6 and 12 months
    ahead and its 90% range, read from outputs/forecasts/origin_<month>/forecast_long.csv.

Run: python src/app/build_map_data.py
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "2026-10"
FC = ROOT / "outputs" / "forecasts" / f"origin_{ORIGIN}" / "forecast_long.csv"
GEOJSON = ROOT / "data" / "dashboard" / "district_boundaries.geojson"
LGD = ROOT / "data" / "external" / "lgd_districts" / "LGD_Districts.parquet"
OUT = ROOT / "app" / "data" / "map_data.js"
PROVENANCE = ROOT / "data" / "dashboard" / "district_boundaries_provenance.json"
HORIZONS = (3, 6, 12)
TARGETS = (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers"))
LON0, LAT0, KX = 68.0, 37.3, 0.927                       # integer map units: 0.001 degree of latitude (about 111 m); x is shrunk by cos(22 deg)
BACKDROP_TOL_DEG, BACKDROP_MIN_AREA_DEG2 = 0.03, 0.01
STATE_CODES = {"Maharashtra": 27, "Delhi": 7, "West Bengal": 19, "Tamil Nadu": 33}   # LGD state codes of the four project states

spec = importlib.util.spec_from_file_location("build_boundaries", ROOT / "src" / "dashboard" / "build_boundaries.py")
bb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bb)                                # reuse the project's own WKB reader and Douglas-Peucker simplifier


def project(lon, lat):
    return int(round((lon - LON0) * 1000 * KX)), int(round((LAT0 - lat) * 1000))


def ring_path(ring, tol_deg):
    ring = np.asarray(ring, float)
    if tol_deg:
        ring = bb.simplify_ring(ring, tol_deg)
    pts = [project(lon, lat) for lon, lat in ring[:-1]]
    clean = [pts[0]] + [p for i, p in enumerate(pts[1:], 1) if p != pts[i - 1]]
    if len(clean) < 3:
        return ""
    d = "M%d %d" % clean[0]
    d += "l" + " ".join("%d %d" % (b[0] - a[0], b[1] - a[1]) for a, b in zip(clean, clean[1:]))
    return d + "z"


def main():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    codes = {f["properties"]["district_lgd_code"] for f in gj["features"]}
    assert len(codes) == 56

    districts, xs, ys = [], [], []
    for f in gj["features"]:
        p, g = f["properties"], f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        tol = 0.0015 if p["approx_area_km2"] < 500 else 0.004
        d = "".join(ring_path(r, tol) for poly in polys for r in poly)
        x0, y0 = project(p["bbox"][0], p["bbox"][3])
        x1, y1 = project(p["bbox"][2], p["bbox"][1])
        lx, ly = project(p["label_lon"], p["label_lat"])
        districts.append({"c": p["district_lgd_code"], "n": p["district"], "s": p["state"], "d": d, "lx": lx, "ly": ly, "bb": [x0, y0, x1, y1]})
        xs += [x0, x1]; ys += [y0, y1]

    t = pq.read_table(LGD, columns=["dist_lgd", "state_lgd", "dtname", "geometry"]).to_pandas()
    t["dist_lgd"] = t.dist_lgd.astype(int); t["state_lgd"] = t.state_lgd.astype(int)
    mine = {int(c) for c in codes}
    state_of = {v: k for k, v in STATE_CODES.items()}
    others, back = [], []
    for r in t.itertuples():
        if r.dist_lgd in mine:
            continue
        polys = [p for p in bb.parse_wkb(bytes(r.geometry)) if abs(bb.ring_area_deg2(p[0])) >= BACKDROP_MIN_AREA_DEG2 / 10]
        if r.state_lgd in state_of:                          # a district of a project state that has no forecast: drawn on its own
            d = "".join(ring_path(ring, 0.004) for poly in polys for ring in poly)
            pts = np.vstack([ring for poly in polys for ring in poly[:1]])
            x0, y0 = project(pts[:, 0].min(), pts[:, 1].max()); x1, y1 = project(pts[:, 0].max(), pts[:, 1].min())
            others.append({"c": str(r.dist_lgd), "n": r.dtname.strip(), "s": state_of[r.state_lgd], "d": d, "bb": [x0, y0, x1, y1]})
            xs += [x0, x1]; ys += [y0, y1]
            continue
        for poly in polys:
            if abs(bb.ring_area_deg2(poly[0])) < BACKDROP_MIN_AREA_DEG2:
                continue
            for ring in poly[:1]:                           # outer rings only: the backdrop needs no holes
                s_ = ring_path(ring, BACKDROP_TOL_DEG)
                if s_:
                    back.append(s_)
                    for lon, lat in ring[::40]:
                        px, py = project(lon, lat); xs.append(px); ys.append(py)
    backdrop = "".join(back)
    pad = 400
    vb = [min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad]

    L = pd.read_csv(FC, dtype={"district_lgd_code": str})
    sectors = sorted(L.sector.unique())
    conf = {s: {k: L[(L.sector == s) & (L.target_variable == tv)].confidence.iloc[0] for k, tv in TARGETS} for s in sectors}
    for s in sectors:
        for k, tv in TARGETS:
            assert L[(L.sector == s) & (L.target_variable == tv)].confidence.nunique() == 1
    values = {}
    for code in sorted(codes, key=int):
        per = []
        for s in sectors:
            row = []
            for k, tv in TARGETS:
                g = L[(L.district_lgd_code == code) & (L.sector == s) & (L.target_variable == tv)].set_index("horizon")
                assert len(g) == 12
                arr = [round(float(g.last_observed.iloc[0]), 1)] + [round(float(g.loc[h, "forecast"]), 1) for h in HORIZONS]
                for h in HORIZONS:
                    arr += [round(float(g.loc[h, "lo90"]), 1), round(float(g.loc[h, "hi90"]), 1)]
                row.append(arr)
            per.append(row)
        values[code] = per

    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    data = {"viewBox": vb, "backdrop": backdrop, "districts": districts, "others": sorted(others, key=lambda o: (o["s"], o["n"])), "sectors": sectors, "horizons": list(HORIZONS), "targets": [k for k, _ in TARGETS],
            "layout": "values[code][sector_index][target_index] = [last_observed, forecast_h3, forecast_h6, forecast_h12, lo_h3, hi_h3, lo_h6, hi_h6, lo_h12, hi_h12]",
            "confidence": conf, "values": values, "origin": ORIGIN,
            "source": {"credit": prov["source"]["credit"], "licence": prov["source"]["licence"], "sha256": prov["source_sha256"]}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.MAP_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.0f} KB): {len(districts)} districts + {len(others)} without forecast, backdrop {len(backdrop) / 1e3:.0f} KB, viewBox {vb}")


if __name__ == "__main__":
    main()
