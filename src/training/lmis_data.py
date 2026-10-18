"""Phase 7 - turning the split files into model inputs, and scoring.

For target k in E (employed), V (vacancies), S (registered seekers) the model learns y = log(target at t+h) - log(base at t); the base is last value (E),
3-month mean (V) or 6-month mean (S), as selected in Phase 5.  Predicted counts are exp(base + predicted change).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "data" / "processed" / "features" / "feature_sets.json"
KEYS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
NAMES = {"E": "employed workers", "V": "job vacancies", "S": "registered seekers"}


def spec():
    return json.load(open(SPEC_PATH))["targets"]


def shock_col(k, which):
    s = "S" if k == "S" else "EV"
    return f"shock_{s}" if which == "window" else f"target_in_shock_{s}"


def train_rows(df, k, sp=None):
    """Rows used to fit the model for target k: all rows, minus examples whose 13-month-back / horizon-ahead window touches a shock when the Phase 5 policy says so."""
    sp = sp or spec()[k]
    keep = ~df[shock_col(k, "window")].to_numpy() if sp["mask_shock_windows"] else np.ones(len(df), bool)
    return df[keep]


def eval_rows(df, k, mask_shock=True):
    """Rows scored for target k: targets inside shock months (COVID, policy spans; the e-Shram ramp for seekers) are excluded when mask_shock is True."""
    return df[~df[shock_col(k, "target")].to_numpy()] if mask_shock else df


def xy(df, k, sp=None):
    sp = sp or spec()[k]
    y = df[f"target_{k}"].to_numpy() - df[f"{sp['base']}_{k}"].to_numpy()
    return df[sp["features"]], y


def base_log(df, k, sp=None):
    sp = sp or spec()[k]
    return df[f"{sp['base']}_{k}"].to_numpy()


def baseline_log(df, k, name="last_plus_seasonal_shift"):
    """Phase 6 reference predictions (log level) computed from columns of the split file."""
    last = df[f"last_{k}"].to_numpy()
    if name == "last_value":
        return last
    if name == "last_plus_seasonal_shift":
        return last + np.nan_to_num(df[f"{k}_sf_shift"].to_numpy(), nan=0.0)
    if name == "seasonal_naive_drift":
        return last + df[f"{k}_yadrift_h"].to_numpy()
    raise KeyError(name)


def wape(actual_log, pred_log):
    a, p = np.exp(actual_log), np.exp(pred_log)
    return 100.0 * float(np.abs(a - p).sum() / a.sum())


def wape_by_horizon(df, actual_log, pred_log, horizons=range(1, 13)):
    out = {}
    h = df["horizon"].to_numpy()
    for hh in horizons:
        m = h == hh
        if m.any():
            out[int(hh)] = wape(actual_log[m], pred_log[m])
    return out


def mean_horizon_wape(df, actual_log, pred_log):
    """Equal weight per horizon, so long horizons (fewer, noisier rows) count as much as short ones."""
    v = wape_by_horizon(df, actual_log, pred_log)
    return float(np.mean(list(v.values()))), v
