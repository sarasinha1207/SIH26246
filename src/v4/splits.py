"""
v4 phase 3 - time windows, forecast-origin rules and row sampling for a 60-month horizon.

A training example is one (series, forecast origin t, horizon h); the target is the log level at month t + h.  History has 312 months (2000-01 = index 0
to 2025-12 = index 311) and the forecast horizon is 1..60, so windows are cut by the month of the TARGET, with a strict rule on the origin:

    window       target months (index)          fitted on                       origin rule
    train        2000-01 to 2009-12 (0..119)    -                               t + h <= 119
    validation   2010-01 to 2014-12 (120..179)  rows with t + h <= 119          t >= 119          (tuning only)
    test         2015-01 to 2019-12 (180..239)  rows with t + h <= 179          t >= 179          (opened once)
    stress       2020-01 to 2025-12 (240..311)  rows with t + h <= 239          t >= 239          (opened once, information only)
    deploy       2026-01 to 2030-12 (forecast)  rows with t + h <= 311          t = 311

A row of an evaluation window starts after the last month the model was fitted on, so the model could have been fitted on every label before the forecast was
made.  Each window is 60 months or longer, so even the 60-month horizon is evaluated with strict origins.  The test window is calm on purpose (no COVID-19, no
e-Shram break), so it measures typical forecasting skill; the COVID-19 and e-Shram years form the stress window, which measures how a model fitted on
the earlier years copes with shocks nobody could foresee.  The deployed model is fitted on everything (2000-2025) and has seen those shocks.

Sampling: all (t, h) pairs of a window are eligible; for each horizon the 1/6 of its origins with the smallest value of a fixed uniform draw U[t, h] are kept (at
least 6, or all when fewer are eligible), so each smaller fraction is a subset of a larger one and the long horizons are never empty.  The same pair is used for
every series.
"""
import numpy as np

import config as C

T = C.N_MONTHS
MIN_ORIGIN = 36                              # origins need 36 months of history (momentum over 36 months, seasonal profile)
MAX_H = len(C.HORIZONS)
CUT = {"train": 119, "validation": 179, "test": 239, "stress": 311}          # last target month (inclusive) of each window
NAMES = ("train", "validation", "test", "stress")
LOCKED = ("test", "stress")                  # evaluation windows that may be scored once
FRAC = 1 / 6
MIN_PER_HORIZON = 6                           # origins kept per horizon at least (the 60-month horizon has only a few eligible origins)
_U = np.random.default_rng(C.SEED).random((T, MAX_H + 1), dtype=np.float32)


def month(idx):
    return str(C.MONTHS[int(idx)])


def window(name):
    """(first, last) target month index of a window."""
    lo = {"train": 0, "validation": CUT["train"] + 1, "test": CUT["validation"] + 1, "stress": CUT["test"] + 1}[name]
    return lo, CUT[name]


def _pairs(mask_fn, frac, min_per_horizon=MIN_PER_HORIZON):
    """Eligible (t, h) pairs, thinned per horizon: the ceil(frac * n) pairs with the smallest fixed draw U, and at least `min_per_horizon` (all of them when fewer are eligible)."""
    t, h = np.meshgrid(np.arange(T), np.arange(1, MAX_H + 1), indexing="ij")
    t, h = t.ravel(), h.ravel()
    elig = mask_fn(t, h)
    t, h = t[elig], h[elig]
    u = _U[t, h]
    keep = np.zeros(len(t), bool)
    for hh in np.unique(h):
        idx = np.where(h == hh)[0]
        n_keep = min(len(idx), max(int(np.ceil(frac * len(idx))), min_per_horizon))
        keep[idx[np.argsort(u[idx], kind="stable")[:n_keep]]] = True
    return t[keep].astype(np.int32), h[keep].astype(np.int32)


def fit_pairs(cut, frac=FRAC):
    """(origin, horizon) pairs a model fitted on all labels up to month index `cut` may train on: the target month is at or before the cut."""
    return _pairs(lambda t, h: (t >= MIN_ORIGIN) & (t + h <= cut), frac)


def eval_pairs(name, frac=FRAC, unlock=False):
    """(origin, horizon) pairs of an evaluation window: the origin is at or after the last month the model was fitted on and the target is inside the window."""
    if name in LOCKED and not unlock:
        raise PermissionError(f"the {name} window is scored once; pass unlock=True only for that evaluation")
    if name == "train":
        raise ValueError("train is a fitting window; use fit_pairs(CUT['train'])")
    lo, hi = window(name)
    start = lo - 1                                                   # last month of the previous window
    return _pairs(lambda t, h: (t >= start) & (t + h >= lo) & (t + h <= hi), frac)


def fit_cut_for(name):
    """The last target month a model scored on `name` may have been fitted on."""
    return {"validation": CUT["train"], "test": CUT["validation"], "stress": CUT["test"]}[name]


def describe(n_series=C.n_series(), frac=FRAC):
    out = {}
    for name in NAMES:
        lo, hi = window(name)
        if name == "train":
            t, h = fit_pairs(hi, frac)
        else:
            t, h = eval_pairs(name, frac, unlock=True)
        out[name] = {"target_first": month(lo), "target_last": month(hi), "months": hi - lo + 1, "pairs": int(len(t)), "rows": int(len(t)) * n_series,
                     "horizons": int(len(np.unique(h))), "max_horizon": int(h.max())}
    t, h = fit_pairs(CUT["stress"], frac)
    out["deploy_fit"] = {"target_last": month(CUT["stress"]), "pairs": int(len(t)), "rows": int(len(t)) * n_series}
    return out
