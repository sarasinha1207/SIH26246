"""
v4 phase 4 - shared helpers for training, tuning and scoring the 60-month models.

Target: the log change y = log(level at t + h) - log(level at t) of employed workers (E), vacancies (V) or registered seekers (S), one XGBoost model per target
with the horizon as an input.  Scores are on the level scale: WAPE = sum |forecast - actual| / sum actual, in percent.

Model inputs are the candidate features of features.py without
  * the time proxies (as in v3),
  * the group aggregates (sector, trade and state-sector cell growth): they are identical for every series in a group, so with only ten years of training months they
    identify the calendar month and let the trees memorise the era (validation ablation, reports/v4/evaluation/ablation_validation.csv),
  * the district and tier identity columns (cat_district, cat_tier): near-unique identities that add capacity to memorise district histories without helping the validation score.
"""
import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import features as F
import splits as SP

GROUP_PREFIXES = ("sec_", "trd_", "ss_")
DROP_IDENTITY = ("cat_district", "cat_tier")
BANDS = [(1, 12), (13, 24), (25, 36), (37, 48), (49, 60)]
BAND_LABELS = [f"{a}-{b}" for a, b in BANDS]
BASE_PARAMS = dict(objective="reg:squarederror", tree_method="hist", nthread=14, max_bin=128, eta=0.05)


def load_world(df=None, dim=None):
    """PanelData, origin features and seasonal profiles of the panel (the file written by generate.py unless a frame is given)."""
    df = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet") if df is None else df
    dim = pd.read_csv(C.DATA / "dim_series.csv") if dim is None else dim
    D = F.PanelData(df, dim)
    OF, SF = F.origin_features(D)
    return D, OF, SF


def input_columns(columns, feature_set="chosen"):
    """Model inputs among the assembled columns for a named feature set (used by the ablation; 'chosen' is the one the models use)."""
    drop_groups = feature_set != "all_candidates"
    out = []
    for c in columns:
        if c in F.EVAL_ONLY:
            continue
        if drop_groups and c.startswith(GROUP_PREFIXES):
            continue
        if feature_set in ("chosen", "no_identity") and c in DROP_IDENTITY:
            continue
        if feature_set == "no_identity" and c.startswith("cat_"):
            continue
        out.append(c)
    return out


def build(D, OF, SF, t, h, feature_set="chosen", rows=None):
    """Feature matrix X and meta for the (origin, horizon) pairs; `rows` = (fraction, seed) keeps a random part of the rows;
    feature_set=None keeps every assembled column (for the ablation)."""
    X, meta = F.assemble(D, OF, SF, t, h)
    if rows is not None:
        keep = np.random.default_rng(rows[1]).random(len(X)) < rows[0]
        X, meta = X[keep].reset_index(drop=True), meta[keep].reset_index(drop=True)
    if feature_set is not None:
        X = X[input_columns(X.columns, feature_set)]
    return X, meta


def target(D, meta, k):
    return F.target_change(D, meta, k)


def base_log(D, meta, k):
    return D.L[k][meta.series_row.to_numpy(), meta.origin_idx.to_numpy()]


def wape(pred_change, actual_change, base):
    """Level-scale WAPE in percent."""
    a = np.exp(base.astype(np.float64) + actual_change)
    p = np.exp(base.astype(np.float64) + pred_change)
    return float(np.abs(p - a).sum() / a.sum() * 100)


def band_of(horizon):
    return pd.cut(np.asarray(horizon), [0] + [b for _, b in BANDS], labels=BAND_LABELS).astype(str)


def band_wapes(pred, actual, base, horizon, mask=None):
    """WAPE for each horizon band (NaN where a band has no rows)."""
    b = band_of(horizon)
    out = {}
    for lab in BAND_LABELS:
        m = b == lab if mask is None else (b == lab) & mask
        out[lab] = wape(pred[m], actual[m], base[m]) if m.any() else np.nan
    return out


def baselines(X, meta, k):
    """Simple forecasts of the log change: no change, seasonal naive (same month of the last year) and a damped trend with the seasonal shift."""
    h = meta.horizon.to_numpy()
    ya, sh, m36 = X[f"{k}_ya_h"].to_numpy(), X[f"{k}_sf_shift"].to_numpy(), X[f"{k}_mom36_pa"].to_numpy()
    return {"naive": np.zeros(len(X)), "seasonal_naive": np.nan_to_num(ya),
            "damped_trend": np.nan_to_num(h / 12.0 * m36 * 0.5 + sh)}


def objective(pred, actual, base, horizon):
    """Tuning score: the mean of the five horizon-band WAPEs (long horizons count as much as short ones)."""
    return float(np.nanmean(list(band_wapes(pred, actual, base, horizon).values())))


def dtrain(X, y):
    return xgb.QuantileDMatrix(X, y, enable_categorical=True, max_bin=BASE_PARAMS["max_bin"])


def ddata(X):
    return xgb.DMatrix(X, enable_categorical=True)
