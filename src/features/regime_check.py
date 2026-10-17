#!/usr/bin/env python3
"""Phase 5 check of EDA decision D2: does an explicit calendar-regime indicator (post_covid, eshram_progress) help?
These are excluded from the candidate pool as calendar-time proxies; this tests whether that cost accuracy on fold F3, the only fold
where the flags are not constant.  Output: reports/features/selection_H_regime_check.csv"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_features as sf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    C = sf.Ctx()
    ex = C.ex
    spec = json.load(open(ROOT / "data" / "processed" / "features" / "feature_sets.json"))["targets"]
    OF, _ = sf.en.origin_features(C.D)
    rows = []
    key = "F3_2024"
    for k in "EVS":
        s = spec[k]
        tr, va, _ = sf.fold_split(C, key, k, s["mask_shock_windows"])
        rows.append(dict(target=k, rows_train=int(tr.sum()), train_rows_with_post_covid=int(ex.loc[tr, "post_covid"].sum())))
        for name, extra in [("final", []), ("final + post_covid", ["post_covid"]), ("final + post_covid + eshram_progress", ["post_covid", "eshram_progress"])]:
            r = sf.probe(C, key, k, s["features"] + extra, base=s["base"], mask_train=s["mask_shock_windows"], halflife=None)
            rows.append(dict(target=k, feature_set=name, wape=r["wape"], h1=r["h1"], h3=r["h3"], h6=r["h6"], h12=r["h12"]))
    out = pd.DataFrame(rows)
    out.round(3).to_csv(ROOT / "reports" / "features" / "selection_H_regime_check.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
