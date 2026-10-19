"""
Phase 9 - data access and features for deployment.

The processed panel runs to 2026-12, but 2026-11 and 2026-12 are simulated months after today's date (Phase 2 decision).  Deployment treats the panel as history only up to the
chosen forecast origin: everything later is cut off before any feature is built, so a forecast cannot see it.  The test split of Phase 7/8 is spent, so its months are
ordinary history here; the Phase 3 role locks (`load_panel`) are not used.

    panel = load_history("2026-10")                                  # rows with Date <= origin
    train_rows, D = training_rows(panel)                             # every (series, origin, horizon) example whose target is inside the history
    new_rows, D = forecast_rows(panel)                               # one row per series and horizon 1..12 for the last origin of the history (targets in the future)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for sub in ("features", "splits", "common"):
    sys.path.insert(0, str(ROOT / "src" / sub))
import engineering as en  # noqa: E402
import make_splits as ms  # noqa: E402

PANEL = ROOT / "data" / "processed" / "panel_monthly.parquet"
N_SERIES, HORIZONS = 280, list(range(1, 13))


def load_history(origin):
    """Panel rows up to and including the origin month (a 'YYYY-MM' string)."""
    o = pd.Period(origin, "M").to_timestamp()
    df = pd.read_parquet(PANEL)
    df = df[df.Date <= o].reset_index(drop=True)
    for c in df.select_dtypes("category"):
        df[c] = df[c].cat.remove_unused_categories()
    assert df.Date.max() == o, f"the panel has no data for {origin}"
    assert df.Series_ID.nunique() == N_SERIES and df.groupby("Series_ID", observed=True).size().nunique() == 1
    return df


def training_rows(panel):
    """All examples with a known target (the same columns as the split files), labelled split='deploy'."""
    ex, D, _ = ms.build_examples(panel)
    ex.insert(0, "split", "deploy")
    return ex, D


def forecast_rows(panel):
    """Rows for the last month of the panel as origin, horizons 1..12 (targets are after the panel and unknown)."""
    D = en.PanelData(panel)
    OF, SF = en.origin_features(D)
    last = D.T - 1
    ex = en.make_categorical(en.build_examples(D, OF, SF, horizons=HORIZONS, origin_min=last, origin_max=last, need_target=False), D)
    ex = ex[ex.origin_idx == last].copy()
    ex["origin_date"] = D.dates[ex.origin_idx.to_numpy()]
    ex["target_date"] = [o + pd.DateOffset(months=int(h)) for o, h in zip(ex.origin_date, ex.horizon)]
    ex["target_date"] = pd.to_datetime(ex["target_date"])
    ex["sector"] = D.sector[ex.series_row.to_numpy()]
    ex["state"] = D.meta.State_Name.to_numpy()[ex.series_row.to_numpy()]
    ex["district"] = D.meta.District_Name.to_numpy()[ex.series_row.to_numpy()]
    ex = ex.reset_index(drop=True)
    assert len(ex) == N_SERIES * len(HORIZONS)
    return ex, D
