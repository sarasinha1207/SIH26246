# Phase 4 – Exploratory Data Analysis

Status: **Approved** (sign-off in Section 8).
Reproduce: `python src/eda/run_eda.py` (about 1 minute), then `python tests/test_eda_outputs.py`.
Outputs: `reports/eda/figures/` (17 charts), `reports/eda/tables/` (22 CSV tables, the table view of every chart), `reports/eda/eda_findings.json`.

---

## 1. Scope and rules
* **Data used:** `train` and `validation` rows only (2011-01 to 2024-12, 47,040 rows, 280 series), loaded through `load_panel`. The test period (2025–2026) was never loaded; the script asserts this, and a test checks it.
* **Goal:** learn what the data does so Phases 5–8 are designed on evidence, with the Phase 1 questions in mind: what drives demand, supply and the gap, how predictable they are, and where the pitfalls are.
* **Caveat:** the data is a simulation. Section 6 separates findings that describe the labour market from findings that describe how the simulator was built.

## 2. Findings

### F1. Scale and growth differ widely across sectors
2024 averages across the 56 districts: Manufacturing 10.8M employed, Construction 7.9M, Textiles 3.1M, Healthcare 2.7M, IT-ITeS 2.4M. Employment growth was 0.2–5.4% a year in 2011–2019 (Textiles lowest, IT-ITeS highest) and 6.2–9.0% a year in 2022–2024 (`t01`, Fig 1).

### F2. The growth regime has shifted, so history is a poor guide to 2024
Average year-on-year employment growth, 2012–2019 against 2024: Manufacturing 1.8% → 6.2%, Construction 3.1% → 6.6%, Healthcare 3.9% → 6.6%, Textiles 0.4% → 4.5%; IT-ITeS fell 5.8% → 4.0%. IT-ITeS vacancies moved from +4.6% a year to **−26.9%** in 2024 (distribution shift KS = 0.75). Seeker growth jumped to 9–12% a year in four sectors (`t11`, Fig 12).

### F3. Seasonality is strong in two sectors only
Construction swings 14.8% peak to trough and seasonality explains 69% of its (detrended) variance: high in Dec–Feb, down about 9% in Jun–Sep. Textiles swings 11.6% (70% of variance): up in Sep–Nov, down in Apr–May. Manufacturing 5.2% (44%); IT-ITeS 2.0% and Healthcare 1.7%. Vacancies and seekers inherit the same shapes, but noise hides much of it. All 15 target-by-sector combinations reject "no month effect" in an ANOVA (p < 0.05), though pooling series makes those p-values optimistic, so the amplitudes are the useful measure (`t02`, Fig 2).

### F4. COVID: deep drops in three sectors, a demand surge in Healthcare
Employment fell 50.4% in Construction (May 2020; 18 months to regain Feb-2020), 42.9% in Textiles (17 months) and 37.8% in Manufacturing (10 months). Vacancies fell harder: −72.4%, −65.6%, −58.6%. Healthcare vacancies jumped +49.8% in May 2020 and IT-ITeS +19.4% by Dec 2020 while their employment barely rose (+9.1% and +6.1%). IT-ITeS vacancies then reached +94% over Feb 2020 in Jul 2022 and fell back (`t03`, Fig 3).

### F5. The e-Shram launch is a structural break in supply and in coverage
After the 2021-08..2023-02 ramp, vacancies per registered seeker are 0.41× their 2019 level in Manufacturing, 0.25× in Construction, 0.40× in Healthcare and 0.27× in Textiles, but 1.06× in IT-ITeS. This reflects a change in who is registered, not a change in the labour market (Fig 4).

### F6. Activity is concentrated; density follows district tier
IT-ITeS is the most concentrated sector: the top 5 districts hold 58.9% of its employment (Gini 0.705, Pune largest). Manufacturing's top 5 hold 31.5%. Workers per 1,000 residents: Manufacturing in hub tiers is 4.8× the tribal-district level; IT-ITeS in the top tier is 26.9× (`t04`, `t05`, Fig 5).

### F7. District differences are persistent
The rank of a district's coverage (vacancies per seeker) is highly stable: Spearman 0.92–0.97 one year apart, 0.79–0.93 five years apart (COVID years excluded). District rankings are therefore meaningful, not noise (`t06`, Fig 6).

### F8. Series behave like "level + noise", with seasonal echo
Pooled autocorrelation of monthly changes: Employment 0.82 at lag 12 (seasonal) and about 0 at lag 1. Vacancies and seekers have lag-1 autocorrelation of −0.31 and −0.34 (the signature of measurement noise) and weak seasonal echo (0.14–0.16). Implied noise: Employment about 1.0% a month, Vacancies 4.8%, Seekers 4.3%. For vacancies the noise does not depend on series size (Spearman 0.00), so tiny series are not noisier in percentage terms (`F12`, Fig 7, 11).

### F9. Vacancies move with employment, not ahead of it
The cross-correlation of year-on-year growth peaks at lag 0 (0.245); there is no useful lead. Vacancy growth and seeker growth are almost unrelated (0.07) (Fig 8).

### F10. Few covariates predict growth, and the signal is mean reversion
Within-sector, within-month rank correlation with next-12-month growth: strongest are employment momentum (−0.31 for employment), vacancy momentum (−0.32) and vacancy rate (−0.23) for vacancies, and unemployment (−0.235) and seeker rate (−0.19) for seekers. Wages, demographics, population and seat levels have |correlation| ≤ 0.07. The negative sign is partly real mean reversion and partly mechanical: noise at the origin month enters both the feature and the target with opposite signs (`t07`, Fig 9).

### F11. Training seats follow district size more than demand
Across districts, seats and vacancies are rank-correlated at 0.86–0.89, yet 16–19% of seats (total variation distance) sit where vacancies do not call for them. Construction has far fewer seats per vacancy (95 per 100) than Manufacturing (191), Textiles (183), IT-ITeS (233) or Healthcare (274); seats are an annual capacity and vacancies a stock, so only the comparison across sectors is meaningful. Largest over-allocations relative to vacancy share: Gadchiroli and Yavatmal in IT-ITeS, Nandurbar and Washim in Manufacturing; Howrah is under-served in Healthcare (`t08`, `t09`, Fig 10).

### F12. Baseline errors on the validation year set the bar
Origin 2023-12, WAPE % (`t10`):

| Target | Horizon | Last value | Seasonal naive + drift | Seasonally adjusted 3-month level |
|---|---|---|---|---|
| Employment | 1 / 3 / 6 / 12 | 1.35 / **1.93** / 4.11 / 5.35 | 1.52 / **1.93** / **2.48 / 2.85** | **1.28** / 2.60 / 4.15 / 5.28 |
| Vacancies | 1 / 3 / 6 / 12 | **5.16 / 7.01** / 10.22 / 9.60 | 7.19 / 8.11 / **10.00** / 17.69 | 5.56 / 7.52 / 11.63 / **9.45** |
| Seekers | 1 / 3 / 6 / 12 | 4.36 / 5.37 / 7.07 / 8.60 | 6.21 / 7.95 / 9.99 / 14.72 | **4.08 / 5.11 / 6.72 / 8.31** |

Simple moving averages and seasonal-adjusted smoothing do not clearly beat the last value for vacancies. Vacancy error grows from about 5% at one month to about 10% at six, so the hard part is the level shifts (hiring cycles, above all IT-ITeS, where the six-month error reaches 21%), not the month-to-month noise. A perfect forecast of the underlying level would still show a WAPE of about 0.8 × noise, i.e. about 0.8% (employment), 3.9% (vacancies) and 3.5% (seekers).

### F13. Levels are right-skewed; the 12-month change a model predicts is not
Mean skewness of levels across target-by-sector combinations is 2.96, but of log-levels only −0.26, and of 12-month log changes 0.02 (largest excess kurtosis 0.75, IT-ITeS vacancies). Typical 1st–99th percentile of the 12-month change: employment −4.4% to +11.7% across sectors, vacancies about −46% to +35% (IT-ITeS widest), seekers about −20% to +32% (`t14`, Fig 13).

### F14. Variables are almost uncorrelated in changes, but heavily redundant in levels
Year-on-year changes: the largest off-diagonal correlation is 0.51 (training seats and certified trainees), 91% of pairs are below 0.2; the notable links are unemployment rate with seekers (0.45), employment with seekers (0.27) and with vacancies (0.24). In levels, 16 column pairs have |r| ≥ 0.95: every demographic count tracks total employment (r 0.95–0.99), and male and female shares are perfectly anti-correlated (r = −1) (`t15`, `t16`, Fig 14).

### F15. Levels are non-stationary; one difference makes the series stationary
Augmented Dickey-Fuller tests on 2012–2019 (5% level) reject a unit root in log-levels for only 1.4% of employment series, 27.8% of vacancy series and 0% of seeker series. Month-on-month differences reject in 74%, 94% and 87%. Twelve-month differences reject in only 17%, 34% and 18% (the test has low power with 96 observations and seasonal patterns remain) (`t17`).

### F16. Sector explains coverage; state adds little
Employment growth 2022–2024 ranges from 5.5% a year (West Bengal Textiles) to 10.1% (Tamil Nadu Construction). Coverage hardly varies by state within a sector (IT-ITeS 0.52–0.63, Manufacturing 0.12–0.15, Construction 0.04 everywhere). Unemployment is highest in West Bengal and Delhi (`t18`, Fig 15).

### F17. Unemployment follows the national cycle; wages follow one trend
Unemployment peaks at 11.1–11.9% in April–May 2020 in Manufacturing, Construction and Textiles. IT-ITeS and Healthcare peak at 7.4% and 7.1% in June 2018, not in COVID. Wages grow 5.5% a year everywhere and differ by tier only in level, from 5.9% below to 24.1% above the sector average (`t13`, Fig 16).

### F18. The Phase 1 early-warning thresholds label sectors, not districts
Applying the Phase 1 coverage thresholds (1.0, 0.20, 0.10) to 2024, 100% of Construction districts are "Saturation Risk", 95% of Textiles, 96% of IT-ITeS are "Balanced", 80% of Healthcare and 75% of Manufacturing are "Oversupply Watch". No district in any sector has more openings than registered seekers in 2024. The status mostly repeats the sector, so as defined it adds little for ranking districts (`t19`, `t20`, Fig 17).

### F19. Baseline errors already exceed the Phase 1 equity limit
Last-value error at six months for the worst economic tier is 1.67× the overall error for employment (peripheral tribal), 1.68× for vacancies (logistics hub, which is Nagpur alone) and 1.82× for seekers (metro residential), against the Phase 1 limit of 1.5×. Tiers with one to three districts are noisy, so Phase 8 must report tier results with district counts (`t21`).

## 3. Figures
| Figure | Shows |
|---|---|
| `fig01_trends` | Employment, vacancies, seekers by sector, indexed |
| `fig02_seasonality` | Month-of-year profile |
| `fig03_covid` | COVID shock and recovery |
| `fig04_coverage` | Vacancies per seeker over time |
| `fig05_density_heatmap` | Employment density by tier and sector |
| `fig06_rank_stability` | District rank persistence |
| `fig07_acf` | Autocorrelation of monthly changes |
| `fig08_leadlag` | Vacancy vs employment and seeker growth |
| `fig09_covariate_signal` | Feature signal vs next-12-month growth |
| `fig10_seats_vs_demand` | Seats against vacancies by district |
| `fig11_noise_vs_volume` | Noise against series size |
| `fig12_yoy_growth` | Year-on-year growth regimes |
| `fig13_distributions` | Distributions of levels and of 12-month changes |
| `fig14_correlation` | Correlation of year-on-year changes |
| `fig15_states` | State comparison of growth and coverage |
| `fig16_unemployment_wages` | Unemployment over time; wage by tier |
| `fig17_status_classes` | Phase 1 status classes by sector and year |

All charts use the validated reference palette in fixed sector order (blue, orange, aqua, yellow, magenta); three of those colours are below 3:1 contrast on the light surface, so every chart carries a legend and every chart has a matching CSV table.

## 4. Implications for the next phases
| Finding | What to do |
|---|---|
| F8 multiplicative noise; counts right-skewed | Model log-changes or log-levels; use `log1p` for zero-containing counts |
| F2 regime shift; F4 COVID; F5 e-Shram | Mask COVID, policy and e-Shram windows in training (as the prototype did), and weight recent years; test an explicit regime or post-2022 indicator |
| F3 seasonality | Include month-of-year and seasonal-lag features; sector-specific seasonal strength matters |
| F10 signal is deviation from smoothed level | Build features that separate level from noise: deviations from 6- and 12-month means, momentum, vacancy and seeker rates. Skip wages, demographics and seat levels in the first model; test them once to confirm |
| F12 baselines | Phase 8 must beat last-value, seasonal-naive-with-drift and the seasonally adjusted level, per horizon and sector, not only the seasonal naive baseline |
| F12 IT-ITeS vacancy cycle | Report IT-ITeS separately; it dominates vacancy error |
| F9 no lead from vacancies | Do not expect cross-target leading features to help; test but do not rely on it |
| F7 persistent district effects | Series-level or district-level identity features (and the dimension tables) are useful |
| F11 seat–demand mismatch | A candidate decision output (over- and under-supply of seats), but see Section 6 |
| F15 stationarity | Confirms D1: forecast log-changes, not levels; difference once, seasonal terms handled with month features |
| F14 redundancy | Use shares and ratios, not demographic counts; keep one of male/female; expect wage and demographic features to drop out |
| F18 thresholds | Redesign the early-warning flags: coverage relative to the series' own history or percentile within sector-year, plus trend and a supply-capacity term (D7) |
| F19 equity | Report accuracy by tier with district counts; do not apply the 1.5× rule to tiers of one or two districts without comment |
| Prototype comparison | The provisional LightGBM scored vacancy WAPE ≈ 9.0%, about the same as the last-value baseline over the same horizons. Treat it as not yet adding value on vacancies |

## 5. Data-quality items found
No new defects. Items to keep in view: IT-ITeS vacancies and the e-Shram break distort any pooled metric; 4 low-volume series (`dim_series.csv`) have single-digit vacancies; the test period starts in a different growth regime from the training years (F2).

## 6. What the findings say about reality vs the simulator
| Finding | Reliable for the real world? |
|---|---|
| COVID drop sizes (F4) | They come from the parameters set in the brief, so they restate the brief |
| Persistent district effects and high rank stability (F7) | Built into the simulator by design; real data would likely be less stable |
| Seats follow size and over-serve small districts (F11) | Built by construction (half of seat allocation is spread evenly); do not read it as a real finding |
| Weak signal from wages, demographics (F10) | Partly by construction: the simulator does not link them to growth |
| Noise levels (F8, F12) | Set by the generator (employment 1–1.4%, vacancies 4–5%) |
| Methods and pitfalls (smoothing doesn't beat last value; regime shifts; breaks) | Transferable lessons |

## 7. Limits of this EDA
Stationarity used a small ADF implementation (`src/eda/stat_tests.py`, no statsmodels needed), checked in the tests on simulated random walks and white noise; it has low power on 96 observations, and no cointegration or multivariate time-series tests were run. The signal check pools series, so it can hide sector-specific effects, and the seasonality p-values pool series. All charts are static light-mode PNGs.

## 8. Decisions and sign-off
| # | Decision | Recommendation |
|---|---|---|
| D1 | Model log-changes (or log-levels) per series, direct multi-horizon | Yes |
| D2 | Mask COVID, policy and e-Shram windows in training and weight recent years | Yes |
| D3 | Add the seasonally adjusted level and moving-average baselines to the Phase 8 comparison | Yes |
| D4 | Report IT-ITeS vacancies and low-volume series separately | Yes |
| D5 | Treat F11 (seat–demand mismatch) as an illustrative output only, not a finding about real districts | Yes |
| D6 | Exclude wages, demographics and seat levels from the first model; confirm in Phase 5 | Yes |
| D7 | Treat the Phase 1 coverage thresholds as placeholders and design relative early-warning flags in Phases 5 and 8 | Yes |
| D8 | Use shares and ratios, not demographic counts, and drop redundant columns from the feature set | Yes |

Sign-off (approved by the project owner):
- [x] Findings F1–F19 and their limits (Section 6, 7) accepted
- [x] Decisions D1–D8 accepted

Phase 5 (Feature Engineering & Selection) has started. It builds every feature from data available at the forecast origin only and selects features using train and validation periods only.
