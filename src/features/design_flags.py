#!/usr/bin/env python3
"""Phase 5 (D7): evaluate the relative early-warning flags on train + validation data (2011-2024).

Checks: (1) the classes are not degenerate in any sector-year; (2) the flags persist (percentile rank year to year);
(3) forward-looking value: how well does today's percentile (persistence) and the trailing trend predict an extreme decile 12 months
later?; (4) the seat-versus-demand mismatch indicator.
Outputs: reports/features/flags_*.csv, flags_summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_access import load_panel  # noqa: E402
import engineering as en  # noqa: E402
import flags as fl  # noqa: E402

REP = ROOT / "reports" / "features"


def main():
    D = en.PanelData(load_panel("monthly"))
    R = fl.relative_flags(D)
    labels = fl.status_labels(R["status_code"])
    sec, years = D.sector, D.dates.year.to_numpy()
    shock = D.covid | D.policy
    # (1) class shares by sector-year
    rows = []
    for s in np.unique(sec):
        for y in sorted(set(years)):
            sel = (sec == s)[:, None] & (years == y)[None, :]
            lab = labels[sel]
            lab = lab[lab != ""]
            if len(lab):
                vc = pd.Series(lab).value_counts(normalize=True)
                rows.append(dict(sector=s, year=y, **{k: float(vc.get(k, 0.0)) for k in fl.STATUSES}))
    shares = pd.DataFrame(rows)
    shares.round(3).to_csv(REP / "flags_class_shares.csv", index=False)
    summ = {"typical_share_range": [round(float(shares.Typical.min()), 3), round(float(shares.Typical.max()), 3)],
            "mean_share": shares[fl.STATUSES].mean().round(3).to_dict(),
            "max_single_class_share": round(float(shares[fl.STATUSES].max().max()), 3),
            "sector_years_with_4plus_classes": int(((shares[fl.STATUSES] > 0).sum(axis=1) >= 4).sum()), "sector_years": len(shares)}
    # (2) persistence: rank correlation of the percentile 12 months apart
    pct = R["cov_pct"]
    per = []
    for s in np.unique(sec):
        m = sec == s
        rho = [stats.spearmanr(pct[m][:, t], pct[m][:, t + 12])[0] for t in range(24, D.T - 12)
               if not (shock[t] or shock[t + 12])]
        per.append(float(np.mean(rho)))
    summ["pct_rank_persistence_12m"] = round(float(np.mean(per)), 3)
    # (3) forward-looking value of the pieces: persistence benchmark and the (rejected) trailing trend
    def auc(score, event):
        """P(score of an event row > score of a non-event row)."""
        ev_, ne_ = score[event], score[~event]
        if len(ev_) == 0 or len(ne_) == 0:
            return np.nan
        return float(stats.mannwhitneyu(ev_, ne_).statistic / (len(ev_) * len(ne_)))

    rows3, bench = [], []
    pool = {k: [] for k in ("p0", "p1", "tr")}
    for t in range(24, D.T - 12):
        if shock[t] or shock[t + 12]:
            continue
        for k, v in (("p0", pct[:, t]), ("p1", pct[:, t + 12]), ("tr", R["cov_trend_rel"][:, t])):
            pool[k].append(v)
    p0, p1, tr = (np.concatenate(pool[k]) for k in ("p0", "p1", "tr"))
    ok = ~(np.isnan(p0) | np.isnan(p1) | np.isnan(tr))
    p0, p1, tr = p0[ok], p1[ok], tr[ok]
    for name, extreme_next in (("saturation", p1 <= 10), ("shortage", p1 >= 90)):
        sgn = -1.0 if name == "saturation" else 1.0           # higher score = higher risk
        not_yet = (p0 > 10) if name == "saturation" else (p0 < 90)
        rows3.append(dict(event=f"in the {name} decile 12 months later", n=int(len(p0)), base_rate=float(extreme_next.mean()),
                          auc_current_percentile=auc(sgn * p0, extreme_next),
                          auc_trailing_trend_among_not_yet_extreme=auc(sgn * tr[not_yet], extreme_next[not_yet])))
        # persistence benchmark: flag = in the extreme decile (or the outer 30%) now
        for cut in (10, 20, 30):
            flag = (p0 <= cut) if name == "saturation" else (p0 >= 100 - cut)
            tp = int((flag & extreme_next).sum())
            bench.append(dict(event=name, flag_if_percentile_within=cut, precision=tp / max(int(flag.sum()), 1), recall=tp / max(int(extreme_next.sum()), 1)))
    lift = pd.DataFrame(rows3)
    lift.round(3).to_csv(REP / "flags_forward_value.csv", index=False)
    pd.DataFrame(bench).round(3).to_csv(REP / "flags_persistence_benchmark.csv", index=False)
    summ["forward_value"] = lift.round(3).to_dict("records")
    summ["persistence_benchmark"] = pd.DataFrame(bench).round(3).to_dict("records")
    # (4) seat mismatch
    sm = R["seat_mismatch"]
    srow = []
    for s in np.unique(sec):
        for y in (2012, 2016, 2019, 2024):
            sel = (sec == s)[:, None] & (years == y)[None, :]
            v = sm[sel]
            v = v[~np.isnan(v)]
            srow.append(dict(sector=s, year=y, share_over_allocated=float((v > fl.SEAT_ALERT).mean()), share_under_allocated=float((v < -fl.SEAT_ALERT).mean()),
                             median=float(np.median(v))))
    pd.DataFrame(srow).round(3).to_csv(REP / "flags_seat_mismatch.csv", index=False)
    json.dump(summ, open(REP / "flags_summary.json", "w"), indent=2)
    print(json.dumps(summ, indent=2))
    print(lift.round(3).to_string(index=False)); print(pd.DataFrame(bench).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
