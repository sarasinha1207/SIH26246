#!/usr/bin/env python3
"""
v4 phase 6 - the 2026-2030 forecast for every series.

Origin 2025-12, horizons 1..60.  For each of the 7,925 district-trade series the three deployed seed ensembles (deploy_fit.py) forecast the log change of employed workers (E),
vacancies (V) and registered seekers (S); the tree count per horizon is the one chosen on validation.  Then
  * ranges: the usual and the wide 90% range of phase 5 (data/v4/interval_calibration.csv), added to the forecast on the log scale;
  * reconciliation: the five trades of a district-sector add up exactly to the district-sector count (largest-remainder rounding of the trade forecasts to whole persons);
  * confidence labels of phase 5 (data/v4/confidence_cells.csv) per target, trade, horizon band and volume class;
  * early-warning flags of phase 5 from the forecast vacancy-to-seeker coverage (percentile among the districts of the same trade, same month).
Writes data/v4/exports/forecast_series.parquet (git-ignored; shipped through the compact exports of exports.py).

Run: python src/v4/forecast.py [--models deploy|stress] [--out DIR]       (--models stress is a dry run with the evaluation models, for development only)
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

import config as C
import early_warning as EW
import evaluate as EV
import model_lib as M

EXPORTS = C.DATA / "exports"
ORIGIN_IDX = C.N_MONTHS - 1


def load_boosters(model_dir, k):
    files = sorted(Path(model_dir).glob(f"{k}_seed*_*.json"))
    assert len(files) == len(EV.SEEDS), f"{model_dir} {k}: expected {len(EV.SEEDS)} seed models, found {len(files)}"
    out = []
    for f in files:
        b = xgb.Booster()
        b.load_model(str(f))
        out.append(b)
    return out


def point_forecasts(model_dir):
    """Log-level forecasts for every series and horizon 1..60 from origin 2025-12: dict k -> (base_log (n,), pred_change (n, 60)) and the features' series order."""
    best = json.loads((EV.OUT / "best_params.json").read_text(encoding="utf-8"))
    D, OF, SF = M.load_world()
    n = D.L["E"].shape[0]
    h = np.tile(np.arange(1, 61, dtype=np.int32), 1)
    X, me = M.build(D, OF, SF, np.full(60, ORIGIN_IDX, np.int32), h)
    assert len(X) == 60 * n and list(me.series_row.iloc[:n]) == list(range(n)), "row layout: horizon-major, series order within a horizon"
    de = M.ddata(X)
    out = {}
    for k in "EVS":
        pr = EV.predict_by_horizon(load_boosters(model_dir, k), de, me.horizon.to_numpy(), best[k]["trees_by_band"])
        out[k] = (D.L[k][:, ORIGIN_IDX].astype(np.float64), pr.reshape(60, n).T)             # (n, 60)
    return out, D


def reconcile(points, group):
    """Round the trade forecasts to whole persons so that the trades of a district-sector add up to the rounded district-sector total.
    points: (n, 60) floats; group: (n,) district-sector id.  Largest-remainder rounding inside each group and month."""
    order = np.argsort(group, kind="stable")
    g = group[order]
    starts = np.r_[0, np.where(np.diff(g) != 0)[0] + 1]
    size = np.diff(np.r_[starts, len(g)])
    assert (size == size[0]).all(), "every district-sector has the same number of trades"
    m = size[0]
    x = points[order].reshape(len(starts), m, -1)
    floor = np.floor(x)
    total = np.rint(x.sum(axis=1))                                          # (groups, 60)
    extra = (total - floor.sum(axis=1)).astype(int)                         # whole persons still to hand out, 0..m-1
    rank = np.argsort(np.argsort(-(x - floor), axis=1, kind="stable"), axis=1, kind="stable")
    out = floor + (rank < extra[:, None, :])
    res = np.empty_like(points)
    res[order] = out.reshape(len(g), -1)
    return res


def forecast(model_dir):
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    stats = pd.read_csv(C.DATA / "dim_series_stats.csv")
    cal = pd.read_csv(C.DATA / "interval_calibration.csv")
    cells = pd.read_csv(C.DATA / "confidence_cells.csv")
    pts, D = point_forecasts(model_dir)
    n = len(dim)
    assert list(dim.Series_ID) == list(D.sid), "dim_series order must be the panel order"
    grp = pd.factorize(dim.District_LGD_Code.astype(str) + "|" + dim.Sector_Code)[0]
    cols = {"series_row": np.repeat(np.arange(n), 60), "horizon": np.tile(np.arange(1, 61), n)}
    flat = lambda a: np.asarray(a).reshape(-1)                              # noqa: E731  (n, 60) -> series-major rows
    band = M.band_of(cols["horizon"])
    low_vol = stats.Low_Volume_Current.to_numpy()[cols["series_row"]]
    trade = dim.Trade_Code.to_numpy()[cols["series_row"]]
    levels = {}
    for k in "EVS":
        base, chg = pts[k]
        raw = np.exp(base[:, None] + chg)                                   # unrounded point forecast
        levels[k] = reconcile(raw, grp)
        t = cal[cal.target == k]
        assert not t.scheme.iloc[0].startswith("h_scaled"), "scaled schemes are not deployed"
        key = pd.MultiIndex.from_arrays([dim.Sector_Name.to_numpy()[cols["series_row"]] if t.scheme.iloc[0] == "h_sector" else np.full(n * 60, "all"), cols["horizon"]])
        t = t.set_index(["group", "horizon"])
        for nm in ("lo", "hi", "lo_wide", "hi_wide"):
            off = t[nm].reindex(key).to_numpy()
            assert np.isfinite(off).all()
            cols[f"{k}_{nm}"] = np.rint(flat(raw) * np.exp(off)).astype(np.int64)
        cols[k] = flat(levels[k]).astype(np.int64)
        for nm in ("lo", "lo_wide"):                                         # a range always contains its own point forecast (whole-person rounding can put it a person outside)
            cols[f"{k}_{nm}"] = np.minimum(cols[f"{k}_{nm}"], cols[k])
        for nm in ("hi", "hi_wide"):
            cols[f"{k}_{nm}"] = np.maximum(cols[f"{k}_{nm}"], cols[k])
        cc = cells[cells.target == k].set_index(["trade", "band"])
        lab_col = np.where(low_vol, cc.label_low_volume.reindex(pd.MultiIndex.from_arrays([trade, band])).to_numpy(), cc.label_normal_volume.reindex(pd.MultiIndex.from_arrays([trade, band])).to_numpy())
        cols[f"{k}_confidence"] = lab_col
    out = pd.DataFrame(cols)
    # flags: forecast coverage log(V/S) of the point forecasts, percentile among the districts of the trade in each target month
    cov = np.log(np.maximum(out.V, 0.5)) - np.log(np.maximum(out.S, 0.5))
    pc = (pd.DataFrame({"x": cov, "t": trade, "h": out.horizon}).groupby(["t", "h"]).x.rank(pct=True) * 100).to_numpy()
    out["coverage_pct"] = pc.astype(np.float32)
    out["flag_code"] = EW.flag_code(pc).astype(np.int8)
    out.insert(0, "Series_ID", dim.Series_ID.to_numpy()[out.series_row])
    out.insert(2, "month", C.FORECAST_MONTHS[out.horizon.to_numpy() - 1].astype(str))
    return out, dim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="deploy", choices=("deploy", "stress"))
    ap.add_argument("--out", default=str(EXPORTS))
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out, _ = forecast(C.MODELS / a.models)
    out.to_parquet(out_dir / "forecast_series.parquet", index=False)
    print(f"{len(out):,} rows written to {out_dir / 'forecast_series.parquet'}")


if __name__ == "__main__":
    main()
