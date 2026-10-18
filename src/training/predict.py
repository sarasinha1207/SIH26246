#!/usr/bin/env python3
"""
Phase 7 - load the saved XGBoost checkpoint and forecast.

    from predict import Forecaster
    fc = Forecaster.load("models/xgboost_v1")
    out = fc.predict(frame)         # frame: rows in the split-file layout (feature columns + last_/sm3_/sm6_ base columns + horizon)

Command line (reads a split file or any parquet in the same layout):
    python src/training/predict.py --split validation --out forecasts_validation.parquet
    python src/training/predict.py --input my_rows.parquet --out my_forecasts.parquet
The test split is refused unless --unlock-test is given (Phase 8 only).

Output columns, per target k in E/V/S: pred_k (count), lo90_k, hi90_k (90% interval from the saved residual quantiles) and pred_log_k.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocess import FeaturePreprocessor  # noqa: E402

KEYS = ("E", "V", "S")


class Forecaster:
    def __init__(self, models, pre, params, intervals, manifest):
        self.models, self.pre, self.params, self.intervals, self.manifest = models, pre, params, intervals, manifest

    @classmethod
    def load(cls, folder=ROOT / "models" / "xgboost_v1"):
        folder = Path(folder)
        manifest = json.load(open(folder / "checkpoint_manifest.json"))
        params = json.load(open(folder / "params.json"))
        pre = {k: FeaturePreprocessor.from_dict(d) for k, d in json.load(open(folder / "preprocessor.json")).items()}
        models = {}
        for k in KEYS:
            models[k] = []
            for sd in params[k]["seeds"]:
                m = xgb.XGBRegressor()
                m.load_model(folder / f"{k}_seed{sd}.ubj")
                models[k].append(m)
        intervals = json.load(open(folder / "intervals.json"))["by_target_horizon"]
        return cls(models, pre, params, intervals, manifest)

    def required_columns(self):
        cols = set()
        for k in KEYS:
            cols |= set(self.params[k]["features"]) | {f"{self.params[k]['base']}_{k}"}
        return sorted(cols)

    def predict(self, df, targets=KEYS):
        missing = [c for c in self.required_columns() if c not in df.columns]
        if missing:
            raise KeyError(f"input is missing columns: {missing}")
        out = pd.DataFrame(index=df.index)
        for c in ("Series_ID", "origin_date", "target_date", "horizon"):
            if c in df.columns:
                out[c] = df[c]
        for k in targets:
            p = self.params[k]
            Z = self.pre[k].transform(df[p["features"]])
            change = np.mean([m.predict(Z) for m in self.models[k]], axis=0)
            lvl = df[f"{p['base']}_{k}"].to_numpy() + change
            lo = np.array([self.intervals[k][str(int(h))][0] for h in df["horizon"]])
            hi = np.array([self.intervals[k][str(int(h))][1] for h in df["horizon"]])
            out[f"pred_log_{k}"] = lvl
            out[f"pred_{k}"] = np.exp(lvl)
            out[f"lo90_{k}"] = np.exp(lvl + lo)
            out[f"hi90_{k}"] = np.exp(lvl + hi)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default=str(ROOT / "models" / "xgboost_v1"))
    ap.add_argument("--split", choices=["train", "validation", "test"])
    ap.add_argument("--input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--unlock-test", action="store_true")
    a = ap.parse_args()
    if bool(a.split) == bool(a.input):
        ap.error("give exactly one of --split or --input")
    if a.split:
        import splits as sp
        df = sp.load_split(a.split, unlock_test=a.unlock_test)
    else:
        df = pd.read_parquet(a.input)
    fc = Forecaster.load(a.model_dir)
    out = fc.predict(df)
    out.to_parquet(a.out, index=False)
    print(f"{len(out):,} rows -> {a.out}")


if __name__ == "__main__":
    main()
