# LMIS Dashboard Brief – everything an AI (or a developer) needs to build the dashboard

Project: SIH26246, *AI-Enabled Labour Market Intelligence and Skill Demand-Supply Forecasting Engine*, for the Ministry of Skill Development and Entrepreneurship (MSDE).
Written 2026-10-18. Data pack: `data/dashboard/` (built by `python src/dashboard/export_data_pack.py`).

---

## 1. What the project does
Planners at MSDE, NCVET and the Sector Skill Councils need to see, early, where training capacity does not match labour demand. The project builds a Labour Market Intelligence System that, for every **district × sector**, tracks and forecasts:
* **Demand**: employed workers and open job vacancies.
* **Supply**: registered job seekers (a proxy) and the training capacity (sanctioned seats, certified trainees).
* **The gap**: openings against seekers, a ranking of districts within each sector, and early-warning flags for oversupply (saturation) and shortage.

The dashboard lets planners drill down from the four-state total to a state, a district and a sector, see trends, forecasts and flags, and export the numbers.

## 2. Honest status (put these caveats on the dashboard)
* **All data is synthetic.** It is calibrated to Indian statistics (Census 2011 populations, PLFS-style unemployment, NIC/NCO/NSQF taxonomies, official LGD district codes) but contains no observed values. The dashboard must say so on every page.
* The project is at **Phase 6 of 10** (model selection done; model training, evaluation, deployment still to come). **Forecasts do not exist yet**; the history and the relative flags do. Build the forecast views against the contract in Section 7 so they light up when forecasts arrive.
* The data pack holds **2011-01 to 2024-12**. The years 2025–26 exist in the project but are a locked test set; do not show them until the evaluation phase releases them. (Nov–Dec 2026 are simulated beyond today's date.)

## 3. Coverage
| State / UT | LGD code | Districts |
|---|---|---|
| Maharashtra | 27 | **36** (all districts) |
| Delhi | 07 | **11** (all districts) |
| West Bengal | 19 | **5** (Kolkata, North 24 Parganas, South 24 Parganas, Howrah, Hooghly) |
| Tamil Nadu | 33 | **4** (Chennai, Tiruvallur, Kanchipuram, Chengalpattu) |
| **Total** | | **4 states / UTs, 56 districts** |

District list with official LGD codes, 2011 population, growth rate and economic tier: `data/dashboard/dim_district.csv`. There are 16 district tiers (for example `metro_core`, `industrial_it_hub`, `industrial_hub`, `textile_cluster`, `peripheral_tribal`); use them for grouping and comparison.

**Sectors (5):**
| Sector | Code | NIC-2008 | NCO-2015 anchor | NSQF | Chart colour |
|---|---|---|---|---|---|
| Manufacturing (excluding textiles and apparel) | MFG | Division 10-12, 15-33 | 7223 | 3–6 | `#2a78d6` |
| Construction | CON | Division 41-43 | 7111 | 2–5 | `#eb6834` |
| IT-ITeS | ITS | Division 62-63 | 2511 | 5–8 | `#1baf7a` |
| Healthcare | HLT | Division 86 | 2211 | 4–8 | `#eda100` |
| Textiles and Apparel | TXT | Division 13-14 | 8153 | 2–5 | `#e87ba4` |

Each sector also lists four more NCO-2015 occupation families (`dim_sector.csv`, column `nco_families`). There is **no trade-level data**, only sector × district.

**Time:** monthly, 192 months in the full project (2011-01 to 2026-12); the data pack has 168 months (to 2024-12). **Series:** 56 districts × 5 sectors = **280 series**; 47,040 rows in the pack.

## 4. The files to load
| File | What it holds |
|---|---|
| `data/dashboard/monthly_metrics_2011_2024.csv` | **Main table**, one row per district × sector × month (28 columns below) |
| `data/dashboard/dim_district.csv` | 56 districts: state, LGD codes, tier, 2011 population, growth |
| `data/dashboard/dim_sector.csv` | 5 sectors: code, NIC, NCO, NSQF, colour |
| `data/dashboard/district_boundaries.geojson` | **Map polygons of the 56 districts** (0.4 MB, WGS84), one feature per district, joined on `properties.district_lgd_code` |
| `data/dashboard/district_map_preview.png` | What the polygons should look like (four panels, one per state) |
| `data/dashboard/district_boundaries_provenance.json` | Source, licence, checksum and caveats of the map polygons |
| `data/dashboard/data_pack_manifest.json` | Row counts, period, the list of status values |

Columns of the main table:
| Group | Columns |
|---|---|
| Keys | `Series_ID` (`<district LGD>-<sector code>`, e.g. `490-ITS` = Pune IT-ITeS), `Date` (first day of month), `state`, `district`, `district_lgd_code` (string, keep leading zeros), `district_tier`, `sector` |
| Demand | `employed` (workers), `vacancies` (open job openings) |
| Supply | `registered_seekers`, `training_seats_annual` (sanctioned seats, constant within a financial year Apr–Mar), `trainees_certified` (per month) |
| Context | `avg_monthly_wage_inr` (nominal), `unemployment_rate_pct`, `female_share_pct`, `graduate_share_pct`, `youth_15_24_share_pct`, `district_population` |
| Gap metrics | `net_gap_persons` = vacancies − seekers (negative = more seekers than openings), `coverage_monthly` and `coverage_3m` = openings per registered seeker, `seat_mismatch_log` |
| Relative flags | `coverage_percentile_in_sector` (0–100), `relative_status`, `absolute_context` |
| Warnings | `is_covid_window`, `is_eshram_ramp`, `is_low_volume_series` |

## 5. Definitions the dashboard must use
* **Coverage** = vacancies ÷ registered seekers (use the 3-month version for charts: it is less noisy). Above 1 means more openings than seekers.
* **Relative status** compares a district with the other districts of its **own sector in the same month**: *Tightest decile* (percentile ≥ 90), *Tight* (70–90), *Typical*, *Loose* (10–30), *Loosest decile* (≤ 10). By construction about 11 / 20 / 39 / 20 / 11% of districts fall in each class every month.
* **Absolute context** (always show it next to the relative status, because a relative class says nothing about absolute shortage): *openings exceed seekers* (coverage ≥ 1), *moderate* (0.2–1), *oversupplied* (0.1–0.2), *deep surplus* (< 0.1). In 2024 Construction is in deep surplus almost everywhere, so its "Tightest decile" districts are only the least oversupplied.
* **Seat mismatch** = log of (district's share of the sector's seats ÷ its share of the sector's vacancies). Above +0.5 the district has more seats than its demand share; below −0.5 fewer. Use as an illustration only; in this data half of the seats are spread evenly by construction.
* **Severity ranking:** rank districts within a sector by `net_gap_persons` (most negative = largest surplus of seekers) and by coverage percentile.
* **Registered seekers are a proxy** for labour supply. They have a structural break when the e-Shram registry launched (August 2021, ramp until about February 2023): coverage falls sharply in every sector except IT-ITeS. Shade `is_eshram_ramp` and `is_covid_window` on time charts and never read the break as a labour-market change.

## 6. Headline numbers (2024 monthly averages, to check your build)
| Sector | Employed | Vacancies | Seekers | Coverage |
|---|---|---|---|---|
| Manufacturing | 10.8 million | 247 thousand | 1.85 million | 0.13 |
| Construction | 7.9 million | 117 thousand | 2.79 million | 0.04 |
| Textiles and Apparel | 3.1 million | 54 thousand | 0.82 million | 0.07 |
| Healthcare | 2.7 million | 80 thousand | 0.50 million | 0.16 |
| IT-ITeS | 2.4 million | 87 thousand | 0.15 million | 0.59 |

Employed by state (five sectors, 2024): Maharashtra 16.1 million, West Bengal 5.4 million, Tamil Nadu 2.7 million, Delhi 2.7 million. IT-ITeS employment is highly concentrated: Pune, North 24 Parganas, Chennai and Mumbai Suburban are the largest districts.

## 7. Forecast contract (to be delivered by the modelling phases; build the screens now)
One file per monthly run, `forecast_latest.csv`, one row per series × target month:
`Series_ID, state, district, district_lgd_code, sector, origin_month, target_month, horizon_months (1–12), employed_fcst, employed_p05, employed_p95, vacancies_fcst, vacancies_p05, vacancies_p95, seekers_fcst, seekers_p05, seekers_p95, coverage_fcst, net_gap_fcst, coverage_percentile_fcst, relative_status_fcst, absolute_context_fcst, entering_extreme_decile (yes/no, from the forecast at 6 and 12 months), model_version, generated_on`.
Intervals are 90% ranges. Show forecasts as a line with a shaded band continuing from history.

**Accuracy to display beside any forecast** (validation years, WAPE = weighted absolute percentage error): employment about 1.3%, vacancies about 6.3%, seekers about 5.2%, averaged over horizons of 1, 3, 6 and 12 months, with error rising as the horizon grows. The learned model beats the "last value plus seasonal shift" baseline by about a quarter for employment and about 10% for vacancies and seekers. It does **not** beat that baseline for seekers twelve months ahead, and IT-ITeS vacancies are the least predictable. Show a "how reliable is this?" note.

## 8. Screens
1. **National overview:** KPI tiles (employed, vacancies, seekers, coverage, trainees certified, seats) with sector breakdown and a time slider; four-state map.
2. **Drill-down:** four-state → state → district → sector; breadcrumb and filters for state, district tier, sector, period.
3. **Trend explorer:** monthly lines per sector for employed, vacancies, seekers (index = 2011 average, log scale), shaded COVID and e-Shram windows; seasonal pattern view.
4. **Gap and ranking:** table and bar chart of districts ranked by net gap and by coverage percentile within a sector, relative status chips with the absolute context beside them, sortable and exportable.
5. **Early warning:** list of districts in the loosest decile (saturation risk) or tightest decile, those that move into an extreme decile in the forecast (when available), with a plain explanation.
6. **Training capacity:** seats and certified trainees against vacancies by district (scatter with the seat-mismatch band); this view is illustrative.
7. **Workforce profile:** gender, age and education shares by sector and district.
8. **Forecast view:** fan chart per district × sector with the accuracy note (Section 7).
9. **Method and data notes:** synthetic-data notice, definitions (Section 5), data period, limitations.
10. **Export / API:** CSV and JSON download of any filtered table; a simple read API (`/districts`, `/sectors`, `/metrics?district=&sector=&from=&to=`, `/gap-ranking?month=&sector=`, `/forecast?district=&sector=&horizon=`) so scheme target-setting tools can pull the numbers.

**Map:** `data/dashboard/district_boundaries.geojson` has one polygon per district (56 features, WGS84 longitude/latitude). Join it to the metrics on `properties.district_lgd_code` (a string, equal to `district_lgd_code` in the other files). Each feature also carries `district`, `state`, `state_lgd_code`, `district_tier`, `label_lon`/`label_lat` (a point inside the district for labels), `bbox` (to zoom to a district) and `boundary_name_in_source`. For a state view, group the features by `state` and draw the state outline from the union of their borders. Colour districts by the selected metric (coverage percentile or net gap) and add a tooltip with the district, sector and value.

**Map source and attribution:** the polygons come from the Local Government Directory district layer as distributed by bharatlas (licence CC0-1.0 / CC-BY-4.0, snapshot updated 2026-05-19). Show "Boundaries: Local Government Directory, via bharatlas" in the map footer. They are simplified (about 200 m) for dashboard use, so do not use them for surveys; their areas match the source to within 2%. They are mostly Census-2011-era shapes with later updates, so some source names are older than the dashboard names (for example `Aurangabad` for Chhatrapati Sambhajinagar, `Ahmednagar` for Ahilyanagar, `Osmanabad` for Dharashiv); always join on the LGD code, never on names. The project's own district codes were cross-checked against this layer: all 56 match, and Palghar (665), Chengalpattu (730), South East Delhi (670) and Shahdara (671) are present.

## 9. Design and accessibility
* **Languages:** English first, with Hindi, Marathi, Tamil and Bengali (the state languages covered); keep all text in translation files.
* **Accessibility:** WCAG 2.1 AA, keyboard navigation, a data-table view of every chart, screen-reader labels, colour never the only signal.
* **Colour:** use the fixed sector colours above (blue, orange, aqua, yellow, magenta; the same colour for the same sector everywhere, never cycled). Three of them (aqua, yellow, magenta) have low contrast on white, so always show direct labels or a legend and a table view. Use a single-hue blue ramp for magnitude and a blue-to-red scale only for signed values.
* **Charts:** thin lines, one y-axis per chart (never dual-axis), log scale for indexed series, hover tooltips with exact values, recessive grids, light and dark themes.
* **Performance:** the main table is 47,040 rows (9 MB); load once, filter in the browser or a small API.

## 10. Caveats to surface
* Synthetic data notice on every page; map footer credit for the boundaries (Section 8).
* Relative status always paired with absolute context.
* Four series have very small counts (`is_low_volume_series`: New Delhi Construction, Manufacturing and Textiles, and Gadchiroli IT-ITeS): grey them out or add a "small numbers" note.
* Percentages can differ slightly from counts because of rounding; counts for gender, age and education sum exactly to employed.
* IT-ITeS hub-versus-periphery gaps are far larger than for other sectors (about 20–27 times per resident); this is deliberate and not an error.

## 11. Suggested prompt for the AI
> Build a multilingual, accessible web dashboard for the "LMIS" labour-market project described in `docs/DASHBOARD_BRIEF.md`. Load `data/dashboard/monthly_metrics_2011_2024.csv`, `dim_district.csv` and `dim_sector.csv`. Implement the screens in Section 8 with the definitions in Section 5, the colours and accessibility rules in Section 9, and the caveats in Sections 2 and 10. Add a forecast screen that reads `forecast_latest.csv` in the format of Section 7 and shows "forecasts not yet available" until the file exists. Include CSV/JSON export and a small read API. Draw the map from `data/dashboard/district_boundaries.geojson`, joined on `district_lgd_code`, and credit the boundary source.
