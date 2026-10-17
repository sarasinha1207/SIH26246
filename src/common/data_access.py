"""Guarded access to the processed panel.

The Phase 3 split policy locks the test period (2025-01 onward) until Phase 8.  Every later phase should load data through
`load_panel`, which refuses to return test rows unless the caller unlocks them explicitly (and says so in the log).
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
ROLES = ("train", "validation", "test")


def load_panel(freq="monthly", roles=("train", "validation"), unlock_test=False, drop_blocklisted=False):
    """Return the processed panel restricted to `roles`.

    freq              'monthly' or 'quarterly'
    roles             any of 'train', 'validation', 'test'
    unlock_test       must be True to receive 'test' rows (Phase 8 final evaluation only)
    drop_blocklisted  drop identifier and flag columns that must never be model inputs
    """
    if freq not in ("monthly", "quarterly"):
        raise ValueError("freq must be 'monthly' or 'quarterly'")
    bad = set(roles) - set(ROLES)
    if bad:
        raise ValueError(f"unknown split roles: {sorted(bad)}")
    if "test" in roles and not unlock_test:
        raise PermissionError("the test period is locked until Phase 8; pass unlock_test=True only for the final evaluation")
    df = pd.read_parquet(PROC / f"panel_{freq}.parquet")
    df = df[df.Split_Role.isin(roles)].reset_index(drop=True)
    for c in df.select_dtypes("category"):
        df[c] = df[c].cat.remove_unused_categories()
    if drop_blocklisted:
        block = json.load(open(PROC / "SCHEMA.json"))["model_input_blocklist"]
        df = df.drop(columns=[c for c in block if c in df.columns])
    return df
