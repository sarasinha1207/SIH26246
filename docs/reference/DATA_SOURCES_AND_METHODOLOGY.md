# LMIS Synthetic Panel (v2) – Sources, Calibration and Method

Generator: `src/data_generation/generate_lmis_master_dataset.py` (seed 42, byte-reproducible)
Files: `data/raw/lmis_district_monthly_2011_2026.csv` (53,760 × 41), `lmis_district_quarterly_2011_2026.csv` (17,920 × 40), `district_catalog.csv`, `sector_nco_crosswalk.csv`
Column dictionary: `docs/reference/DATA_DICTIONARY.csv` · Audit: `reports/phase2_raw_data_checks.json`

> **The data is simulated.** v2 is calibrated to published Indian statistics where this project could verify them, and to stated assumptions elsewhere. Section 2 marks which is which. Treat levels as plausible, not observed.

## 1. What changed from v1
| v1 defect | v2 fix |
|---|---|
| Employment = labour force × density multiplier, clipped at 42% (bound on 25% of rows, 64% of Manufacturing); muted the COVID shock | Employment = district workers × tier share × national sector index. No clipping anywhere |
| Manufacturing (NIC 10–32) overlapped Textiles (13–14) | Manufacturing = NIC 10–12, 15–33 |
| NCO `8110`, `8261` do not exist in NCO-2015 | Valid anchor codes (`7223`, `8153`) plus a 25-row crosswalk, all verified against `NCO-Codes.xlsx` |
| Maharashtra LGD codes were wrong (e.g. Mumbai City `495` is Sindhudurg); Nandurbar `497A` invalid | Official LGD codes; sources in `district_catalog.csv` |
| Chennai, Kanchipuram/Chengalpattu and Delhi populations double-counted | Census-2011 consistent (Delhi's 11 districts re-apportioned to the Census total) |
| Vacancies and seekers were fixed ratios of employment | Hiring-climate, unemployment and registry dynamics with persistent district effects |
| No training-capacity data | New `Training_Seats_Sanctioned`, `Trainees_Certified_Monthly` |
| Pune ÷ Gadchiroli IT ≈ 53× while documented as 60× "PASS" | Manufacturing hub/periphery ≈ 4.2× (spec 4–8×); IT ≈ 20× by design (see 4) |

## 2. Calibration anchors and how far each is verified
| Anchor | Value used | Verification |
|---|---|---|
| District LGD codes | All 56 | **Verified** against the LGD district export; Maharashtra's 36 also match the state land-records LGD directory and Kolkata `315` the West Bengal State Health Society LGD list |
| Urban unemployment (usual status) | 7.7% (2017-18), 5.4% (2022-23), 5.1% (2023-24) | Cited by PLFS summaries found by web search. Other years are approximate |
| IT-BPM workforce | 4.36M (FY20), ~4.5M (FY21), >5M (FY22); index path built from these | NASSCOM figures found by search; other years from recollection |
| Census-2011 populations | Catalog values for Maharashtra, Delhi, West Bengal, Tiruvallur, Chennai (4,646,732) | Most match the Census. Chengalpattu 2,556,244 matches the Anna University district profile (other sources differ by up to ~5%). Kanchipuram 1,442,008 is **derived** (undivided Kancheepuram 3,998,252 minus Chengalpattu) |
| COVID shocks (peak), wage growth 5.5%/yr, metro premium 1.25, gender/education bands, IT graduates > 80% | From your project brief | Implemented as specified, except Healthcare/IT surges (see 4) |
| Sector employment index paths, LFPR path, tier shares, vacancy rates, informal shares, skilling-seat rates, e-Shram ramp | Stylised | **Not verified** – plausible-order assumptions. Replace when real series are available |

## 3. Model structure (per district d, sector s, month t)
* **Workers**: `W_d(t) = Pop_d(t) × 0.665 × LFPR(t) × state factor × (1 − urban UR(t))`, with `Pop_d(t) = Pop_d,2011 × (1+g_d)^(t/12)`.
* **Employment**: `E = W × share_tier,s × [Idx_s(t) / 1.015^(t/12)] × district effect × season × COVID × policy × noise`.
  * COVID: `1 + δ_s · I(t) · stringency`, I(t) = monthly intensity (1.0 in Apr–May 2020); δ = −0.52 Construction, −0.38 Manufacturing, −0.42 Textiles, +0.08 Healthcare, +0.03 IT-ITeS.
  * Post-2021 recovery: residual scar = `0.2 · δ_s · max(0, 1 − β_s ln(1+τ))`, τ = months since Jul-2021.
  * Demonetisation (Nov 2016–Jan 2017) and GST (Jul–Oct 2017) dips; sector seasonality (monsoon construction, festive textiles, etc.).
  * Noise: persistent district effect (log-normal) + AR(1) φ = 0.9 + white noise.
* **Vacancies** (demand): `V = E × v_s × hiring_climate_s(t) × tightness × COVID_V × district effect × AR(1) noise`. Healthcare ≈ +47% and IT ≈ +12% at the April-2020 peak (the "surge" lives in vacancies; headcount rises only +9% / +4%).
* **Registered seekers** (supply proxy): `S = 0.6·unemployed + informal_s · E · reg(t) + 0.4·certified_12m`, with `reg(t)` a logistic ramp from ~2% to ~35% centred on early 2022 (e-Shram launched Aug-2021).
* **Training seats** (formal skilling capacity: ITI, diploma, short-term NSQF centres; levels are approximate): sanctioned seats per 1,000 working-age persons × state factor × national path (ITI expansion) × allocation (half lagged demand, half uniform, so supply is mismatched to demand); fixed within each financial year. **Certified** = seats × utilisation (0.72; 0.55 in FY2020-21) × 0.82 pass rate × monthly profile (peak July).
* **Wage**: `base_s · 1.055^(t/12) · metro premium · state factor · noise`.
* **Unemployment**: national urban path + sector offset + state offset + COVID spike, bounded 3.5–12% (only 0.7% of values sit on a bound).
* **Demographics**: persistent district profile drawn from a Dirichlet, monthly sampling noise from a second Dirichlet, integer counts by largest-remainder so gender, age and education counts sum exactly to total employed.

## 4. Deliberate departures from the project brief
* **IT-ITeS hub/periphery disparity is ~20×, not 4–8×.** Real IT employment is far more concentrated than the 4–8× in the brief; the 4–8× target is met for Manufacturing (4.2×). Audit check C13b records this as a documented warning.
* **Healthcare +44% and IT-ITeS +12% COVID "surges" are applied to vacancies**, not to headcount, because employment cannot grow 44% in two months.
* **Supply columns are new.** They address the missing training-capacity data identified in Phase 2.

## 5. Known limitations
* Counts are floored at 1 only (not 5/10/50 as in early drafts), so no value sits on an artificial minimum; the tiniest series (e.g. Gadchiroli IT-ITeS) have single-digit vacancies.
* IT-ITeS graduate share is projected to ≥ 80.5% in every row, so the brief's ">80%" holds row by row, not just on average.
* Seekers carry a real structural break at the Aug-2021 e-Shram launch; any model must handle it.
* The last two months (Nov–Dec 2026) are later than today's date and are simulated.
* Only one NCO anchor code per row; the crosswalk lists all families for each sector.
* Everything here describes the simulator, not the labour market.
