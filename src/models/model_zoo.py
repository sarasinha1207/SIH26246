"""
Phase 6 - candidate model families, all fed the Phase 5 features / bases / training policy.

Learners (global, one model per target; the horizon is a feature):
    lightgbm            gradient-boosted trees, the Phase 5 probe settings
    lightgbm_per_horizon  the same learner trained separately for each horizon
    hist_gbm            scikit-learn HistGradientBoostingRegressor
    xgboost             XGBoost (hist tree method, leaf-wise growth, settings mirroring the two models above)
    random_forest       scikit-learn RandomForestRegressor
    ridge               linear model on standardised, median-imputed features
    mlp                 small neural network (64-32) on standardised, median-imputed features
Statistical (per sector, per target):  holt_winters  damped-trend additive seasonal smoothing on the log scale
Baselines (no learning):               last_value, seasonal_naive_drift, last_plus_seasonal_shift, sm3_plus_seasonal_shift
All predictions are changes in log level relative to the Phase 5 base; callers add the base and exponentiate.
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.optimize import minimize
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LGB_DEFAULT = dict(objective="regression", n_estimators=250, learning_rate=0.08, num_leaves=31, min_child_samples=100, feature_fraction=0.8,
                   bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, n_jobs=-1, verbose=-1, random_state=42)


# XGBoost settings chosen to mirror the LightGBM / HistGradientBoosting defaults: leaf-wise trees with 31 leaves, learning rate 0.08,
# at least 100 samples per leaf (min_child_weight = 100 for squared error), 80% row and column sampling, L2 penalty 5.
XGB_DEFAULT = dict(n_estimators=250, learning_rate=0.08, tree_method="hist", grow_policy="lossguide", max_depth=0, max_leaves=31, min_child_weight=100,
                   subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0, n_jobs=-1, random_state=42, verbosity=0)


class Learner:
    """fit(X, y, w) / predict(X) wrapper around one scikit-learn-style estimator."""

    def __init__(self, est):
        self.est = est

    def fit(self, X, y, w=None):
        try:
            self.est.fit(X, y, sample_weight=w) if w is not None else self.est.fit(X, y)
        except TypeError:
            self.est.fit(X, y)
        return self

    def predict(self, X):
        return self.est.predict(X)


class PerHorizon:
    """One LightGBM per horizon."""

    def __init__(self, params=None):
        self.params = params or LGB_DEFAULT
        self.models = {}

    def fit(self, X, y, w=None):
        for h, idx in X.groupby("horizon").groups.items():
            self.models[h] = lgb.LGBMRegressor(**self.params).fit(X.loc[idx], y.loc[idx], sample_weight=None if w is None else pd.Series(w, index=X.index).loc[idx])
        return self

    def predict(self, X):
        out = np.zeros(len(X))
        for h, m in self.models.items():
            sel = (X["horizon"] == h).to_numpy()
            if sel.any():
                out[sel] = m.predict(X[sel])
        return out


def make_model(name, params=None):
    if name == "lightgbm":
        return Learner(lgb.LGBMRegressor(**(params or LGB_DEFAULT)))
    if name == "xgboost":
        import xgboost as xgb
        return Learner(xgb.XGBRegressor(**(params or XGB_DEFAULT)))
    if name == "lightgbm_per_horizon":
        return PerHorizon(params)
    if name == "hist_gbm":
        return Learner(HistGradientBoostingRegressor(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=100, l2_regularization=5.0,
                                                     random_state=42))
    if name == "random_forest":
        return Learner(RandomForestRegressor(n_estimators=120, min_samples_leaf=40, max_features=0.4, n_jobs=-1, random_state=42))
    if name == "ridge":
        return Learner(make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0)))
    if name == "mlp":
        return Learner(make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                     MLPRegressor(hidden_layer_sizes=(64, 32), early_stopping=True, validation_fraction=0.1, max_iter=120,
                                                  learning_rate_init=1e-3, random_state=42)))
    raise KeyError(name)


# ------------------------------------------------------------------------------------------------------------------------------
# Baselines: predictions as changes relative to the base, taken from the example frame
# ------------------------------------------------------------------------------------------------------------------------------
def baseline_log_level(ex, k, name):
    """Predicted log level for the rows of `ex` (the full example frame, indexed like the training frames)."""
    last = ex[f"last_{k}"].to_numpy()
    if name == "last_value":
        return last
    if name == "seasonal_naive_drift":
        return last + ex[f"{k}_yadrift_h"].to_numpy()
    sf = np.nan_to_num(ex[f"{k}_sf_shift"].to_numpy(), nan=0.0)
    if name == "last_plus_seasonal_shift":
        return last + sf
    if name == "sm3_plus_seasonal_shift":
        return ex[f"sm3_{k}"].to_numpy() + sf
    raise KeyError(name)


BASELINES = ["last_value", "seasonal_naive_drift", "last_plus_seasonal_shift", "sm3_plus_seasonal_shift"]


# ------------------------------------------------------------------------------------------------------------------------------
# Holt-Winters (damped additive trend, additive seasonality, log scale), parameters shared within a sector
# ------------------------------------------------------------------------------------------------------------------------------
def _hw_run(Y, params, collect=False):
    """Filter all series of Y (n x T, NaN = no update) with (alpha, beta, gamma, phi).  Returns one-step SSE (and states if collect)."""
    a, b_, g, phi = params
    n, T = Y.shape
    level = np.nanmean(Y[:, :12], axis=1)
    trend = (np.nanmean(Y[:, 12:24], axis=1) - level) / 12.0
    seas = np.nan_to_num(Y[:, :12] - level[:, None])
    sse, cnt = 0.0, 0
    Ls, Bs, Ss = (np.zeros((n, T)), np.zeros((n, T)), np.zeros((n, T, 12))) if collect else (None, None, None)
    for t in range(12, T):
        m = t % 12
        pred = level + phi * trend + seas[:, m]
        y = Y[:, t]
        ok = ~np.isnan(y)
        err = np.where(ok, y - pred, 0.0)
        sse += float((err ** 2).sum())
        cnt += int(ok.sum())
        yeff = np.where(ok, y, pred)
        new_level = a * (yeff - seas[:, m]) + (1 - a) * (level + phi * trend)
        trend = b_ * (new_level - level) + (1 - b_) * phi * trend
        seas[:, m] = g * (yeff - new_level) + (1 - g) * seas[:, m]
        level = new_level
        if collect:
            Ls[:, t], Bs[:, t], Ss[:, t, :] = level, trend, seas
    return (sse / max(cnt, 1), (Ls, Bs, Ss)) if collect else sse / max(cnt, 1)


class HoltWinters:
    """Per target and sector: fit shared smoothing parameters on the training window, then filter forward so every origin has its own state."""

    def __init__(self):
        self.params = {}

    def fit_predict(self, L, sector, shock, train_end, rows):
        """L: (series, T) log levels; shock: (T,) bool months not to learn from; rows: DataFrame[series_row, origin_idx, horizon].
        Returns predicted log level for each row."""
        n, T = L.shape
        Y = np.where(shock[None, :], np.nan, L)
        out = np.full(len(rows), np.nan)
        sr, oi, hh = rows.series_row.to_numpy(), rows.origin_idx.to_numpy(), rows.horizon.to_numpy()
        for s in np.unique(sector):
            m = sector == s
            Ytr = Y[m][:, :train_end + 1]
            best = minimize(lambda p: _hw_run(Ytr, p), x0=[0.3, 0.03, 0.1, 0.95], method="L-BFGS-B",
                            bounds=[(0.01, 0.99), (0.001, 0.3), (0.001, 0.99), (0.8, 1.0)])
            self.params[s] = best.x
            _, (Ls, Bs, Ss) = _hw_run(Y[m], best.x, collect=True)
            idx_series = np.where(m)[0]
            pos = {g: i for i, g in enumerate(idx_series)}
            sel = np.isin(sr, idx_series)
            a, b_, g, phi = best.x
            for j in np.where(sel)[0]:
                i, t, h = pos[sr[j]], oi[j], hh[j]
                damp = sum(phi ** q for q in range(1, h + 1))
                out[j] = Ls[i, t] + damp * Bs[i, t] + Ss[i, t, (t + h) % 12]
        return out
