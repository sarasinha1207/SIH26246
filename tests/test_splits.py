"""Phase 7 tests: the train / validation / test files are independent, time-ordered, balanced across sectors, and rebuildable without later data.
Runs under pytest or standalone: python tests/test_splits.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for sub in ("common", "features", "splits"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import splits as sp  # noqa: E402
import make_splits as ms  # noqa: E402
from data_access import load_panel  # noqa: E402

MAN = json.load(open(sp.MANIFEST))
KEY = ["Series_ID", "origin_idx", "horizon"]
W = sp.windows()
KEYCOLS = KEY + ["target_idx", "sector", "split"]
TR, VA = sp.load_split("train"), sp.load_split("validation")
TE = sp.load_split("test", unlock_test=True)                       # structure checks only; no model touches it in Phase 7


def test_windows_are_70_5_25_of_192_months():
    d = sp.describe()
    assert [d[s]["months"] for s in sp.NAMES] == [134, 10, 48]
    assert abs(d["train"]["share"] - 0.70) < 0.005 and abs(d["validation"]["share"] - 0.05) < 0.005 and abs(d["test"]["share"] - 0.25) < 0.005
    assert d["train"]["last_month"] == "2022-02-01" and d["validation"]["last_month"] == "2022-12-01" and d["test"]["last_month"] == "2026-12-01"


def test_files_are_disjoint_and_time_ordered():
    keys = [set(map(tuple, f[KEY].to_numpy())) for f in (TR, VA, TE)]
    assert not (keys[0] & keys[1]) and not (keys[0] & keys[2]) and not (keys[1] & keys[2])
    assert TR.target_idx.max() == W["train"][1] < VA.target_idx.min()
    assert VA.target_idx.min() == W["validation"][0] and VA.target_idx.max() == W["validation"][1] < TE.target_idx.min() == W["test"][0]
    assert TE.target_idx.max() == W["test"][1]
    assert VA.origin_idx.min() >= W["train"][1] and TE.origin_idx.min() >= W["validation"][1]
    assert (TR.split == "train").all() and (VA.split == "validation").all() and (TE.split == "test").all()
    assert len(TR) + len(VA) + len(TE) + MAN["rows_dropped_straddling_boundaries"] == MAN["rows_total_before_split"]


def test_every_sector_has_the_same_shares():
    """The cut dates are the same for all series, so each sector gets 134 / 10 / 48 months and an equal row count (56 series per sector)."""
    assert set(MAN["series_per_sector"].values()) == {56}
    for s, m in MAN["calendar_months_per_sector"].items():
        assert m == {"train": 134, "validation": 10, "test": 48}, s
    for name, f in (("train", TR), ("validation", VA), ("test", TE)):
        n = f.groupby("sector").size()
        assert n.nunique() == 1 and len(n) == 5, name
    assert TR.groupby("Series_ID").size().nunique() == 1


def test_files_match_the_recorded_checksums():
    for n in sp.NAMES:
        assert sp.sha256(sp.SPLIT_DIR / f"{n}.parquet") == MAN["files"][n]["sha256"], n


def test_test_split_stays_locked_by_default():
    try:
        sp.load_split("test")
    except PermissionError:
        return
    raise AssertionError("load_split returned the test split without unlock_test")


def _same(a, b, cols):
    a = a.sort_values(KEY).reset_index(drop=True)
    b = b.sort_values(KEY).reset_index(drop=True)
    assert len(a) == len(b)
    for c in cols:
        x, y = a[c].to_numpy(), b[c].to_numpy()
        if x.dtype.kind in "fiub":
            assert np.allclose(x.astype(float), y.astype(float), equal_nan=True, rtol=0, atol=1e-9), c
        else:
            assert (x == y).all(), c


def test_train_and_validation_rows_are_rebuilt_exactly_from_data_up_to_their_window():
    """Truncate the panel at the end of the window; the features and targets of the file's rows must be identical (no later data was used)."""
    full = load_panel("monthly", roles=("train", "validation", "test"), unlock_test=True)
    cols = [c for c in TR.columns if c not in ("split",)]
    for name, f, last in (("train", TR, W["train"][1]), ("validation", VA, W["validation"][1])):
        cut = full[full.Date <= sp.month_of(last)]
        ex, _, _ = ms.build_examples(cut)
        part = ms.assign(ex)[name] if name == "train" else None
        if name == "validation":
            oi, ti = ex.origin_idx.to_numpy(), ex.target_idx.to_numpy()
            part = (ti > W["train"][1]) & (ti <= last) & (oi >= W["train"][1])
        _same(ex[part], f, cols)


if __name__ == "__main__":
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"[PASS] {n}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {n}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
