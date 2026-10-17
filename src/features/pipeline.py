"""Phase 5 -> 6/7 interface: ready-to-train data for each target, using the selected feature sets.

    from pipeline import training_frame
    X, y, w, meta = training_frame("V", train_end="2023-12-01")             # all 12 horizons, shock windows masked as selected
    Xv, yv, _, mv = validation_frame("V", origin="2023-12-01", months=12)    # rows whose targets fall in the next 12 months

The panel is always loaded through load_panel, so the locked test period (2025+) can only be reached with unlock_test=True
(Phase 8).  The prediction target is log(x[t+h]) - log(x[t] or a smoothed base), as chosen in selection; add the base back and exponentiate.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402

SPEC_PATH = ROOT / "data" / "processed" / "features" / "feature_sets.json"
_CACHE = {}


def spec():
    return json.load(open(SPEC_PATH))["targets"]


def _examples(unlock_test=False):
    key = bool(unlock_test)
    if key not in _CACHE:
        roles = ("train", "validation", "test") if unlock_test else ("train", "validation")
        D = en.PanelData(load_panel("monthly", roles=roles, unlock_test=unlock_test))
        OF, SF = en.origin_features(D)
        ex = en.make_categorical(en.build_examples(D, OF, SF, horizons=en.HORIZONS), D)
        _CACHE[key] = (D, ex)
    return _CACHE[key]


def _idx(D, date):
    return int(np.where(D.dates == pd.Timestamp(date))[0][0])


def _target_shock(D, ex, k):
    shock = (D.covid | D.policy | (D.ramp if k == "S" else np.zeros(D.T, bool)))
    return shock[ex.target_idx.to_numpy()]


def training_frame(k, train_end="2023-12-01", unlock_test=False):
    """Rows whose target month is <= train_end.  Returns X, y (relative to the base), sample weights (or None), meta."""
    D, ex = _examples(unlock_test)
    sp = spec()[k]
    te = _idx(D, train_end)
    m = (ex.target_idx <= te).to_numpy()
    if sp["mask_shock_windows"]:
        m &= ~ex["shock_S" if k == "S" else "shock_EV"].to_numpy()
    sub = ex[m]
    y = sub[f"target_{k}"] - sub[f"{sp['base']}_{k}"]
    hl = sp["recency_halflife_months"]
    w = (0.5 ** ((te - sub.target_idx.to_numpy()) / hl)) if hl else None
    return sub[sp["features"]], y, w, sub[["Series_ID", "origin_idx", "target_idx", "horizon", f"{sp['base']}_{k}", f"target_{k}"]]


def validation_frame(k, origin="2023-12-01", months=12, unlock_test=False):
    """Rows with origin >= `origin` and target within `months` after it, excluding targets inside shock windows."""
    D, ex = _examples(unlock_test)
    sp = spec()[k]
    o = _idx(D, origin)
    m = ((ex.origin_idx >= o) & (ex.target_idx <= o + months)).to_numpy() & ~_target_shock(D, ex, k)
    sub = ex[m]
    y = sub[f"target_{k}"] - sub[f"{sp['base']}_{k}"]
    return sub[sp["features"]], y, None, sub[["Series_ID", "origin_idx", "target_idx", "horizon", f"{sp['base']}_{k}", f"target_{k}"]]
