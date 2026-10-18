#!/usr/bin/env python3
"""
Builds data/dashboard/district_boundaries.geojson: the polygons of the project's 56 districts, keyed by the official LGD district code.

Source (public, CC0-1.0 / CC-BY-4.0): the Local Government Directory district layer as distributed by bharatlas
(https://bharatlas.com/, layer "Districts (2024), LGD", 785 districts, last updated 2026-05-19).  Download once:

    curl -L -o LGD_Districts.parquet https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/districts/LGD_Districts.parquet
    (22,178,335 bytes)

then run:  python src/dashboard/build_boundaries.py path/to/LGD_Districts.parquet

The script keeps the 56 districts of data/dashboard/dim_district.csv (matched on LGD code, with the state code checked), rounds coordinates to
4 decimals (about 11 m) and simplifies each ring with Douglas-Peucker at 0.002 degrees (about 200 m), which is right for a dashboard map but not
for survey work.  The source SHAPE_Area column is a Web-Mercator area, so it is multiplied by cos(latitude)^2 before it is compared with the area of the simplified polygons.
Boundaries are the LGD/Census-2011 geometry with later updates for some districts (see boundary_vintage), so district
names in the source can be the older ones (for example Aurangabad for Chhatrapati Sambhajinagar); the LGD code is the reliable key.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "dashboard"
TOLERANCE_DEG = 0.002
DECIMALS = 4
MIN_POLYGON_AREA_DEG2 = 2e-6
SOURCE = {"name": "LGD districts (2024) via bharatlas", "url": "https://bharatlas.com/", "download_url":
          "https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/districts/LGD_Districts.parquet", "licence": "CC0-1.0 / CC-BY-4.0",
          "credit": "Local Government Directory (lgdirectory.gov.in), distributed by bharatlas", "layer_last_updated": "2026-05-19"}


def parse_wkb(buf):
    """Minimal 2-D WKB reader for Polygon and MultiPolygon.  Returns a list of polygons; each polygon is a list of (n, 2) ring arrays."""
    def geom(off):
        end = "<" if buf[off] == 1 else ">"
        gtype = struct.unpack_from(end + "I", buf, off + 1)[0]
        off += 5
        assert gtype in (3, 6), f"unsupported WKB type {gtype}"
        if gtype == 3:
            poly, off = polygon(off, end)
            return [poly], off
        n = struct.unpack_from(end + "I", buf, off)[0]
        off += 4
        polys = []
        for _ in range(n):
            sub, off = geom(off)
            polys += sub
        return polys, off

    def polygon(off, end):
        nrings = struct.unpack_from(end + "I", buf, off)[0]
        off += 4
        rings = []
        for _ in range(nrings):
            npts = struct.unpack_from(end + "I", buf, off)[0]
            off += 4
            rings.append(np.frombuffer(buf, dtype=np.dtype(end + "f8"), count=2 * npts, offset=off).reshape(npts, 2).copy())
            off += 16 * npts
        return rings, off

    polys, _ = geom(0)
    return polys


def douglas_peucker(pts, tol):
    n = len(pts)
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = pts[i + 1:j]
        d = b - a
        norm = np.hypot(*d)
        dist = np.hypot(*(seg - a).T) if norm == 0 else np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / norm
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep]


def simplify_ring(ring, tol):
    """Closed ring: split at the point farthest from the start so the end points are not identical, then simplify both halves."""
    pts = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
    if len(pts) <= 4:
        return np.vstack([pts, pts[:1]])
    k = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    first, second = douglas_peucker(pts[:k + 1], tol), douglas_peucker(np.vstack([pts[k:], pts[:1]]), tol)
    out = np.vstack([first[:-1], second])
    return out if len(out) >= 4 else np.vstack([out, out[:1]])


def ring_area_deg2(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))


def area_km2(polys):
    """Approximate area from degrees (equirectangular at the polygon's latitude)."""
    tot = 0.0
    for rings in polys:
        lat = np.radians(rings[0][:, 1].mean())
        k = (111.32 * np.cos(lat)) * 110.57
        tot += abs(ring_area_deg2(rings[0])) * k - sum(abs(ring_area_deg2(h)) * k for h in rings[1:])
    return tot


def main(src):
    OUT.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    dd = pd.read_csv(OUT / "dim_district.csv", dtype={"district_lgd_code": str, "state_lgd_code": str})
    codes = [int(c) for c in dd.district_lgd_code]
    t = pq.read_table(src, filters=[("dist_lgd", "in", codes)]).to_pandas()
    assert len(t) == 56 and set(t.dist_lgd) == set(codes), "the source does not contain exactly the 56 project districts"
    t["dist_lgd"] = t.dist_lgd.astype(int).astype(str)
    feats, rows = [], []
    for r in dd.itertuples():
        s = t[t.dist_lgd == r.district_lgd_code].iloc[0]
        assert str(int(s.state_lgd)).zfill(2) == r.state_lgd_code, (r.district, s.state_lgd)
        polys = [[simplify_ring(np.round(ring, 6), TOLERANCE_DEG) for ring in poly] for poly in parse_wkb(bytes(s.geometry))]
        polys = [p for p in polys if abs(ring_area_deg2(p[0])) >= MIN_POLYGON_AREA_DEG2] or polys[:1]
        coords = [[np.round(ring, DECIMALS).tolist() for ring in poly] for poly in polys]
        allpts = np.vstack([ring for poly in polys for ring in poly[:1]])
        areas = [abs(ring_area_deg2(p[0])) for p in polys]
        big = polys[int(np.argmax(areas))][0]
        cx = float(np.average(big[:, 0])), float(np.average(big[:, 1]))
        feats.append({"type": "Feature", "properties": {
            "district_lgd_code": r.district_lgd_code, "district": r.district, "state": r.state, "state_lgd_code": r.state_lgd_code, "district_tier": r.district_tier,
            "boundary_name_in_source": s.dtname, "boundary_vintage": s.year_stat or "unknown", "approx_area_km2": round(area_km2(polys), 1),
            "source_area_km2_mercator_corrected": round(float(s.SHAPE_Area) * np.cos(np.radians((float(allpts[:, 1].min()) + float(allpts[:, 1].max())) / 2)) ** 2 / 1e6, 1), "label_lon": round(cx[0], 4), "label_lat": round(cx[1], 4),
            "bbox": [round(float(allpts[:, 0].min()), 4), round(float(allpts[:, 1].min()), 4), round(float(allpts[:, 0].max()), 4), round(float(allpts[:, 1].max()), 4)]},
            "geometry": {"type": "MultiPolygon" if len(coords) > 1 else "Polygon", "coordinates": coords if len(coords) > 1 else coords[0]}})
    gj = {"type": "FeatureCollection", "name": "lmis_district_boundaries", "crs_note": "WGS84 (EPSG:4326), longitude/latitude in degrees", "features": feats}
    path = OUT / "district_boundaries.geojson"
    path.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    prov = {"source": SOURCE, "source_file": src.name, "source_bytes": src.stat().st_size, "source_sha256": sha, "districts": len(feats),
            "simplification_tolerance_deg": TOLERANCE_DEG, "coordinate_decimals": DECIMALS, "output_bytes": path.stat().st_size,
            "join_key": "properties.district_lgd_code (string) = district_lgd_code in monthly_metrics_2011_2024.csv and dim_district.csv",
            "caveats": ["Dashboard-grade simplification, not for survey use.", "Mostly Census-2011-era geometry with later updates; names in the source can be older than the dashboard names.",
                        "Each district ring is simplified separately, so tiny gaps can appear along shared borders at high zoom."]}
    json.dump(prov, open(OUT / "district_boundaries_provenance.json", "w"), indent=2)
    print(f"{len(feats)} districts -> {path} ({path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
