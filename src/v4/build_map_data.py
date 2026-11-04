#!/usr/bin/env python3
"""
v4 phase 8 - build app/data/map_data.js: the map of India with the 317 districts of the ten pilot states, and the values that colour it.

Geometry   the 317 districts come from the Local Government Directory layer (data/external/lgd_districts/LGD_Districts.parquet, 785 districts, CC0-1.0 / CC-BY-4.0, bharatlas),
           keyed by LGD district code, simplified to about 100-450 m.  The faint India backdrop is every district of the other states, simplified to about 3 km: a backdrop for
           orientation, not an authoritative boundary.
Values     per district, sector and measure, from the phase 6 roll-ups (forecast_rollups.csv.gz, level district_sector) and the panel:
               values[code][sector_index][measure_index] = [last observed, forecast at h1, h2, h3, lo_h1, hi_h1, lo_h2, hi_h2, lo_h3, hi_h3]    (h1, h2, h3 = 12, 36, 60 months ahead)
           measures: employed workers, job vacancies, registered job seekers (with the usual 90% range) and the Demand Index (now and at h1, h2, h3, no range).
Confidence per sector, measure and horizon: the label most trades of the sector carry in the cell of that horizon band (data/v4/confidence_cells.csv).

Run: python src/v4/build_map_data.py
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import config as C

ROOT = C.ROOT
LGD = ROOT / "data" / "external" / "lgd_districts" / "LGD_Districts.parquet"
PROVENANCE = ROOT / "data" / "dashboard" / "district_boundaries_provenance.json"
OUT = ROOT / "app" / "data" / "map_data.js"
HORIZONS = (12, 36, 60)
BANDS = ["1-12", "25-36", "49-60"]                              # the confidence band of each horizon
LON0, LAT0, KX = 68.0, 37.3, 0.927                              # integer map units: 0.001 degree of latitude (about 111 m); x is shrunk by cos(22 deg)
BACKDROP_TOL_DEG, BACKDROP_MIN_AREA_DEG2 = 0.03, 0.01

spec = importlib.util.spec_from_file_location("build_boundaries", ROOT / "src" / "dashboard" / "build_boundaries.py")
bb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bb)                                     # the project's own WKB reader and Douglas-Peucker simplifier


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


def rdp(pts, tol):
    """Douglas-Peucker on an open polyline (numpy array of lon, lat), iterative."""
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p, q = pts[a], pts[b]
        d = q - p
        seg = pts[a + 1:b] - p
        L = np.hypot(*d)
        dist = np.hypot(*(seg - np.outer(np.clip(seg @ d / (L * L), 0, 1), d)).T) if L > 0 else np.hypot(*seg.T)
        i = int(np.argmax(dist))
        if dist[i] > tol:
            m = a + 1 + i
            keep[m] = True
            stack += [(a, m), (m, b)]
    return pts[keep]


def borders(t, state_codes, tol=0.004):
    """The lines that separate the project's states from each other and from the rest of India, as one SVG path string.

    Edges (consecutive polygon vertices rounded to 0.0001 degree) are counted over all 785 districts of the LGD layer.  An edge is part of a state border when a project state lies on one
    side and either nothing (the coast or the national border) or a district of another state lies on the other.  Edges are chained into polylines between junctions and simplified."""
    import collections
    occ, sides = collections.Counter(), collections.defaultdict(set)
    for r in t.itertuples():
        for poly in bb.parse_wkb(bytes(r.geometry)):
            for ring in poly:
                pts = [(round(float(x), 4), round(float(y), 4)) for x, y in ring]
                for a, b in zip(pts, pts[1:]):
                    if a != b:
                        k = (min(a, b), max(a, b))
                        occ[k] += 1
                        sides[k].add(int(r.state_lgd))
    edges = [k for k, n in occ.items() if (n == 1 and next(iter(sides[k])) in state_codes) or (len(sides[k]) >= 2 and sides[k] & state_codes)]
    adj = collections.defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen, out = set(), []

    def walk(start, nxt):
        line, prev, cur = [start], start, nxt
        while True:
            line.append(cur)
            seen.add((min(prev, cur), max(prev, cur)))
            if len(adj[cur]) != 2:
                return line
            n2 = [x for x in adj[cur] if x != prev and (min(cur, x), max(cur, x)) not in seen]
            if not n2:
                return line
            prev, cur = cur, n2[0]

    for node, nb in list(adj.items()):
        if len(nb) != 2:
            for x in nb:
                if (min(node, x), max(node, x)) not in seen:
                    out.append(walk(node, x))
    for a, b in edges:                                                             # closed loops with no junction
        if (min(a, b), max(a, b)) not in seen:
            out.append(walk(a, b))
    d = []
    for line in out:
        pts = rdp(np.array(line, float), tol)
        if len(pts) < 2:
            continue
        xy = [project(lon, lat) for lon, lat in pts]
        xy = [xy[0]] + [p for i, p in enumerate(xy[1:], 1) if p != xy[i - 1]]
        if len(xy) < 2:
            continue
        d.append("M%d %d" % xy[0] + "l" + " ".join("%d %d" % (b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:])))
    return "".join(d)


def tolerance(area_deg2):
    return 0.0015 if area_deg2 < 0.05 else 0.003 if area_deg2 < 0.4 else 0.005


def confidence():
    cells = pd.read_csv(C.DATA / "confidence_cells.csv")
    dim = pd.read_csv(C.DATA / "dim_series.csv").drop_duplicates("Trade_Code")
    cells = cells.merge(dim[["Trade_Code", "Sector_Name"]], left_on="trade", right_on="Trade_Code")
    out = {}
    for sec in C.SECTORS:
        out[sec] = {}
        for k in "EVS":
            row = []
            for b in BANDS:
                lab = cells[(cells.Sector_Name == sec) & (cells.target == k) & (cells.band == b)].label_normal_volume.str.lower()
                top = lab.value_counts()
                row.append(top.index[0] + ("" if len(top) == 1 else " (varies by trade)"))
            out[sec][k] = row
    return out


def values(codes):
    r = pd.read_csv(ROOT / "data" / "v4" / "exports" / "forecast_rollups.csv.gz", low_memory=False)
    r = r[(r.level == "district_sector") & r.horizon.isin(HORIZONS)]
    raw = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet", columns=["Series_ID", "Date", "Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"])
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    last = raw[raw.Date == "2025-12-01"].merge(dim[["Series_ID", "District_LGD_Code", "Sector_Name"]], on="Series_ID").groupby(["District_LGD_Code", "Sector_Name"])[["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers"]].sum()
    # Demand Index of December 2025 per district-sector: employed-weighted over its trades
    dpar = pd.read_parquet(C.DATA / "exports" / "demand_index.parquet")
    dpar = dpar[dpar.month == "2025-12"].set_index("series_row").DI
    e = raw[raw.Date == "2025-12-01"].set_index("Series_ID").Total_Employed_Workers.reindex(dim.Series_ID).to_numpy()
    tmp = dim[["District_LGD_Code", "Sector_Name"]].assign(w=e, wd=e * dpar.reindex(range(len(dim))).to_numpy())
    now_di = (tmp.groupby(["District_LGD_Code", "Sector_Name"]).wd.sum() / tmp.groupby(["District_LGD_Code", "Sector_Name"]).w.sum())
    out = {}
    idx = r.set_index(["District_LGD_Code", "Sector_Name", "horizon"])
    for code in codes:
        per = []
        for sec in C.SECTORS:
            row = []
            for k, col in (("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers")):
                arr = [int(last.loc[(code, sec), col])] + [int(idx.loc[(code, sec, h), k]) for h in HORIZONS]
                for h in HORIZONS:
                    arr += [int(idx.loc[(code, sec, h), f"{k}_lo"]), int(idx.loc[(code, sec, h), f"{k}_hi"])]
                row.append(arr)
            row.append([round(float(now_di.loc[(code, sec)]), 1)] + [round(float(idx.loc[(code, sec, h), "DI"]), 1) for h in HORIZONS])
            per.append(row)
        out[str(code)] = per
    return out


def main():
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    dd = dim.drop_duplicates("District_LGD_Code")[["District_LGD_Code", "District_Name", "State_Name"]].sort_values(["State_Name", "District_Name"])
    codes = [int(c) for c in dd.District_LGD_Code]
    t = pq.read_table(LGD, columns=["dist_lgd", "state_lgd", "dtname", "geometry"]).to_pandas()
    t["dist_lgd"] = t.dist_lgd.astype(int)
    mine = set(codes)
    assert mine <= set(t.dist_lgd), sorted(mine - set(t.dist_lgd))
    info = dd.set_index("District_LGD_Code")
    districts, xs, ys, back = [], [], [], []
    for r in t.itertuples():
        polys = [p for p in bb.parse_wkb(bytes(r.geometry)) if abs(bb.ring_area_deg2(p[0])) >= BACKDROP_MIN_AREA_DEG2 / 10]
        if r.dist_lgd in mine:
            area = sum(abs(bb.ring_area_deg2(p[0])) for p in polys)
            d = "".join(ring_path(ring, tolerance(area)) for poly in polys for ring in poly)
            pts = np.vstack([ring for poly in polys for ring in poly[:1]])
            x0, y0 = project(pts[:, 0].min(), pts[:, 1].max())
            x1, y1 = project(pts[:, 0].max(), pts[:, 1].min())
            districts.append({"c": str(r.dist_lgd), "n": info.loc[r.dist_lgd, "District_Name"], "s": info.loc[r.dist_lgd, "State_Name"], "d": d, "bb": [x0, y0, x1, y1]})
            xs += [x0, x1]
            ys += [y0, y1]
            continue
        for poly in polys:
            if abs(bb.ring_area_deg2(poly[0])) < BACKDROP_MIN_AREA_DEG2:
                continue
            s_ = ring_path(poly[0], BACKDROP_TOL_DEG)               # outer rings only: the backdrop needs no holes
            if s_:
                back.append(s_)
                for lon, lat in poly[0][::40]:
                    px, py = project(lon, lat)
                    xs.append(px)
                    ys.append(py)
    districts.sort(key=lambda d: (d["s"], d["n"]))
    assert len(districts) == 317 == len(codes)
    pad = 400
    vb = [min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad]
    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    data = {"viewBox": vb, "backdrop": "".join(back), "borders": borders(t, set(C.STATES.values())), "districts": districts, "others": [], "states": list(C.STATES), "sectors": list(C.SECTORS), "horizons": list(HORIZONS), "targets": ["E", "V", "S", "D"],
            "layout": "values[code][sector_index][measure_index]: E, V, S = [last_observed, forecast_h1, forecast_h2, forecast_h3, lo_h1, hi_h1, lo_h2, hi_h2, lo_h3, hi_h3]; D (Demand Index) = [december_2025, h1, h2, h3]",
            "confidence": confidence(), "values": values(codes), "origin": C.ORIGIN,
            "source": {"credit": prov["source"]["credit"], "licence": prov["source"]["licence"], "sha256": hashlib.sha256(LGD.read_bytes()).hexdigest()}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.MAP_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.0f} KB): {len(districts)} districts, backdrop {len(data['backdrop']) / 1e3:.0f} KB, viewBox {[round(v) for v in vb]}")


if __name__ == "__main__":
    main()
