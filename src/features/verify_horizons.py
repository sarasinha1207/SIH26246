#!/usr/bin/env python3
"""Phase 5 check: selection used horizons 1/3/6/12; confirm the selected feature sets also work for all 12 horizons.
Trains the probe on fold F3 (train targets <= 2023-12) with the selected features and reports WAPE by horizon against the baselines.
Output: reports/features/selection_G_all_horizons.csv"""
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
from select_features import PROBE, wape  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    rows = []
    for k in "EVS":
        X, y, w, meta = pl.training_frame(k, "2023-12-01")
        Xv, yv, _, mv = pl.validation_frame(k, "2023-12-01", 12)
        m = lgb.LGBMRegressor(**PROBE).fit(X, y, sample_weight=w)
        base = pl.spec()[k]["base"]
        pred = np.exp(mv[f"{base}_{k}"].to_numpy() + m.predict(Xv))
        act = np.exp(mv[f"target_{k}"].to_numpy())
        h = mv.horizon.to_numpy()
        _, ex = pl._examples()
        last = np.exp(ex.loc[mv.index, f"last_{k}"].to_numpy())
        snd = np.exp(ex.loc[mv.index, f"last_{k}"].to_numpy() + ex.loc[mv.index, f"{k}_yadrift_h"].to_numpy())
        for hh in range(1, 13):
            s = h == hh
            rows.append(dict(target=k, horizon=hh, n=int(s.sum()), probe_wape=wape(act[s], pred[s]), last_value_wape=wape(act[s], last[s]),
                             seasonal_naive_drift_wape=wape(act[s], snd[s])))
        print(k, "done", flush=True)
    out = pd.DataFrame(rows).round(2)
    out.to_csv(ROOT / "reports" / "features" / "selection_G_all_horizons.csv", index=False)
    print(out.groupby("target")[["probe_wape", "last_value_wape", "seasonal_naive_drift_wape"]].mean().round(2))


if __name__ == "__main__":
    main()
