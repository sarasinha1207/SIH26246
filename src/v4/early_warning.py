#!/usr/bin/env python3
"""
v4 phase 5 - trade-level early-warning flags and confidence labels.

Flags compare the forecast labour-market tightness of a (district, trade) with the other districts of the same trade in the same target month.
    coverage  = vacancies / registered seekers (log), forecast = (base_V + predicted_V) - (base_S + predicted_S)
    percentile of the forecast coverage among all districts of the trade (the same origin and horizon, so one target month)
    Shortage alert    percentile >= 90        Shortage watch    75 <= percentile < 90
    Oversupply alert  percentile <= 10        Oversupply watch  10 < percentile <= 25
The flags are RELATIVE (as in v3): about 10% of districts are in each tail by construction, so a shortage alert means "among the tightest districts for this trade",
and the absolute coverage is shown beside it.  What is tested is whether the districts flagged for month t+h are the ones that are in the tail then.
    truth   shortage: the actual coverage of the target month is in the top decile of its trade (top quartile for the watch level);  oversupply: bottom decile (bottom quartile)
    precision = share of flagged series whose truth holds;  recall = share of truth series that were flagged;  lift = precision / base rate
    benchmark: persistence, the same percentile rules applied to the coverage at the origin (nothing forecast)
A flag is issued for every series; the confidence label says how far to trust it (low-volume series have noisy monthly counts).

Confidence labels (per target, trade, horizon band and series):  the level-scale WAPE that earlier out-of-sample forecasts of the same trade and horizon band reached -
High up to HIGH_WAPE percent, Medium up to MEDIUM_WAPE, otherwise Low - and a low-volume series is one level lower.  (The calibrated intervals depend on horizon, sector and
volume only, so they cannot tell one series from another; the cell error can tell trades apart.)  A label is only useful if the observed error rises from High to Low, which is
checked on the windows after the one the labels were taken from.

Run: python src/v4/early_warning.py [deploy]     (needs predictions_<window>.parquet from predictions.py; 'deploy' writes data/v4/confidence_cells.csv)
"""
import numpy as np
import pandas as pd

import config as C
import intervals as IV
import model_lib as M

OUT = C.REPORTS / "evaluation"
ALERT, WATCH = 90.0, 75.0                        # percentile cut points of the shortage flags; the oversupply flags use 100 - cut
HIGH_WAPE, MEDIUM_WAPE = 8.0, 20.0               # confidence labels: expected WAPE (percent) of the trade and horizon band in earlier windows
LABELS = ["High", "Medium", "Low"]
FLAGS = ["Shortage alert", "Shortage watch", "Oversupply watch", "Oversupply alert"]
EVAL_BANDS = [("1-12", 1, 12), ("13-24", 13, 24), ("25-36", 25, 36), ("37-48", 37, 48), ("49-60", 49, 60)]


def cohort_percentile(df, col, trade):
    """Percentile (0-100) of `col` among the series of the same trade, origin and horizon."""
    g = pd.DataFrame({"x": col, "trade": trade, "o": df.origin_idx.to_numpy(), "h": df.horizon.to_numpy()})
    return (g.groupby(["trade", "o", "h"]).x.rank(pct=True) * 100).to_numpy()


def flag_code(p):
    """0 shortage alert, 1 shortage watch, 2 none, 3 oversupply watch, 4 oversupply alert (NaN stays NaN)."""
    c = np.full(len(p), 2.0)
    c[p <= 100 - WATCH] = 3
    c[p >= WATCH] = 1
    c[p <= 100 - ALERT] = 4
    c[p >= ALERT] = 0
    c[np.isnan(p)] = np.nan
    return c


def coverage_frame(df, trade):
    """Forecast, actual and origin (persistence) log coverage with their cohort percentiles."""
    f = (df.base_V + df.pred_V) - (df.base_S + df.pred_S)
    a = (df.base_V + df.act_V) - (df.base_S + df.act_S)
    n = df.base_V - df.base_S
    out = pd.DataFrame({"origin_idx": df.origin_idx.to_numpy(), "horizon": df.horizon.to_numpy(), "volume": df.volume.to_numpy(), "shock": df.shock_S.to_numpy()})
    for nm, x in (("fc", f), ("act", a), ("now", n)):
        out[f"p_{nm}"] = cohort_percentile(df, x.to_numpy(np.float64), trade)
    return out


def flag_table(cf, window):
    """Precision, recall, lift of the flags (model and persistence) by horizon band and volume class."""
    rows = []
    band = pd.cut(cf.horizon, [0] + [b for _, _, b in EVAL_BANDS], labels=[b for b, _, _ in EVAL_BANDS]).astype(str)
    for vol in ("all", "normal", "low"):
        sel_v = np.ones(len(cf), bool) if vol == "all" else (cf.volume == vol).to_numpy()
        for bname in [b for b, _, _ in EVAL_BANDS] + ["all horizons"]:
            m = sel_v if bname == "all horizons" else sel_v & (band == bname).to_numpy()
            if not m.any():
                continue
            c = cf[m]
            for source, pcol in (("model", "p_fc"), ("persistence", "p_now")):
                code = flag_code(c[pcol].to_numpy())
                for name, k_codes, truth_dec, truth_qtr in (
                        ("Shortage alert", (0,), c.p_act >= ALERT, c.p_act >= WATCH),
                        ("Shortage watch", (1,), c.p_act >= ALERT, c.p_act >= WATCH),
                        ("Oversupply watch", (3,), c.p_act <= 100 - ALERT, c.p_act <= 100 - WATCH),
                        ("Oversupply alert", (4,), c.p_act <= 100 - ALERT, c.p_act <= 100 - WATCH)):
                    flagged = np.isin(code, k_codes)
                    n = int(flagged.sum())
                    dec, qtr = truth_dec.to_numpy(), truth_qtr.to_numpy()
                    # recall is for the union of alert and watch of the same direction: share of the tail that was flagged at either level
                    both = np.isin(code, (0, 1)) if name.startswith("Shortage") else np.isin(code, (3, 4))
                    rows.append({"window": window, "source": source, "volume": vol, "band": bname, "flag": name, "flagged": n, "base_rate_decile": dec.mean(),
                                 "precision_decile": dec[flagged].mean() if n else np.nan, "precision_quartile": qtr[flagged].mean() if n else np.nan,
                                 "lift_decile": dec[flagged].mean() / dec.mean() if n else np.nan, "recall_decile_alert_or_watch": (dec & both).sum() / max(dec.sum(), 1)})
    return pd.DataFrame(rows)


def cell_wape(df, k, trade):
    """Observed level-scale WAPE (percent) of earlier out-of-sample forecasts for each (trade, horizon band) cell; the index of the result is (trade, band)."""
    act = np.exp(df[f"base_{k}"].to_numpy(np.float64) + df[f"act_{k}"].to_numpy(np.float64))
    err = np.abs(np.exp(df[f"base_{k}"].to_numpy(np.float64) + df[f"pred_{k}"].to_numpy(np.float64)) - act)
    g = pd.DataFrame({"trade": trade, "band": M.band_of(df.horizon.to_numpy()), "err": err, "act": act}).groupby(["trade", "band"])
    return g.err.sum() / g.act.sum() * 100


def label_from_wape(wape, low_volume):
    """High / Medium / Low from the expected error of the cell; a low-volume series is one level lower (monthly counts of a few workers are noisy)."""
    lev = np.where(np.asarray(wape) <= HIGH_WAPE, 0, np.where(np.asarray(wape) <= MEDIUM_WAPE, 1, 2))
    lev = np.minimum(lev + np.asarray(low_volume).astype(int), 2)
    return np.array(LABELS, dtype=object)[lev]


def confidence_table(df, k, trade, cells, window):
    """Observed WAPE by confidence label (and horizon band) of the forecasts of one target, labels taken from the cell errors of the earlier windows."""
    band = M.band_of(df.horizon.to_numpy())
    w = cells.reindex(pd.MultiIndex.from_arrays([trade, band])).to_numpy()
    lab = label_from_wape(w, (df.volume == "low").to_numpy())
    act = np.exp(df[f"base_{k}"].to_numpy(np.float64) + df[f"act_{k}"].to_numpy(np.float64))
    prd = np.exp(df[f"base_{k}"].to_numpy(np.float64) + df[f"pred_{k}"].to_numpy(np.float64))
    rows = []
    for b in M.BAND_LABELS + ["all horizons"]:
        mb = np.ones(len(df), bool) if b == "all horizons" else band == b
        for L in LABELS:
            m = mb & (lab == L)
            if m.any():
                rows.append({"window": window, "target": k, "band": b, "label": L, "rows": int(m.sum()), "share": m.sum() / mb.sum(),
                             "wape_pct": np.abs(prd[m] - act[m]).sum() / act[m].sum() * 100})
    return pd.DataFrame(rows)


def main():
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    wins = {w: IV.load(w) for w in ("validation", "test", "stress")}
    plan = [("test", ["validation"]), ("stress", ["validation", "test"])]
    flag_tabs, conf_tabs = [], []
    for w, cal_w in plan:
        df = wins[w]
        cal = pd.concat([wins[x] for x in cal_w], ignore_index=True)
        cf = coverage_frame(df, dim.Trade_Code.to_numpy()[df.series_row.to_numpy()])
        flag_tabs.append(flag_table(cf, w))
        tr = dim.Trade_Code.to_numpy()[df.series_row.to_numpy()]
        for k in "EVS":
            cells = cell_wape(cal, k, dim.Trade_Code.to_numpy()[cal.series_row.to_numpy()])
            conf_tabs.append(confidence_table(df, k, tr, cells, w))
        print(w, "done", flush=True)
    pd.concat(flag_tabs).round(4).to_csv(OUT / "flag_precision.csv", index=False)
    pd.concat(conf_tabs).round(4).to_csv(OUT / "confidence_labels.csv", index=False)


def deploy():
    """Cell errors for the 2026-2030 labels: 'calm' = validation + test windows, 'all' = also the stress window.  The label is taken from the calm error."""
    dim = pd.read_csv(C.DATA / "dim_series.csv")
    wins = {w: IV.load(w) for w in ("validation", "test", "stress")}
    calm, everything = pd.concat([wins["validation"], wins["test"]], ignore_index=True), pd.concat(list(wins.values()), ignore_index=True)
    rows = []
    for k in "EVS":
        a = cell_wape(calm, k, dim.Trade_Code.to_numpy()[calm.series_row.to_numpy()])
        b = cell_wape(everything, k, dim.Trade_Code.to_numpy()[everything.series_row.to_numpy()])
        t = pd.DataFrame({"wape_calm_pct": a, "wape_all_windows_pct": b}).reset_index()
        t.insert(0, "target", k)
        t["label_normal_volume"] = label_from_wape(t.wape_calm_pct, np.zeros(len(t), bool))
        t["label_low_volume"] = label_from_wape(t.wape_calm_pct, np.ones(len(t), bool))
        rows.append(t)
    out = pd.concat(rows)
    out.round(3).to_csv(C.DATA / "confidence_cells.csv", index=False)
    print("confidence cells", len(out))


if __name__ == "__main__":
    import sys
    deploy() if sys.argv[1:] == ["deploy"] else main()
