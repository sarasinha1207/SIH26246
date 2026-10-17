#!/usr/bin/env python3
"""
Phase 4 - Exploratory Data Analysis.

Uses ONLY the train and validation periods (2011-01 .. 2024-12) through src/common/data_access.load_panel; the locked
test period is never loaded.  Produces figures, tables and a findings file that docs/phases/PHASE_4_EDA.md is written from.

Outputs: reports/eda/figures/*.png, reports/eda/tables/*.csv, reports/eda/eda_findings.json
Run:     python src/eda/run_eda.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_access import load_panel  # noqa: E402
from stat_tests import adf_tstat, ADF_CRIT_5PCT  # noqa: E402

OUT = ROOT / "reports" / "eda"
FIG, TAB = OUT / "figures", OUT / "tables"
SECTORS = ["Manufacturing", "Construction", "IT-ITeS", "Healthcare", "Textiles and Apparel"]
# categorical slots 1-5 of the validated reference palette, fixed order (blue, orange, aqua, yellow, magenta)
COL = dict(zip(SECTORS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SEQ = LinearSegmentedColormap.from_list("blue_seq", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
BAND = "#e9e8e2"
TARGETS = {"E": "Total_Employed_Workers", "V": "Active_Job_Vacancies", "S": "eShram_Registered_Seekers"}
TNAME = {"E": "Employed workers", "V": "Job vacancies", "S": "Registered seekers"}
F = {}                                                  # findings

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"], "font.size": 9,
                     "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "lines.linewidth": 1.6})


def style(ax, grid="y"):
    ax.grid(axis="x" if grid == "x" else "y" if grid == "y" else "both")
    if grid == "y":
        ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)


def save(fig, name, title, sub=None, legend=True):
    """Title, subtitle and (optional) sector legend sit in their own rows above the plot area."""
    top = 0.80 if sub else 0.86
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.text(0.005, 0.985, title, ha="left", va="top", fontsize=11, color=INK, fontweight="semibold")
    if sub:
        fig.text(0.005, 0.985 - 0.065 * (4.2 / fig.get_figheight()), sub, ha="left", va="top", fontsize=8.5, color=INK2)
    if legend and getattr(fig, "_sector_legend", False):
        handles = [plt.Line2D([0], [0], color=COL[s_], lw=2) for s_ in SECTORS]
        fig.legend(handles, SECTORS, loc="upper left", ncol=5, bbox_to_anchor=(0.0, top + 0.035), fontsize=8, labelcolor=INK2,
                   handlelength=1.4, columnspacing=1.4)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def sector_legend(fig, y=0.99):
    fig._sector_legend = True


def shade(ax, cov, ramp=None):
    ax.axvspan(*cov, color=BAND, alpha=0.9, lw=0, zorder=0)
    if ramp is not None:
        ax.axvspan(*ramp, color=BAND, alpha=0.5, lw=0, zorder=0)


def wide(df, col):
    return df.pivot(index="Series_ID", columns="Date", values=col)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    df = load_panel("monthly", roles=("train", "validation"))
    assert df.Date.max() == pd.Timestamp("2024-12-01") and not (df.Split_Role.astype(str) == "test").any()
    df["Sector_Name"] = df.Sector_Name.astype(str)
    dates = pd.DatetimeIndex(sorted(df.Date.unique()))
    nT = len(dates)
    sid = sorted(df.Series_ID.astype(str).unique())
    df["Series_ID"] = df.Series_ID.astype(str)
    meta = df.drop_duplicates("Series_ID").set_index("Series_ID").loc[sid][["Sector_Name", "District_Name", "State_Name", "Econ_Tier"]]
    sec = meta.Sector_Name.to_numpy()
    tiers = meta.Econ_Tier.astype(str).to_numpy()
    states = meta.State_Name.astype(str).to_numpy()
    flag_by_date = df.drop_duplicates("Date").set_index("Date").loc[dates]
    cov_m, pol_m, ramp_m = (flag_by_date[c].to_numpy(bool) for c in ("Is_Covid_Window", "Is_Policy_Shock", "Is_Eshram_Ramp"))
    COV = (pd.Timestamp("2020-03-01"), pd.Timestamp("2022-02-01"))
    RAMP = (dates[ramp_m].min(), dates[ramp_m].max())
    A = {k: wide(df, v).loc[sid].to_numpy(float) for k, v in TARGETS.items()}
    L = {k: np.log(v) for k, v in A.items()}
    extra = {c: wide(df, c).loc[sid].to_numpy(float) for c in
             ["Avg_Monthly_Wage_INR", "Unemployment_Rate_Pct", "Female_Share_Pct", "Edu_Graduate_and_Above_Pct", "Age_15_24_Pct",
              "District_Total_Population_Est", "Training_Seats_Sanctioned", "Trainees_Certified_Monthly"]}
    F["scope"] = dict(rows=int(len(df)), series=len(sid), first=str(dates[0].date()), last=str(dates[-1].date()),
                      roles=sorted(df.Split_Role.astype(str).unique().tolist()), ramp=f"{RAMP[0]:%Y-%m}..{RAMP[1]:%Y-%m}")

    # ================================================================================================================
    # 1. Level, scale and trend by sector
    # ================================================================================================================
    nat = df.groupby(["Sector_Name", "Date"])[["Total_Employed_Workers", "Active_Job_Vacancies", "eShram_Registered_Seekers",
                                               "Training_Seats_Sanctioned", "Trainees_Certified_Monthly"]].sum()
    y24 = df[df.Year == 2024]
    summ = y24.groupby("Sector_Name").agg(Employed=("Total_Employed_Workers", "sum"), Vacancies=("Active_Job_Vacancies", "sum"),
                                          Seekers=("eShram_Registered_Seekers", "sum"), Seats=("Training_Seats_Sanctioned", "sum"),
                                          Certified=("Trainees_Certified_Monthly", "sum"), Wage=("Avg_Monthly_Wage_INR", "mean"),
                                          UR=("Unemployment_Rate_Pct", "mean")) / [12, 12, 12, 12, 1, 1, 1]
    summ["Seats"] = summ["Seats"] * 1.0
    ann = lambda s, col: nat.loc[s, col].groupby(nat.loc[s].index.year).mean()
    for s in SECTORS:
        e = ann(s, "Total_Employed_Workers")
        summ.loc[s, "Emp_CAGR_2011_2019_pct"] = 100 * ((e[2019] / e[2011]) ** (1 / 8) - 1)
        summ.loc[s, "Emp_CAGR_2022_2024_pct"] = 100 * ((e[2024] / e[2022]) ** (1 / 2) - 1)
    summ.round(2).to_csv(TAB / "t01_sector_summary_2024.csv")
    F["sector_summary"] = summ.round(2).to_dict("index")

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9), sharex=True)
    for ax, (k, col) in zip(axes, [("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies"), ("S", "eShram_Registered_Seekers")]):
        shade(ax, COV, RAMP if k == "S" else None)
        ends = {}
        for s in SECTORS:
            x = nat.loc[s, col]
            idx = 100 * x / x[x.index.year == 2011].mean()
            ax.plot(idx.index, idx.values, color=COL[s], lw=1.6)
            ends[s] = idx.values[-1]
        ax.set_yscale("log")
        ax.set_title(TNAME[k] + " (2011 average = 100, log scale)", loc="left", fontsize=9, color=INK2)
        style(ax)
        lo_, hi_ = ax.get_ylim()
        ax.set_yticks([t for t in (10, 20, 50, 100, 200, 400, 800, 1600) if lo_ <= t <= hi_])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    sector_legend(fig, 1.02)
    save(fig, "fig01_trends.png", "Every sector grows, but vacancies and seekers move very differently from employment",
         "National totals across the 56 districts, 2011-2024. Grey bands: COVID window; lighter band on the right panel: e-Shram registration ramp.")

    # ================================================================================================================
    # 2. Seasonality
    # ================================================================================================================
    months = dates.month.to_numpy()
    excl = cov_m | pol_m
    seas_rows, fig = [], None
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6), sharex=True)
    for ax, k in zip(axes, "EVS"):
        x = L[k].copy()
        ma = pd.DataFrame(x.T).rolling(13, center=True, min_periods=13).mean().to_numpy().T      # centred 13-month mean
        ratio = x - ma
        mask = excl | (ramp_m if k == "S" else np.zeros(nT, bool))
        ratio[:, mask] = np.nan
        ax.axhline(0, color=AXIS, lw=0.8)
        for s in SECTORS:
            r = ratio[sec == s]
            prof = np.array([np.nanmean(r[:, months == m]) for m in range(1, 13)])
            prof = prof - prof.mean()
            ax.plot(range(1, 13), 100 * prof, color=COL[s], lw=1.6, marker="o", ms=3)
            dev = r - np.nanmean(r, axis=1, keepdims=True)
            tot = np.nanvar(dev)
            expl = np.nanvar(prof[months - 1][None, :] * np.ones_like(r)) / tot if tot > 0 else np.nan
            groups = [r[:, months == m].ravel() for m in range(1, 13)]
            groups = [g[~np.isnan(g)] for g in groups]
            anova_p = float(stats.f_oneway(*groups)[1])
            seas_rows.append(dict(target=TNAME[k], sector=s, anova_p=anova_p, amplitude_pct=100 * (prof.max() - prof.min()),
                                  peak_month=int(prof.argmax() + 1), trough_month=int(prof.argmin() + 1),
                                  variance_share_pct=100 * expl))
        ax.set_xticks(range(1, 13))
        ax.set_title(TNAME[k] + ": % vs 13-month average", loc="left", fontsize=9, color=INK2)
        style(ax)
    sector_legend(fig, 1.02)
    save(fig, "fig02_seasonality.png", "Construction and Textiles & Apparel are strongly seasonal; IT-ITeS and Healthcare barely are",
         "Average month-of-year deviation from the centred 13-month mean; COVID, policy and e-Shram windows excluded.")
    st = pd.DataFrame(seas_rows)
    st[[c for c in st.columns if c != "anova_p"]] = st[[c for c in st.columns if c != "anova_p"]].apply(lambda col: col.round(2) if col.dtype.kind == "f" else col)
    st["anova_p"] = st.anova_p.map(lambda x: float(f"{x:.3g}"))
    st.to_csv(TAB / "t02_seasonality.csv", index=False)
    F["seasonality"] = st.to_dict("records")

    # ================================================================================================================
    # 3. COVID shock and recovery (national)
    # ================================================================================================================
    base_d = pd.Timestamp("2020-02-01")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.7), sharex=True)
    cov_rows = []
    for ax, (k, col) in zip(axes, [("E", "Total_Employed_Workers"), ("V", "Active_Job_Vacancies")]):
        ax.axhline(100, color=AXIS, lw=0.8)
        for s_ in SECTORS:
            x = nat.loc[s_, col]
            idx = 100 * x / x[base_d]
            w = idx["2019-06-01":]
            ax.plot(w.index, w.values, color=COL[s_], lw=1.6)
            lo = idx[COV[0]:COV[1]].min()
            first_wave = idx["2020-03-01":"2020-12-01"]               # surge measured in the first wave only (later gains are trend)
            hi = first_wave.max()
            trough = idx[COV[0]:COV[1]].idxmin()
            rec = None
            if lo < 100:
                back = idx[trough:] >= 100
                rec = (back.idxmax().to_period("M") - trough.to_period("M")).n if back.any() else None
            cov_rows.append(dict(target=TNAME[k], sector=s_, worst_decline_pct=round(min(lo - 100, 0), 1),
                                 trough_month=f"{trough:%Y-%m}" if lo < 100 else "",
                                 months_to_regain_feb2020=rec, peak_surge_pct=round(max(hi - 100, 0), 1),
                                 peak_month=f"{first_wave.idxmax():%Y-%m}" if hi > 100 else ""))
        ax.set_title(TNAME[k] + " (Feb 2020 = 100)", loc="left", fontsize=9, color=INK2)
        style(ax)
    sector_legend(fig, 1.02)
    save(fig, "fig03_covid.png", "COVID hit Construction, Textiles and Manufacturing; Healthcare vacancies surged",
         "National totals, indexed to Feb 2020. Vacancies react far more sharply than employment.")
    ct = pd.DataFrame(cov_rows)
    ct.to_csv(TAB / "t03_covid_impact.csv", index=False)
    F["covid"] = ct.to_dict("records")

    # ================================================================================================================
    # 4. Coverage (vacancies per registered seeker) over time
    # ================================================================================================================
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    shade(ax, COV, RAMP)
    cov_levels = {}
    for s in SECTORS:
        c = nat.loc[s, "Active_Job_Vacancies"] / nat.loc[s, "eShram_Registered_Seekers"]
        ax.plot(c.index, c.values, color=COL[s], lw=1.6)
        pre, post = c["2019-01-01":"2020-02-01"].mean(), c["2023-06-01":"2024-12-01"].mean()
        cov_levels[s] = dict(pre_covid=round(pre, 3), post_ramp=round(post, 3), ratio_post_over_pre=round(post / pre, 2))
    ax.axhline(1, color=AXIS, lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_title("Job vacancies per registered seeker (log scale); 1.0 = one opening per seeker", loc="left", fontsize=9, color=INK2)
    style(ax)
    sector_legend(fig, 1.04)
    save(fig, "fig04_coverage.png", "Coverage is far lower after the e-Shram launch in every sector except IT-ITeS",
         "National vacancies divided by registered seekers. The break is a registry change, not a labour-market shift.")
    F["coverage"] = cov_levels

    # ================================================================================================================
    # 5. District heterogeneity: density by tier, concentration
    # ================================================================================================================
    d24 = y24.assign(dens=y24.Total_Employed_Workers / y24.District_Total_Population_Est * 1000)
    heat = d24.groupby(["Econ_Tier", "Sector_Name"], observed=True).dens.mean().unstack()[SECTORS]
    heat = heat.loc[heat.mean(axis=1).sort_values(ascending=False).index]
    heat.round(1).to_csv(TAB / "t04_density_by_tier_per1000pop_2024.csv")
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    im = ax.imshow(np.log10(heat.values), cmap=SEQ, aspect="auto")
    ax.set_xticks(range(5), [s.replace(" and ", " &\n") for s in SECTORS], fontsize=8)
    ax.set_yticks(range(len(heat)), [t.replace("_", " ") for t in heat.index], fontsize=8)
    ax.grid(False)
    for i in range(heat.shape[0]):
        for j in range(5):
            v = heat.values[i, j]
            rgb = SEQ((np.log10(v) - np.log10(heat.values).min()) / np.ptp(np.log10(heat.values)))[:3]
            lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
            ax.text(j, i, f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", va="center", fontsize=8,
                    color=INK if lum > 0.45 else "#ffffff")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "fig05_density_heatmap.png", "Employment density differs by tier and sector: workers per 1,000 residents, 2024",
         "Cell colour is log-scaled; the numbers are the values. Rows ordered by overall density.")
    mfg_hub = heat.loc[["industrial_it_hub", "metro_core"], "Manufacturing"].mean()
    F["density"] = dict(it_ratio_top_tier_to_tribal=round(heat.loc["industrial_it_hub", "IT-ITeS"] / heat.loc["peripheral_tribal", "IT-ITeS"], 1),
                        mfg_ratio_hub_to_tribal=round(mfg_hub / heat.loc["peripheral_tribal", "Manufacturing"], 1))
    conc = {}
    for s in SECTORS:
        x = y24[y24.Sector_Name == s].groupby("District_Name", observed=True).Total_Employed_Workers.sum().sort_values(ascending=False)
        sh = x / x.sum()
        gini = (np.abs(x.values[:, None] - x.values[None, :]).sum()) / (2 * len(x) ** 2 * x.mean())
        conc[s] = dict(top5_share_pct=round(100 * sh.head(5).sum(), 1), top10_share_pct=round(100 * sh.head(10).sum(), 1),
                       gini=round(float(gini), 3), top_district=sh.index[0])
    F["concentration"] = conc
    pd.DataFrame(conc).T.to_csv(TAB / "t05_concentration_2024.csv")

    # ================================================================================================================
    # 6. Do district gaps persist? rank stability of coverage and of employment density
    # ================================================================================================================
    years = list(range(2011, 2025))
    cov_dist = (df.groupby(["Sector_Name", "District_Name", "Year"], observed=True)[["Active_Job_Vacancies", "eShram_Registered_Seekers"]].sum())
    cov_dist["cov"] = cov_dist.Active_Job_Vacancies / cov_dist.eShram_Registered_Seekers
    lagrows = []
    for s in SECTORS:
        p = cov_dist.loc[s]["cov"].unstack()
        for lag in (1, 2, 3, 5):
            rho = [stats.spearmanr(p[y], p[y + lag])[0] for y in years if y + lag in years and y >= 2011 and not (2020 <= y <= 2021 or 2020 <= y + lag <= 2021)]
            lagrows.append(dict(sector=s, lag_years=lag, mean_spearman=float(np.mean(rho))))
    lr = pd.DataFrame(lagrows)
    lr.round(3).to_csv(TAB / "t06_coverage_rank_stability.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    for s in SECTORS:
        r = lr[lr.sector == s]
        ax.plot(r.lag_years, r.mean_spearman, color=COL[s], marker="o", ms=4, lw=1.6)
    ax.set_xticks([1, 2, 3, 5], ["1 year", "2 years", "3 years", "5 years"])
    ax.set_ylim(0, 1.02)
    ax.set_title("Rank correlation of district coverage across years (1.0 = identical ranking)", loc="left", fontsize=9, color=INK2)
    style(ax)
    sector_legend(fig, 1.05)
    save(fig, "fig06_rank_stability.png", "District differences in coverage are persistent, so rankings are meaningful",
         "Mean Spearman correlation between a district's coverage rank in year t and t+lag, COVID years excluded.")
    F["rank_stability"] = lr.round(3).to_dict("records")

    # ================================================================================================================
    # 7. Autocorrelation of monthly changes (pooled over series)
    # ================================================================================================================
    def pooled_acf(logx, mask, maxlag=24):
        d = np.diff(logx, axis=1)
        dm = mask[:-1] | mask[1:]
        d = np.where(dm[None, :], np.nan, d)
        x = d - np.nanmean(d, axis=1, keepdims=True)
        out = []
        for k in range(1, maxlag + 1):
            a, b = x[:, :-k], x[:, k:]
            ok = ~np.isnan(a) & ~np.isnan(b)
            out.append((a[ok] * b[ok]).sum() / (np.nansum(np.where(ok, a, 0) ** 2) ** 0.5 * np.nansum(np.where(ok, b, 0) ** 2) ** 0.5))
        return np.array(out)

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4), sharey=True)
    acf = {}
    for ax, k in zip(axes, "EVS"):
        mask = excl | (ramp_m if k == "S" else np.zeros(nT, bool))
        a = pooled_acf(L[k], mask)
        acf[k] = a
        ax.axhline(0, color=AXIS, lw=0.8)
        ax.bar(range(1, 25), a, color="#2a78d6", width=0.55)
        ax.axhspan(-0.03, 0.03, color=BAND, lw=0)
        ax.set_xticks([1, 6, 12, 18, 24])
        ax.set_title(TNAME[k] + ": month-on-month change", loc="left", fontsize=9, color=INK2)
        style(ax)
    axes[0].set_ylabel("autocorrelation")
    save(fig, "fig07_acf.png", "Employment changes echo seasonally at lag 12; vacancy and seeker changes are dominated by noise (negative lag 1)",
         "Pooled autocorrelation of log changes across 280 series, shock windows excluded. Grey band: about +/-0.03.")
    F["acf"] = {k: dict(lag1=round(float(v[0]), 3), lag2=round(float(v[1]), 3), lag12=round(float(v[11]), 3), lag24=round(float(v[23]), 3),
                        max_abs_other=round(float(np.max(np.abs(np.delete(v, [11, 23])))), 3)) for k, v in acf.items()}

    # ================================================================================================================
    # 8. Lead / lag between vacancies and employment growth (year-on-year)
    # ================================================================================================================
    yo = lambda x: x[:, 12:] - x[:, :-12]
    win = np.convolve((excl | ramp_m).astype(int), np.ones(13, int), "valid") > 0
    yV, yE, yS = (np.where(win[None, :], np.nan, yo(L[k])) for k in "VES")

    def xcorr(a, b, lags=range(-12, 13)):
        res = []
        for k in lags:
            x, y = (a[:, :a.shape[1] - k], b[:, k:]) if k >= 0 else (a[:, -k:], b[:, :b.shape[1] + k])
            ok = ~np.isnan(x) & ~np.isnan(y)
            res.append(np.corrcoef(x[ok], y[ok])[0, 1])
        return np.array(res)

    lags = np.arange(-12, 13)
    xve, xvs = xcorr(yV, yE), xcorr(yV, yS)
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.plot(lags, xve, color="#2a78d6", marker="o", ms=3.5, lw=1.6)
    ax.plot(lags, xvs, color="#eb6834", marker="o", ms=3.5, lw=1.6)
    ax.set_xlabel("months (positive = vacancy growth leads)")
    ax.legend(["vacancy growth vs employment growth", "vacancy growth vs seeker growth"], loc="upper right", fontsize=8, labelcolor=INK2)
    ax.set_title("Cross-correlation of year-on-year growth rates", loc="left", fontsize=9, color=INK2)
    style(ax)
    save(fig, "fig08_leadlag.png", "Vacancy growth moves with employment growth, not ahead of it",
         "Pooled across series; COVID, policy and e-Shram windows excluded.")
    F["leadlag"] = dict(vac_vs_emp_peak_lag=int(lags[np.nanargmax(xve)]), vac_vs_emp_peak_corr=round(float(np.nanmax(xve)), 3),
                        vac_vs_emp_lag0=round(float(xve[12]), 3), vac_vs_seek_peak_lag=int(lags[np.nanargmax(np.abs(xvs))]),
                        vac_vs_seek_peak_corr=round(float(xvs[np.nanargmax(np.abs(xvs))]), 3), vac_vs_seek_lag0=round(float(xvs[12]), 3))

    # ================================================================================================================
    # 9. Which covariates carry signal about next-12-month growth?  (within sector x month rank correlation)
    # ================================================================================================================
    H = 12
    feats = {
        "log size (employed)": L["E"], "vacancy rate (V/E)": L["V"] - L["E"], "seeker rate (S/E)": L["S"] - L["E"],
        "employment momentum (12m)": np.pad(yo(L["E"]), ((0, 0), (12, 0)), constant_values=np.nan),
        "vacancy momentum (12m)": np.pad(yo(L["V"]), ((0, 0), (12, 0)), constant_values=np.nan),
        "employment momentum (3m)": np.pad(L["E"][:, 3:] - L["E"][:, :-3], ((0, 0), (3, 0)), constant_values=np.nan),
        "log wage": np.log(extra["Avg_Monthly_Wage_INR"]), "unemployment rate": extra["Unemployment_Rate_Pct"],
        "female share": extra["Female_Share_Pct"], "graduate share": extra["Edu_Graduate_and_Above_Pct"],
        "youth share (15-24)": extra["Age_15_24_Pct"], "log population": np.log(extra["District_Total_Population_Est"]),
        "training seats per 1,000 pop": np.log(extra["Training_Seats_Sanctioned"] / extra["District_Total_Population_Est"] * 1000),
    }
    tgt = {k: np.pad(L[k][:, H:] - L[k][:, :-H], ((0, 0), (0, H)), constant_values=np.nan) for k in "EVS"}
    ok_o = np.ones(nT, bool)
    ok_o[nT - H:] = False
    ok_o[:12] = False
    # origin and target windows must avoid shocks
    badwin = np.convolve((excl | ramp_m).astype(int), np.ones(H + 13, int), "full")
    for t in range(nT):
        lo, hi = max(0, t - 12), min(nT - 1, t + H)
        if (excl | ramp_m)[lo:hi + 1].any():
            ok_o[t] = False
    rows = []
    for tk in "EVS":
        long = []
        for name, M in feats.items():
            v = M[:, ok_o].ravel()
            long.append(pd.Series(v, name=name))
        X = pd.concat(long, axis=1)
        X["y"] = tgt[tk][:, ok_o].ravel()
        X["sector"] = np.repeat(sec, ok_o.sum())
        X["date"] = np.tile(dates[ok_o], len(sid))
        X = X.dropna()
        R = X.groupby(["sector", "date"]).rank(pct=True)
        for name in feats:
            rows.append(dict(target=TNAME[tk], feature=name, ic=float(np.corrcoef(R[name], R["y"])[0, 1])))
    ic = pd.DataFrame(rows)
    ic.round(3).to_csv(TAB / "t07_covariate_signal.csv", index=False)
    piv = ic.pivot(index="feature", columns="target", values="ic")
    piv = piv.loc[piv.abs().max(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    h = 0.26
    cols3 = ["#2a78d6", "#eb6834", "#1baf7a"]
    for j, tn in enumerate(TNAME.values()):
        ax.barh(np.arange(len(piv)) + (j - 1) * h, piv[tn].values, height=h * 0.9, color=cols3[j])
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.set_yticks(range(len(piv)), piv.index, fontsize=8)
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in cols3], list(TNAME.values()), loc="upper right", fontsize=8, labelcolor=INK2)
    ax.set_xlabel("rank correlation with next-12-month growth, within sector and month")
    style(ax, grid="x")
    save(fig, "fig09_covariate_signal.png", "Growth is predicted mainly by recent over- and under-shoots; wages, demographics and seat levels add almost nothing",
         "Within-sector, within-month rank correlation of each feature with the next-12-month log change. COVID, policy and e-Shram windows excluded.")
    F["signal"] = {tn: piv[tn].abs().sort_values(ascending=False).head(5).round(3).to_dict() for tn in TNAME.values()}
    F["signal_signed"] = {tn: piv[tn].round(3).to_dict() for tn in TNAME.values()}

    # ================================================================================================================
    # 10. Training capacity vs demand: is supply aligned with where vacancies are?
    # ================================================================================================================
    tdf = y24.groupby(["Sector_Name", "District_Name"], observed=True).agg(
        vac=("Active_Job_Vacancies", "mean"), seats=("Training_Seats_Sanctioned", "mean"), cert=("Trainees_Certified_Monthly", "sum"),
        emp=("Total_Employed_Workers", "mean"), pop=("District_Total_Population_Est", "mean")).reset_index()
    fig, axes = plt.subplots(1, 5, figsize=(14, 3.3))
    mism = []
    for ax, s in zip(axes, SECTORS):
        t = tdf[tdf.Sector_Name == s]
        sv, ss = t.vac / t.vac.sum(), t.seats / t.seats.sum()
        tv = 0.5 * np.abs(sv - ss).sum()
        r = stats.spearmanr(t.vac, t.seats)[0]
        mism.append(dict(sector=s, total_variation_distance=round(float(tv), 3), spearman_seats_vs_vacancies=round(float(r), 3),
                         seats_per_100_vacancies=round(float(100 * t.seats.sum() / t.vac.sum()), 1),
                         certified_to_vacancies_ratio=round(float(t.cert.sum() / t.vac.sum()), 2)))
        ax.scatter(t.vac, t.seats, s=14, color=COL[s], edgecolor=SURFACE, linewidth=0.6)
        lim = [min(t.vac.min(), t.seats.min()) * 0.8, max(t.vac.max(), t.seats.max()) * 1.2]
        ax.plot(lim, lim, color=AXIS, lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(s, loc="left", fontsize=8.5, color=INK2)
        ax.set_xlabel("vacancies (monthly avg)", fontsize=8)
        style(ax, grid="both")
    axes[0].set_ylabel("sanctioned seats")
    save(fig, "fig10_seats_vs_demand.png", "Training seats track district size closely; 16-19% of seats sit where vacancies do not call for them",
         "One dot per district, 2024, log scales. Dashed line: seats equal vacancies (units differ: annual seats vs a vacancy stock).")
    mm = pd.DataFrame(mism)
    mm.to_csv(TAB / "t08_training_vs_demand_2024.csv", index=False)
    F["training_vs_demand"] = mm.to_dict("records")
    tdf["gap"] = np.log((tdf.seats / tdf.groupby("Sector_Name").seats.transform("sum")) / (tdf.vac / tdf.groupby("Sector_Name").vac.transform("sum")))
    top = (tdf.reindex(tdf.gap.abs().sort_values(ascending=False).index).groupby("Sector_Name").head(2)[["Sector_Name", "District_Name", "gap"]])
    top.round(2).to_csv(TAB / "t09_largest_seat_demand_mismatches.csv", index=False)

    # ================================================================================================================
    # 11. Noise, volume and heteroscedasticity
    # ================================================================================================================
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.5))
    noise = {}
    for ax, k in zip(axes, "EVS"):
        mask = excl | (ramp_m if k == "S" else np.zeros(nT, bool))
        d1 = np.diff(L[k], axis=1)
        d2 = np.diff(d1, axis=1)
        m2 = mask[:-2] | mask[1:-1] | mask[2:]
        d2 = np.where(m2[None, :], np.nan, d2)
        sig = np.nanstd(d2, axis=1) / np.sqrt(6)                 # white-noise level implied by second differences
        lvl = np.nanmean(np.where(mask[None, :], np.nan, L[k]), axis=1) / np.log(10)
        rho = stats.spearmanr(lvl, sig)[0]
        noise[k] = dict(median_noise_pct=round(float(100 * np.median(sig)), 2), p10=round(float(100 * np.percentile(sig, 10)), 2),
                        p90=round(float(100 * np.percentile(sig, 90)), 2), spearman_level_vs_noise=round(float(rho), 3))
        ax.scatter(lvl, 100 * sig, s=12, color="#2a78d6", edgecolor=SURFACE, linewidth=0.5)
        ax.set_xlabel("log10 of average level")
        ax.set_title(TNAME[k] + ": noise vs size", loc="left", fontsize=9, color=INK2)
        style(ax, grid="both")
    axes[0].set_ylabel("implied monthly noise (%)")
    save(fig, "fig11_noise_vs_volume.png", "Noise is roughly proportional to the level: about 1% for employment, 4-5% for vacancies and seekers",
         "Each dot is a district-sector series. Noise = std of second differences of the log series / sqrt(6); shock windows excluded.")
    F["noise"] = noise

    # ================================================================================================================
    # 12. Baseline accuracy on the validation year (origin 2023-12) = what any model must beat
    # ================================================================================================================
    t0 = int(np.where(dates == pd.Timestamp("2023-12-01"))[0][0])
    rows = []
    for k in "EVS":
        X = A[k]
        # seasonally adjusted 3-month level, with month factors estimated only from data up to the origin
        ma = pd.DataFrame(L[k].T).rolling(13, center=True, min_periods=13).mean().to_numpy().T
        rr = L[k] - ma
        rr[:, excl | (ramp_m if k == "S" else np.zeros(nT, bool))] = np.nan
        rr[:, t0 - 5:] = np.nan                                  # centred window needs 6 later months: stay within data up to t0
        sf = np.array([np.nanmean(rr[:, months == m], axis=1) for m in range(1, 13)]).T
        sf = sf - sf.mean(axis=1, keepdims=True)
        lvl3 = (L[k] - sf[:, months - 1])[:, t0 - 2:t0 + 1].mean(axis=1)
        for h in (1, 3, 6, 12):
            y = X[:, t0 + h]
            preds = {"last value": X[:, t0], "mean of last 6 months": X[:, t0 - 5:t0 + 1].mean(axis=1),
                     "mean of last 12 months": X[:, t0 - 11:t0 + 1].mean(axis=1), "seasonal naive": X[:, t0 + h - 12],
                     "seasonal naive + drift": X[:, t0 + h - 12] * X[:, t0] / X[:, t0 - 12],
                     "seasonally adjusted 3-month level": np.exp(lvl3 + sf[:, months[t0 + h] - 1])}
            for name, p in preds.items():
                rows.append(dict(target=TNAME[k], horizon=h, model=name, scope="all", wape_pct=100 * np.abs(p - y).sum() / y.sum()))
                for s in SECTORS:
                    m = sec == s
                    rows.append(dict(target=TNAME[k], horizon=h, model=name, scope=s, wape_pct=100 * np.abs(p[m] - y[m]).sum() / y[m].sum()))
                for tr in sorted(set(tiers)):
                    m = tiers == tr
                    rows.append(dict(target=TNAME[k], horizon=h, model=name, scope="tier=" + tr, wape_pct=100 * np.abs(p[m] - y[m]).sum() / y[m].sum()))
    bl = pd.DataFrame(rows).round(2)
    bl.to_csv(TAB / "t10_baseline_errors_validation_2024.csv", index=False)
    F["baselines"] = bl[(bl.scope == "all")].pivot_table(index=["target", "horizon"], columns="model", values="wape_pct").round(2).reset_index().to_dict("records")

    # ================================================================================================================
    # 13. Regime / drift: train history vs the validation year
    # ================================================================================================================
    yoy_all = {k: yo(L[k]) for k in "EVS"}
    yd = dates[12:]
    drift_rows = []
    pre = (yd >= "2012-01-01") & (yd <= "2019-12-01") & ~(np.convolve(pol_m.astype(int), np.ones(13, int), "valid") > 0)
    val = (yd >= "2024-01-01") & (yd <= "2024-12-01")
    for k in "EVS":
        for s in SECTORS:
            m = sec == s
            a, b = yoy_all[k][m][:, pre].ravel(), yoy_all[k][m][:, val].ravel()
            a, b = a[~np.isnan(a)], b[~np.isnan(b)]
            ks = stats.ks_2samp(a, b)
            drift_rows.append(dict(target=TNAME[k], sector=s, train_2012_2019_mean_yoy_pct=100 * a.mean(), val_2024_mean_yoy_pct=100 * b.mean(),
                                   train_std_pct=100 * a.std(), val_std_pct=100 * b.std(), ks_stat=ks.statistic))
    dr = pd.DataFrame(drift_rows).round(2)
    dr.to_csv(TAB / "t11_drift_train_vs_validation.csv", index=False)
    F["drift"] = dr.to_dict("records")
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.5), sharex=True)
    for ax, k in zip(axes, "EVS"):
        ax.axhline(0, color=AXIS, lw=0.8)
        for s in SECTORS:
            m = sec == s
            nat_l = np.log(nat.loc[s, TARGETS[k]].reindex(dates).values)
            g = 100 * (nat_l[12:] - nat_l[:-12])
            gy = pd.Series(g, index=yd)
            ax.plot(gy.index, gy.values, color=COL[s], lw=1.4)
        shade(ax, COV, RAMP if k == "S" else None)
        ax.set_title(TNAME[k] + ": year-on-year growth (%)", loc="left", fontsize=9, color=INK2)
        style(ax)
    sector_legend(fig, 1.02)
    save(fig, "fig12_yoy_growth.png", "Growth regimes shift over time: pre-COVID, COVID, recovery and the validation year differ",
         "National year-on-year growth by sector. Models trained on 2012-2019 growth would misjudge 2024.")

    # ================================================================================================================
    # 14. Wages, unemployment and demographics (quick checks)
    # ================================================================================================================
    w = df.groupby(["Year"]).Avg_Monthly_Wage_INR.mean()
    F["wage_cagr_2011_2024_pct"] = round(100 * ((w[2024] / w[2011]) ** (1 / 13) - 1), 2)
    wt = y24[y24.Sector_Name == "Manufacturing"].groupby("Econ_Tier", observed=True).Avg_Monthly_Wage_INR.mean()
    F["wage_tier_premium_mfg"] = round(float(wt["metro_core"] / wt["peripheral_tribal"]), 3)
    dem = df.groupby(["Sector_Name", "Year"])[["Female_Share_Pct", "Edu_Graduate_and_Above_Pct", "Age_15_24_Pct"]].mean()
    dd = (dem.xs(2024, level="Year") - dem.xs(2011, level="Year")).round(2)
    dd.to_csv(TAB / "t12_demographic_change_2011_2024.csv")
    F["demographic_change_pp"] = dd.to_dict("index")
    ur = df.groupby(["Sector_Name", "Year"]).Unemployment_Rate_Pct.mean().unstack(0).round(2)
    ur.to_csv(TAB / "t13_unemployment_by_year.csv")


    # ================================================================================================================
    # 15. Distributions of levels and of the quantity a model predicts (12-month log change)
    # ================================================================================================================
    yy = {"E": yE, "V": yV, "S": yS}
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 6.4))
    mom_rows = []
    for j, k in enumerate("EVS"):
        for s_ in SECTORS:
            m = sec == s_
            lv = np.log10(A[k][m][:, ~(excl | (ramp_m if k == "S" else np.zeros(nT, bool)))]).ravel()
            ch = yy[k][m].ravel()
            ch = ch[~np.isnan(ch)]
            axes[0, j].hist(lv, bins=40, histtype="step", color=COL[s_], lw=1.4, density=True)
            axes[1, j].hist(100 * ch, bins=60, histtype="step", color=COL[s_], lw=1.4, density=True, range=(-40, 60))
            mom_rows.append(dict(target=TNAME[k], sector=s_, skew_level=stats.skew(A[k][m].ravel()), skew_log_level=stats.skew(np.log(A[k][m].ravel())),
                                 skew_12m_change=stats.skew(ch), excess_kurtosis_12m_change=stats.kurtosis(ch),
                                 p01_12m_change_pct=100 * np.percentile(ch, 1), p99_12m_change_pct=100 * np.percentile(ch, 99)))
        axes[0, j].set_title(TNAME[k] + ": log10 of level", loc="left", fontsize=9, color=INK2)
        axes[1, j].set_title(TNAME[k] + ": 12-month change (%)", loc="left", fontsize=9, color=INK2)
        style(axes[0, j])
        style(axes[1, j])
    sector_legend(fig, 1.02)
    save(fig, "fig13_distributions.png", "Levels are right-skewed and sector-specific; 12-month changes are close to symmetric",
         "Months in shock windows excluded. Top: pooled over series; bottom: the quantity a model has to predict.")
    mom = pd.DataFrame(mom_rows).round(2)
    mom.to_csv(TAB / "t14_distribution_moments.csv", index=False)
    F["distributions"] = dict(mean_skew_level=round(float(mom.skew_level.mean()), 2), mean_skew_log_level=round(float(mom.skew_log_level.mean()), 2),
                              mean_skew_12m=round(float(mom.skew_12m_change.mean()), 2),
                              max_excess_kurtosis_12m=round(float(mom.excess_kurtosis_12m_change.max()), 2))

    # ================================================================================================================
    # 16. Correlation structure of year-on-year changes, and redundant columns
    # ================================================================================================================
    var = {"employed": L["E"], "vacancies": L["V"], "seekers": L["S"], "wage": np.log(extra["Avg_Monthly_Wage_INR"]),
           "unemployment rate": extra["Unemployment_Rate_Pct"], "female share": extra["Female_Share_Pct"],
           "graduate share": extra["Edu_Graduate_and_Above_Pct"], "youth share": extra["Age_15_24_Pct"],
           "population": np.log(extra["District_Total_Population_Est"]), "training seats": np.log(extra["Training_Seats_Sanctioned"]),
           "certified": np.log1p(extra["Trainees_Certified_Monthly"])}
    cols_ = {n: np.where(win[None, :], np.nan, v[:, 12:] - v[:, :-12]).ravel() for n, v in var.items()}
    cm = pd.DataFrame(cols_).dropna().corr()
    cm.round(2).to_csv(TAB / "t15_correlation_yoy_changes.csv")
    div = LinearSegmentedColormap.from_list("div", ["#256abf", "#f0efec", "#e34948"])
    fig, ax = plt.subplots(figsize=(7.8, 6.2))
    ax.imshow(cm.values, cmap=div, vmin=-1, vmax=1)
    ax.set_xticks(range(len(cm)), cm.columns, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(cm)), cm.columns, fontsize=8)
    ax.grid(False)
    for i in range(len(cm)):
        for j in range(len(cm)):
            ax.text(j, i, f"{cm.values[i, j]:.2f}", ha="center", va="center", fontsize=7, color=INK if abs(cm.values[i, j]) < 0.6 else "#ffffff")
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    save(fig, "fig14_correlation.png", "Year-on-year changes are largely uncorrelated across variables",
         "Pearson correlation of year-on-year changes (differences for percentage columns), shock windows excluded.", legend=False)
    off = cm.values[~np.eye(len(cm), dtype=bool)]
    F["correlation_yoy"] = dict(max_abs_offdiag=round(float(np.abs(off).max()), 2), share_abs_below_0_2=round(float((np.abs(off) < 0.2).mean()), 2),
                                top_pairs=[(a, b, round(float(cm.loc[a, b]), 2)) for a, b in
                                           [(cm.index[i], cm.columns[j]) for i in range(len(cm)) for j in range(i)]
                                           if abs(cm.loc[a, b]) >= 0.3])
    num_cols = [c for c in df.select_dtypes("number").columns if c not in ("Year", "Month", "Quarter")]
    cl = df[num_cols].corr()
    pairs = [(cl.index[i], cl.columns[j], float(cl.iloc[i, j])) for i in range(len(cl)) for j in range(i) if abs(cl.iloc[i, j]) >= 0.95]
    pd.DataFrame(pairs, columns=["a", "b", "pearson_r_levels"]).round(3).to_csv(TAB / "t16_redundant_column_pairs.csv", index=False)
    F["redundant_pairs_levels"] = len(pairs)

    # ================================================================================================================
    # 17. Stationarity (augmented Dickey-Fuller, 2012-2019 pre-COVID sample)
    # ================================================================================================================
    sample = (dates >= "2012-01-01") & (dates <= "2019-12-01")
    adf_rows = []
    for k in "EVS":
        for s_ in SECTORS:
            idxs = np.where(sec == s_)[0]
            res = {"level (log)": [], "12-month difference": [], "month-on-month difference": []}
            for i in idxs:
                y = L[k][i, sample]
                res["level (log)"].append(adf_tstat(y) < ADF_CRIT_5PCT)
                res["12-month difference"].append(adf_tstat(y[12:] - y[:-12]) < ADF_CRIT_5PCT)
                res["month-on-month difference"].append(adf_tstat(np.diff(y)) < ADF_CRIT_5PCT)
            for name, v in res.items():
                adf_rows.append(dict(target=TNAME[k], sector=s_, transform=name, share_rejecting_unit_root_pct=100 * float(np.mean(v))))
    adf = pd.DataFrame(adf_rows).round(1)
    adf.to_csv(TAB / "t17_adf_stationarity.csv", index=False)
    F["adf"] = adf.groupby(["target", "transform"]).share_rejecting_unit_root_pct.mean().round(1).reset_index().to_dict("records")

    # ================================================================================================================
    # 18. State comparison, wages and unemployment
    # ================================================================================================================
    sg = []
    for st_ in sorted(set(states)):
        for s_ in SECTORS:
            m = (states == st_) & (sec == s_)
            e22 = A["E"][m][:, dates.year == 2022].mean(axis=1).sum()
            e24 = A["E"][m][:, dates.year == 2024].mean(axis=1).sum()
            v24 = A["V"][m][:, dates.year == 2024].sum()
            s24 = A["S"][m][:, dates.year == 2024].sum()
            sg.append(dict(state=st_, sector=s_, employed_2024=e24, emp_cagr_2022_2024_pct=100 * ((e24 / e22) ** 0.5 - 1),
                           coverage_2024=v24 / s24, unemployment_2024=extra["Unemployment_Rate_Pct"][m][:, dates.year == 2024].mean(),
                           wage_2024=extra["Avg_Monthly_Wage_INR"][m][:, dates.year == 2024].mean()))
    sgd = pd.DataFrame(sg).round(2)
    sgd.to_csv(TAB / "t18_state_comparison_2024.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9))
    snames = sorted(set(states))
    for ax, (col, ttl, logy) in zip(axes, [("emp_cagr_2022_2024_pct", "Employment growth 2022-2024 (% a year)", False),
                                           ("coverage_2024", "Vacancies per registered seeker, 2024", True)]):
        w = 0.15
        for j, s_ in enumerate(SECTORS):
            vals = [sgd[(sgd.state == st_) & (sgd.sector == s_)][col].iloc[0] for st_ in snames]
            ax.bar(np.arange(len(snames)) + (j - 2) * w, vals, width=w * 0.88, color=COL[s_])
        ax.set_xticks(range(len(snames)), snames)
        ax.set_title(ttl, loc="left", fontsize=9, color=INK2)
        if logy:
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        style(ax)
    sector_legend(fig, 1.02)
    save(fig, "fig15_states.png", "States differ in growth and coverage, but the sector ordering is the same everywhere",
         "56 districts grouped by state; Delhi, Tamil Nadu and West Bengal contain 11, 4 and 5 districts.")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.7))
    urs = df.groupby(["Sector_Name", "Date"]).Unemployment_Rate_Pct.mean().unstack(0)
    shade(axes[0], COV)
    for s_ in SECTORS:
        axes[0].plot(urs.index, urs[s_], color=COL[s_], lw=1.5)
    axes[0].set_title("Unemployment rate (%), average across districts", loc="left", fontsize=9, color=INK2)
    style(axes[0])
    wr = d24.groupby(["Econ_Tier", "Sector_Name"], observed=True).Avg_Monthly_Wage_INR.mean().unstack()
    rel = (100 * (wr / wr.mean() - 1)).mean(axis=1).sort_values()
    axes[1].barh(range(len(rel)), rel.values, color="#2a78d6", height=0.7)
    axes[1].set_yticks(range(len(rel)), [t.replace("_", " ") for t in rel.index], fontsize=8)
    axes[1].axvline(0, color=AXIS, lw=0.8)
    axes[1].set_title("Wage vs sector average by tier, 2024 (%)", loc="left", fontsize=9, color=INK2)
    style(axes[1], grid="x")
    sector_legend(fig, 1.02)
    save(fig, "fig16_unemployment_wages.png", "Unemployment follows the national cycle; wages differ by tier but grow at one common rate",
         "Left: sector averages, grey band = COVID window. Right: mean wage by economic tier relative to the sector average.")
    F["wage_tier_spread_pct"] = [round(float(rel.min()), 1), round(float(rel.max()), 1)]
    F["unemployment_peak"] = {s_: [f"{urs[s_].idxmax():%Y-%m}", round(float(urs[s_].max()), 2)] for s_ in SECTORS}
    F["state_summary"] = sgd.groupby("state")[["emp_cagr_2022_2024_pct", "unemployment_2024"]].mean().round(2).to_dict("index")

    # ================================================================================================================
    # 19. Do the Phase 1 early-warning thresholds separate anything?  (coverage status by sector and year)
    # ================================================================================================================
    cy = df.groupby(["Series_ID", "Sector_Name", "Year"], observed=True).agg(V=("Active_Job_Vacancies", "sum"),
                                                                              S=("eShram_Registered_Seekers", "sum")).reset_index()
    cy["cov"] = cy.V / cy.S
    order = ["Acute Shortage", "Balanced", "Oversupply Watch", "Saturation Risk"]
    cy["status"] = np.select([cy["cov"] >= 1.0, cy["cov"] < 0.10, cy["cov"] < 0.20], ["Acute Shortage", "Saturation Risk", "Oversupply Watch"], "Balanced")
    stt = cy.groupby(["Sector_Name", "Year"]).status.value_counts(normalize=True).unstack().reindex(columns=order).fillna(0)
    stt.round(3).to_csv(TAB / "t19_status_shares_by_sector_year.csv")
    ramp_cols = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]            # ordinal blue steps 250/400/550/700
    fig, axes = plt.subplots(1, 5, figsize=(14, 3.4), sharey=True)
    for ax, s_ in zip(axes, SECTORS):
        t = stt.loc[s_]
        bottom = np.zeros(len(t))
        for c_, col_ in zip(order, ramp_cols):
            ax.bar(t.index, t[c_].values, bottom=bottom, color=col_, width=0.82, edgecolor=SURFACE, linewidth=0.8)
            bottom += t[c_].values
        ax.set_title(s_, loc="left", fontsize=8.5, color=INK2)
        ax.set_xticks([2012, 2016, 2020, 2024])
        style(ax)
    axes[0].set_ylabel("share of districts")
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=c_) for c_ in ramp_cols], order, loc="upper left", ncol=4, fontsize=8,
               labelcolor=INK2, bbox_to_anchor=(0.0, 0.85), frameon=False)
    save(fig, "fig17_status_classes.png", "With the Phase 1 thresholds, most sectors collapse into a single status after 2021",
         "Share of districts by coverage status (>= 1.0 acute shortage; 0.20-1.0 balanced; 0.10-0.20 oversupply watch; < 0.10 saturation risk).", legend=False)
    last = stt.xs(2024, level="Year")
    F["status_2024"] = last.round(2).to_dict("index")
    F["status_single_class_sectors_2024"] = [s_ for s_ in SECTORS if last.loc[s_].max() >= 0.9]
    gap = df[df.Year == 2024].groupby(["Series_ID", "Sector_Name"], observed=True).agg(V=("Active_Job_Vacancies", "mean"), S=("eShram_Registered_Seekers", "mean")).reset_index()
    gap["net_gap"] = gap.V - gap.S
    gs = gap.groupby("Sector_Name").net_gap.agg(["median", "sum", lambda x: (x > 0).mean()]).round(1)
    gs.columns = ["median_net_gap_persons", "total_net_gap_persons", "share_of_districts_with_openings_above_seekers"]
    gs.to_csv(TAB / "t20_net_gap_2024.csv")
    F["net_gap_2024"] = gs.to_dict("index")

    # ================================================================================================================
    # 20. Baseline error by economic tier (preview of the Phase 1 equity check) and composition
    # ================================================================================================================
    blt = bl[(bl.scope.str.startswith("tier=")) & (bl.model == "last value") & (bl.horizon == 6)].pivot(index="scope", columns="target", values="wape_pct")
    blall = bl[(bl.scope == "all") & (bl.model == "last value") & (bl.horizon == 6)].set_index("target").wape_pct
    ratio = (blt.max() / blall).round(2)
    blt.to_csv(TAB / "t21_baseline_error_by_tier_h6.csv")
    F["equity_preview_h6_last_value"] = dict(worst_tier_over_overall=ratio.to_dict(), worst_tier={c: blt[c].idxmax() for c in blt.columns})
    comp = df.groupby("Sector_Name")[["Male_Share_Pct", "Female_Share_Pct", "Age_15_24_Pct", "Age_25_54_Pct", "Age_55_Plus_Pct", "Edu_Below_Primary_Pct",
                                      "Edu_Secondary_HigherSecondary_Pct", "Qualification_Vocational_ITI_Certified_Pct", "Edu_Graduate_and_Above_Pct"]].mean().round(1)
    comp.to_csv(TAB / "t22_workforce_composition.csv")
    F["composition"] = comp.to_dict("index")

    json.dump(F, open(OUT / "eda_findings.json", "w"), indent=2, default=str)
    print("EDA complete:", len(list(FIG.glob("*.png"))), "figures,", len(list(TAB.glob("*.csv"))), "tables")


if __name__ == "__main__":
    main()
