#!/usr/bin/env python3
"""
Phase 8 (A5) - are the early-warning flag gains over persistence statistically real?

Flags (Phase 5 definitions, applied to single-month V/S coverage): a district-sector is in the "tightest decile" (shortage) if its coverage ratio V/S is at or above the 90th
percentile of the 56 districts of its sector in the target month, and in the "loosest decile" (saturation) at or below the 10th.  Persistence flags the same event
from today's percentile; the model flags it from the forecast percentile (employed unused; vacancies from the model, seekers from the declared blend).
Uncertainty: two paired bootstraps of the difference model minus persistence in precision and in recall, 2000 resamples each -
  (a) over the 280 series (cluster bootstrap), and (b) moving blocks of 6 target months (keeps month-to-month dependence).
Reads the saved test predictions only.   Run: python src/evaluation/flag_significance.py   Writes reports/evaluation/test/flag_significance.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
import splits as sp  # noqa: E402

B = 2000
BLOCK = 6


def flag_rows(pred, test):
    pv, ps = pred[pred.target == "V"].reset_index(drop=True), pred[pred.target == "S"].reset_index(drop=True)
    d = test.reset_index(drop=True).copy()
    d["act"] = np.exp(pv.actual_log - ps.actual_log)
    d["fc"] = np.exp(pv.primary - ps.cv_blend)
    d["now"] = np.exp(d.last_V - d.last_S)
    d = d[~ps["shock"].to_numpy()]
    return d


def main():
    pred = pd.read_parquet(ROOT / "data" / "interim" / "phase8_test_predictions.parquet")
    test = sp.load_split("test", unlock_test=True, verify=True, columns=["Series_ID", "sector", "origin_idx", "target_idx", "horizon", "last_V", "last_S"])
    d = flag_rows(pred, test)
    rng = np.random.default_rng(11)
    out = []
    for h in (1, 3, 6, 12):
        g = d[d.horizon == h].copy()
        g["p_act"] = g.groupby(["sector", "target_idx"]).act.rank(pct=True) * 100
        g["p_fc"] = g.groupby(["sector", "target_idx"]).fc.rank(pct=True) * 100
        g["p_now"] = g.groupby(["sector", "origin_idx"]).now.rank(pct=True) * 100
        for label, ev in (("shortage (top decile)", lambda x: x >= 90), ("saturation (bottom decile)", lambda x: x <= 10)):
            y, fm, fp = ev(g.p_act).to_numpy(), ev(g.p_fc).to_numpy(), ev(g.p_now).to_numpy()
            comp = pd.DataFrame({"s": g.Series_ID.to_numpy(), "t": g.target_idx.to_numpy(), "y": y, "tpm": fm & y, "fm": fm, "tpp": fp & y, "fp": fp})
            prec = lambda a, b: a / np.maximum(b, 1)  # noqa: E731

            def stats(c):
                s = c[["y", "tpm", "fm", "tpp", "fp"]].sum()
                return prec(s.tpm, s.fm) - prec(s.tpp, s.fp), prec(s.tpm, s.y) - prec(s.tpp, s.y), prec(s.tpm, s.fm), prec(s.tpp, s.fp)
            dp, dr, pm, pp = stats(comp)
            ser = comp.groupby("s")[["y", "tpm", "fm", "tpp", "fp"]].sum()
            mon = comp.groupby("t")[["y", "tpm", "fm", "tpp", "fp"]].sum()
            res = {"series": [], "block": []}
            n_s, n_m = len(ser), len(mon)
            for _ in range(B):
                s = ser.iloc[rng.integers(0, n_s, n_s)].sum()
                res["series"].append((prec(s.tpm, s.fm) - prec(s.tpp, s.fp), prec(s.tpm, s.y) - prec(s.tpp, s.y)))
                starts = rng.integers(0, n_m - BLOCK + 1, int(np.ceil(n_m / BLOCK)))
                idx = np.concatenate([np.arange(a, a + BLOCK) for a in starts])[:n_m]
                s = mon.iloc[idx].sum()
                res["block"].append((prec(s.tpm, s.fm) - prec(s.tpp, s.fp), prec(s.tpm, s.y) - prec(s.tpp, s.y)))
            row = dict(horizon=h, event=label, rows=len(g), precision_model=pm, precision_persistence=pp, diff_precision=dp, diff_recall=dr)
            for kind in ("series", "block"):
                a = np.array(res[kind])
                row[f"{kind}_precision_ci"] = f"{np.quantile(a[:, 0], 0.025):+.3f} to {np.quantile(a[:, 0], 0.975):+.3f}"
                row[f"{kind}_recall_ci"] = f"{np.quantile(a[:, 1], 0.025):+.3f} to {np.quantile(a[:, 1], 0.975):+.3f}"
                row[f"{kind}_share_resamples_model_better_precision"] = float((a[:, 0] > 0).mean())
            out.append(row)
    R = pd.DataFrame(out)
    R.to_csv(ROOT / "reports" / "evaluation" / "test" / "flag_significance.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
