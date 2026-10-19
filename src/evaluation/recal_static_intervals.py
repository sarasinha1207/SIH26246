#!/usr/bin/env python3
"""
Phase 8 (B2, vacancies) - the adaptive conformal intervals made vacancies and employed workers worse (see evaluate_v3.py), so those targets keep static intervals.
Vacancy intervals under-covered at long horizons (85% at 12 months), so this script recalibrates the static quantiles for vacancies: per horizon, the 5% and 95% quantiles of
the signed log errors of the declared model on the ORIGINAL test split (spent, so this is a post-hoc calibration), written to models/xgboost_v3/vacancy_intervals_recalibrated.json.
The clean check is the two fresh synthetic draws (never used here): coverage and width there.     Run: python src/evaluation/recal_static_intervals.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for sub in ("common", "training", "evaluation"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import splits as sp  # noqa: E402
from predict import Forecaster  # noqa: E402

V3 = ROOT / "models" / "xgboost_v3"


def main():
    fc = Forecaster.load(V3 / "primary")
    test = sp.load_split("test", unlock_test=True, verify=True)
    p = fc.predict(test, targets=("V",))
    err = test["target_V"].to_numpy() - p["pred_log_V"].to_numpy()
    q = {}
    for h in range(1, 13):
        e = err[(test.horizon == h).to_numpy()]
        q[str(h)] = [float(np.quantile(e, 0.05)), float(np.quantile(e, 0.95))]
    json.dump({"target": "V", "level": [0.05, 0.95], "calibrated_on": "original test split (post-hoc); verify on fresh draws", "by_horizon": q}, open(V3 / "vacancy_intervals_recalibrated.json", "w"), indent=1)
    rows = []
    for label, src in (("original test (calibration data)", test), ("fresh seed 2027", pd.read_parquet(ROOT / "data/fresh_draws/seed_2027/data/splits/test.parquet")),
                       ("fresh seed 2028", pd.read_parquet(ROOT / "data/fresh_draws/seed_2028/data/splits/test.parquet"))):
        pr = fc.predict(src, targets=("V",))
        e = src["target_V"].to_numpy() - pr["pred_log_V"].to_numpy()
        h = src.horizon.to_numpy()
        for name, tab in (("static (fold-based)", fc.intervals["V"]), ("recalibrated static", q)):
            lo = np.array([tab[str(int(x))][0] for x in h]); hi = np.array([tab[str(int(x))][1] for x in h])
            ins = (e >= lo) & (e <= hi)
            rows.append(dict(source=label, intervals=name, coverage=ins.mean(), coverage_h1=ins[h == 1].mean(), coverage_h6=ins[h == 6].mean(), coverage_h12=ins[h == 12].mean(),
                             width_pct=float(100 * (np.exp(hi - lo) - 1).mean()), width_h12_pct=float(100 * (np.exp(hi - lo) - 1)[h == 12].mean())))
    R = pd.DataFrame(rows)
    R.to_csv(ROOT / "reports" / "evaluation" / "v3" / "vacancy_interval_recalibration.csv", index=False)
    pd.set_option("display.width", 250)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
