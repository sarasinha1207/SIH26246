"""Phase 7 - feature preprocessing fitted on the training split only.

Steps (all statistics come from the train rows; validation, test and live data are only transformed):
    1. missing values  -> replaced by the training median of the feature (the training split has none, so this is a safeguard for new data)
    2. scaling         -> continuous features standardised with the training mean and standard deviation; calendar / horizon codes are left as they are
Gradient-boosted trees split on thresholds, so a monotone rescaling does not change their predictions (checked in reports/training/preprocessing_check.json);
the step is kept so that the same pipeline can feed linear or neural challengers and so that scaling statistics are explicitly train-only.
The fitted object is stored as JSON (no pickle), so a checkpoint stays readable across library versions.
"""
import json

import numpy as np
import pandas as pd

DISCRETE = ("horizon", "origin_month", "target_month", "target_month_sin", "target_month_cos")


class FeaturePreprocessor:
    def __init__(self, features):
        self.features = list(features)
        self.continuous = [c for c in self.features if c not in DISCRETE]
        self.fitted = False
        self.fitted_on_train_only = True

    def fit(self, X, split_names, allowed=("train",)):
        """`split_names`: the values of the `split` column of the rows being fitted; by default only {'train'} is allowed (Phase 8 refits may add 'validation', never 'test')."""
        if not set(split_names) <= set(allowed) or "test" in set(split_names):
            raise ValueError(f"preprocessing statistics may be fitted on {sorted(allowed)} only, got {sorted(set(split_names))}")
        Z = X[self.features].astype(float)
        self.median = Z.median().to_dict()
        self.mean = Z[self.continuous].mean().to_dict()
        std = Z[self.continuous].std(ddof=0).replace(0.0, 1.0)
        self.std = std.to_dict()
        self.n_rows = int(len(Z))
        self.fitted_on_train_only = set(split_names) == {"train"}
        self.n_missing_in_fit = int(Z.isna().sum().sum())
        self.fitted = True
        return self

    def transform(self, X):
        if not self.fitted:
            raise RuntimeError("preprocessor is not fitted")
        Z = X[self.features].astype(float)
        Z = Z.fillna(pd.Series(self.median))
        Z[self.continuous] = (Z[self.continuous] - pd.Series(self.mean)) / pd.Series(self.std)
        return Z

    def to_dict(self):
        return {"features": self.features, "continuous": self.continuous, "median": self.median, "mean": self.mean, "std": self.std,
                "n_rows": self.n_rows, "n_missing_in_fit": self.n_missing_in_fit, "fitted_on": "train split only" if self.fitted_on_train_only else "train + validation splits"}

    @classmethod
    def from_dict(cls, d):
        p = cls(d["features"])
        p.median, p.mean, p.std = d["median"], d["mean"], d["std"]
        p.n_rows, p.n_missing_in_fit, p.fitted = d["n_rows"], d["n_missing_in_fit"], True
        return p

    def save(self, path):
        json.dump(self.to_dict(), open(path, "w"), indent=1)

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.load(open(path)))
