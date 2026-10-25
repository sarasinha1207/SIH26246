#!/usr/bin/env python3
"""
v4 phase 3 - builds the small, tracked records of the split and feature design and measures what training will cost.

Writes
    data/v4/SPLITS_MANIFEST.json                 windows, sampling rule, pair counts and checksums of the (origin, horizon) pairs of every window
    data/v4/dim_series_stats.csv                 per-series volume statistics and the low-volume flags
    reports/v4/features/feature_catalogue.csv    every candidate feature: group, time proxy or not, horizon dependence, first month available
    reports/v4/features/phase3_build.json        size, time and missing-value shares of the training matrix

Run: python src/v4/build_phase3.py     (about two minutes)
"""
import hashlib
import json
import time

import numpy as np
import pandas as pd

import config as C
import features as F
import splits as SP

LOW_VOLUME_VACANCIES = 50                  # as in v3: median monthly vacancies below this make a series 'low volume'
OUT_R = C.REPORTS / "features"


def pair_hash(t, h):
    return hashlib.sha256(np.ascontiguousarray(np.stack([t, h])).tobytes()).hexdigest()


def main():
    OUT_R.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = pd.read_parquet(C.DATA / "raw" / "trade_monthly_2000_2025.parquet")
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    D = F.PanelData(df, dim)
    OF, SF = F.origin_features(D)
    t_feat = time.time() - t0

    # volume statistics: 'train' = the last 24 months of the training window (used to group evaluation rows), 'current' = the last 24 months of history (used to label forecasts)
    st = dim[["Series_ID"]].copy()
    for k in F.KEYS:
        st[f"Median_{k}_train"] = np.median(D.X[k][:, SP.CUT["train"] - 23:SP.CUT["train"] + 1], axis=1)
    st["Median_V_current"] = np.median(D.X["V"][:, -24:], axis=1)
    st["Low_Volume_Train"] = st.Median_V_train < LOW_VOLUME_VACANCIES
    st["Low_Volume_Current"] = st.Median_V_current < LOW_VOLUME_VACANCIES
    st.to_csv(C.DATA / "dim_series_stats.csv", index=False)

    # the training matrix of the first window, built once to measure it
    t, h = SP.fit_pairs(SP.CUT["train"])
    t1 = time.time()
    X, meta = F.assemble(D, OF, SF, t, h)
    t_asm = time.time() - t1
    cat = F.feature_catalogue(OF, X)
    cat.to_csv(OUT_R / "feature_catalogue.csv", index=False)
    inputs = [c for c in X.columns if c not in F.EVAL_ONLY]
    nan_share = X[[c for c in inputs if c not in X.select_dtypes("category").columns]].isna().mean()
    build = {"series": D.nS, "months": F.T, "candidate_features": int(len(cat)), "model_inputs": int(len(inputs)), "time_proxies_excluded": sorted(F.TIME_PROXY_FEATURES),
             "origin_features_seconds": round(t_feat, 1), "train_window_rows": int(len(X)), "train_window_columns": int(X.shape[1]), "train_window_matrix_mb": round(X.memory_usage().sum() / 1e6),
             "train_window_assembly_seconds": round(t_asm, 1), "inputs_all_missing_in_train_window": sorted(nan_share[nan_share == 1.0].index),
             "inputs_partly_missing_in_train_window": {k: round(float(v), 3) for k, v in nan_share[(nan_share > 0) & (nan_share < 1)].sort_values(ascending=False).head(15).items()},
             "categorical_levels": {k: len(v) for k, v in D.cat_levels.items()}, "low_volume_series_train": int(st.Low_Volume_Train.sum()), "low_volume_series_current": int(st.Low_Volume_Current.sum())}
    (OUT_R / "phase3_build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")

    man = {"history": [C.HISTORY_START, C.HISTORY_END], "horizons": [1, SP.MAX_H], "min_origin": SP.MIN_ORIGIN, "sampling_fraction": SP.FRAC, "min_origins_per_horizon": SP.MIN_PER_HORIZON,
           "seed": C.SEED, "windows": {k: {"first_target": SP.month(SP.window(k)[0]), "last_target": SP.month(SP.window(k)[1]), "fitted_on_targets_up_to": (SP.month(SP.fit_cut_for(k)) if k != "train" else None)}
                                          for k in SP.NAMES}, "counts": SP.describe(), "pair_sha256": {}, "rule": SP.__doc__.split("Sampling:")[0].strip()}
    man["pair_sha256"]["train_fit"] = pair_hash(*SP.fit_pairs(SP.CUT["train"]))
    for name in ("validation", "test", "stress"):
        man["pair_sha256"][name] = pair_hash(*SP.eval_pairs(name, unlock=True))
    man["pair_sha256"]["deploy_fit"] = pair_hash(*SP.fit_pairs(SP.CUT["stress"]))
    (C.DATA / "SPLITS_MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(json.dumps({k: build[k] for k in ("candidate_features", "model_inputs", "origin_features_seconds", "train_window_rows", "train_window_matrix_mb", "train_window_assembly_seconds",
                                            "inputs_all_missing_in_train_window", "low_volume_series_train", "low_volume_series_current")}, indent=2))


if __name__ == "__main__":
    main()
