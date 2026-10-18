#!/usr/bin/env python3
"""
Phase 7 - write the independent train / validation / test example files (data/splits/*.parquet) and split_manifest.json.

One row = (series, forecast origin t, horizon h in 1..12).  Features are the Phase 5 selected features (union over the three targets), computed
from trailing windows only; targets, bases and shock flags are included.  Nothing is fitted here: the script only partitions rows.
The rule is in src/common/splits.py (70/5/25 of the calendar months, identical for all series, so every sector gets the same shares).

The partition needs the whole panel, including months the Phase 3 policy called "test", hence unlock_test=True below; the test file is written
but never read in Phase 7 (load_split refuses it without unlock_test).

Run: python src/splits/make_splits.py
"""
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(ROOT / "src" / "features"))
import engineering as en  # noqa: E402
import splits as sp  # noqa: E402
from data_access import load_panel  # noqa: E402

SPEC = ROOT / "data" / "processed" / "features" / "feature_sets.json"
SECTOR_SHORT = {}


def build_examples(df):
    """All (series, origin, horizon) examples of the panel `df` with the columns the models need."""
    D = en.PanelData(df)
    OF, SF = en.origin_features(D)
    ex = en.make_categorical(en.build_examples(D, OF, SF, horizons=en.HORIZONS), D)
    spec = json.load(open(SPEC))["targets"]
    feats = sorted({f for t in spec.values() for f in t["features"]})
    bases = [f"{b}_{k}" for k in "EVS" for b in ("last", "sm3", "sm6")]
    targets = [f"target_{k}" for k in "EVS"]
    # the target month of every row is inside a shock window (used to exclude it from scoring, as in Phase 6)
    shock_ev, shock_s = D.covid | D.policy, D.covid | D.policy | D.ramp
    ex["target_in_shock_EV"] = shock_ev[ex.target_idx.to_numpy()]
    ex["target_in_shock_S"] = shock_s[ex.target_idx.to_numpy()]
    ex["origin_date"] = D.dates[ex.origin_idx.to_numpy()]
    ex["target_date"] = D.dates[ex.target_idx.to_numpy()]
    ex["sector"] = D.sector[ex.series_row.to_numpy()]
    ex["state"] = D.meta.State_Name.to_numpy()[ex.series_row.to_numpy()]
    ex["district"] = D.meta.District_Name.to_numpy()[ex.series_row.to_numpy()]
    ids = ["Series_ID", "sector", "state", "district", "origin_idx", "target_idx", "origin_date", "target_date", "horizon",
           "shock_EV", "shock_S", "target_in_shock_EV", "target_in_shock_S"]
    cols = ids + [f for f in feats if f not in ids] + bases + targets
    return ex[cols].copy(), D, feats


def assign(ex):
    w = sp.windows()
    t_end, v_end = w["train"][1], w["validation"][1]
    oi, ti = ex.origin_idx.to_numpy(), ex.target_idx.to_numpy()
    part = {"train": ti <= t_end,
            "validation": (ti > t_end) & (ti <= v_end) & (oi >= t_end),
            "test": (ti > v_end) & (oi >= v_end)}
    return part


def main():
    t0 = time.time()
    df = load_panel("monthly", roles=("train", "validation", "test"), unlock_test=True)       # partitioning only, nothing is fitted
    ex, D, feats = build_examples(df)
    part = assign(ex)
    n_all = len(ex)
    assigned = np.zeros(n_all, int)
    for p in part.values():
        assigned += p
    assert assigned.max() == 1, "a row landed in two splits"
    sp.SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    files, sector_rows = {}, {}
    for name in sp.NAMES:
        sub = ex[part[name]].reset_index(drop=True)
        sub.insert(0, "split", name)
        path = sp.SPLIT_DIR / f"{name}.parquet"
        sub.to_parquet(path, index=False, compression="zstd")
        files[name] = {"file": path.name, "rows": int(len(sub)), "bytes": path.stat().st_size, "sha256": sp.sha256(path),
                       "origin_range": [str(sub.origin_date.min().date()), str(sub.origin_date.max().date())],
                       "target_range": [str(sub.target_date.min().date()), str(sub.target_date.max().date())],
                       "rows_by_horizon": {int(h): int(n) for h, n in sub.horizon.value_counts().sort_index().items()}}
        sector_rows[name] = sub.groupby("sector").size().to_dict()
    sector_months = {s: {name: int(((D.dates >= pd.Timestamp(sp.month_of(a))) & (D.dates <= pd.Timestamp(sp.month_of(b)))).sum())
                         for name, (a, b) in sp.windows().items()} for s in sorted(set(D.sector))}
    series_per_sector = pd.Series(D.sector).value_counts().to_dict()
    manifest = {
        "rule": "70% / 5% / 25% of the 192 calendar months, chronological, same cut dates for every series (so every sector has the same shares)",
        "windows": sp.describe(),
        "row_rule": {"train": "target month in train window", "validation": "target in validation window and origin >= last train month",
                     "test": "target in test window and origin >= last validation month"},
        "rows_total_before_split": n_all, "rows_dropped_straddling_boundaries": int(n_all - sum(f["rows"] for f in files.values())),
        "files": files, "series": int(len(D.sid)), "series_per_sector": {k: int(v) for k, v in series_per_sector.items()},
        "calendar_months_per_sector": sector_months, "rows_per_sector": {k: {s: int(n) for s, n in v.items()} for k, v in sector_rows.items()},
        "feature_union": feats,
        "notes": ["Features use trailing windows only; train rows can be rebuilt from a panel that stops at the train end (tests/test_splits.py).",
                  "The test file is not read in Phase 7.  Its 2023-2024 months were seen by Phase 5/6 selection (fold F3), and the 2025-26 months were scored once by the quarantined prototype.",
                  "Shock flags: target_in_shock_EV (COVID + policy spans), target_in_shock_S (also the e-Shram ramp, 2021-08 to 2023-02)."],
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "created_seconds": round(time.time() - t0, 1)}
    json.dump(manifest, open(sp.MANIFEST, "w"), indent=2)
    for n, f in files.items():
        print(f"{n:11s} rows {f['rows']:>8,}  origins {f['origin_range']}  targets {f['target_range']}  {f['bytes'] / 1e6:.1f} MB")
    print("dropped (straddling):", manifest["rows_dropped_straddling_boundaries"])


if __name__ == "__main__":
    main()
