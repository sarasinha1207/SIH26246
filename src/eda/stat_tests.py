"""Small statistical helpers for the EDA (no statsmodels dependency)."""
import numpy as np

ADF_CRIT_5PCT = -2.89      # Dickey-Fuller, constant included, about 100 observations (MacKinnon)


def adf_tstat(y, maxlag=12):
    """Augmented Dickey-Fuller t-statistic with a constant.  Lag length chosen by AIC on a common sample.

    H0: unit root.  A t-statistic below ADF_CRIT_5PCT rejects H0 (the series looks stationary)."""
    y = np.asarray(y, float)
    dy = np.diff(y)
    n = len(dy) - maxlag
    if n < 25:
        return np.nan
    Y = dy[maxlag:]
    best = None
    for p in range(maxlag + 1):
        cols = [np.ones(n), y[maxlag:-1]] + [dy[maxlag - i:len(dy) - i] for i in range(1, p + 1)]
        X = np.column_stack(cols)
        beta = np.linalg.lstsq(X, Y, rcond=None)[0]
        e = Y - X @ beta
        sse = float(e @ e)
        aic = n * np.log(sse / n + 1e-300) + 2 * X.shape[1]
        if best is None or aic < best[0]:
            cov = np.linalg.pinv(X.T @ X) * sse / (n - X.shape[1])
            best = (aic, beta[1] / np.sqrt(cov[1, 1]))
    return float(best[1])


def adf_rejects(y, maxlag=12):
    t = adf_tstat(y, maxlag)
    return np.nan if np.isnan(t) else float(t < ADF_CRIT_5PCT)
