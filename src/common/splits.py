"""Phase 7 data splits: 70% train / 5% validation / 25% test of the 192 calendar months (2011-01 to 2026-12), identical for all 280 series.

This definition supersedes the Phase 3 `Split_Role` column (train <= 2023-12, validation 2024, test 2025-26) for Phase 7 onwards; the column is
left in the panel for history only.  The files are written once by src/splits/make_splits.py and read through `load_split`, which refuses to
return the test file unless the caller unlocks it (Phase 8 only).

Row rule (a row = one series, one forecast origin t, one horizon h; target month = t + h):
    train       target month in the train window
    validation  target month in the validation window and origin >= last month of the train window
    test        target month in the test window and origin >= last month of the validation window
Rows are assigned by target month, so the three files have disjoint targets in strict time order.  The origin rule means the model that
forecasts a validation (test) row could have been fitted on every label of the preceding windows before the forecast was made.  Rows that
straddle a boundary without satisfying the origin rule are dropped (counted in the manifest), not reassigned.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPLIT_DIR = ROOT / "data" / "splits"
MANIFEST = SPLIT_DIR / "split_manifest.json"
FIRST_MONTH = pd.Timestamp("2011-01-01")
N_MONTHS = 192
FRACTIONS = {"train": 0.70, "validation": 0.05, "test": 0.25}
NAMES = ("train", "validation", "test")


def windows():
    """Month-index windows (inclusive) per split, derived from the fractions: 134 / 10 / 48 months."""
    n_train = round(FRACTIONS["train"] * N_MONTHS)
    n_val = round(FRACTIONS["validation"] * N_MONTHS)
    edges = {"train": (0, n_train - 1), "validation": (n_train, n_train + n_val - 1), "test": (n_train + n_val, N_MONTHS - 1)}
    return edges


def month_of(idx):
    return FIRST_MONTH + pd.DateOffset(months=int(idx))


def describe():
    return {s: {"first_index": a, "last_index": b, "first_month": str(month_of(a).date()), "last_month": str(month_of(b).date()), "months": b - a + 1,
                "share": round((b - a + 1) / N_MONTHS, 4)} for s, (a, b) in windows().items()}


def sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def load_split(name, columns=None, unlock_test=False, verify=False):
    """Read data/splits/<name>.parquet.  The test file needs unlock_test=True (Phase 8 final evaluation only)."""
    if name not in NAMES:
        raise ValueError(f"unknown split {name!r}")
    if name == "test" and not unlock_test:
        raise PermissionError("the test split is locked until Phase 8; pass unlock_test=True only for the final evaluation")
    path = SPLIT_DIR / f"{name}.parquet"
    if verify:
        want = json.load(open(MANIFEST))["files"][name]["sha256"]
        if sha256(path) != want:
            raise RuntimeError(f"{path.name} does not match the checksum recorded in split_manifest.json")
    return pd.read_parquet(path, columns=columns)
