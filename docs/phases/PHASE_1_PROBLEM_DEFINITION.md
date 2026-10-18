# Phase 1 – Problem Definition

Project: SIH26246 – AI-Enabled Labour Market Intelligence and Skill Demand-Supply Forecasting Engine (MSDE)
Status: **Approved** (sign-off in Section 12). All decisions below are recorded with a rationale. Items marked **[CONFIRM]** were assumptions that the sign-off confirmed. After Phases 2 and 3, some factual statements went out of date; they were corrected and logged in Section 13. No decision was changed.

---

## 1. Business problem
India trains lakhs of candidates a year, but training capacity is often misaligned with real labour demand at district and sector level. Some areas have chronic oversupply of certified candidates, while high-growth areas are under-served. Planners at MSDE, NCVET and the Sector Skill Councils (SSCs) only discover the mismatch after placement outcomes are reported.

**Need:** a forward-looking, district- and sector-level view of labour demand against supply, early enough to change annual training targets, NSQF course revisions and centre capacity.

## 2. Users and the decisions the model supports
| User | Decision | What the model must give them |
|---|---|---|
| MSDE / NCVET planners | Annual training targets per sector and state | 12-month demand and supply outlook, ranked gaps |
| State skill missions | Sanctioning new centres, centre capacity | District × sector gap size (persons) and direction |
| Sector Skill Councils | Curriculum / NSQF revision | Sectors approaching saturation or shortage |
| Dashboard / API consumers | Feeding forecasts into target-setting workflows | A stable export schema (CSV/JSON) |

## 3. Objective
Build a model that forecasts labour **demand** and **supply** for every district × sector and turns the forecasts into a ranked demand-supply gap and early-warning flags, refreshed every month.

**ML objective (one sentence):** predict `Total_Employed_Workers`, `Active_Job_Vacancies` and `eShram_Registered_Seekers` for each district × sector for the next 1–12 months, with uncertainty intervals.

## 4. ML task formulation
| Item | Decision | Rationale |
|---|---|---|
| Task type | Multi-horizon time-series forecasting on a panel | Data is a monthly panel of 56 districts × 5 sectors = 280 series × 192 months |
| Unit of analysis | District × sector × month | Finest level in the dataset; the problem statement asks for district and sector granularity |
| Targets | `Total_Employed_Workers`, `Active_Job_Vacancies`, `eShram_Registered_Seekers` | Employment is the outlook, vacancies the demand signal, seekers the supply proxy |
| Horizon | 1–12 months ahead (quarterly roll-up for planning) | Annual target-setting needs a full year; quarterly aggregation matches planning cycles |
| Refresh cadence | Monthly | Problem statement: "updated periodically rather than annually" |
| Forecast origin | Last observed month in the panel | Standard rolling-origin setup |
| Output type | Point forecast + 90% interval per target and month | Planners need to see uncertainty, not just a number |
| Granularity not in scope | Individual trades / job roles | The dataset has one NCO family code per sector, so trade-level forecasting is impossible with this data **[CONFIRM]** |

## 5. Key definitions
| Term | Definition | Notes |
|---|---|---|
| **Demand** | `Active_Job_Vacancies` (employer openings) | Employed workers is reported as the demand *outlook*, not the gap input |
| **Supply** | `eShram_Registered_Seekers` (registered job-seeker pool) **[CONFIRM]** | The original dataset had no training-seat or outturn column, so this is a proxy. Phase 2 added `Training_Seats_Sanctioned` and `Trainees_Certified_Monthly`; whether to add them to the supply definition is deferred to Phase 8 (Section 13) |
| **Net gap (persons)** | Vacancies − Seekers | > 0: openings exceed seekers (shortage). < 0: surplus of seekers (oversupply) |
| **Coverage** | Vacancies ÷ Seekers (openings per registered seeker) | Scale-free, comparable across districts |
| **Status flag** | Acute Shortage (coverage ≥ 1.00), Balanced, Oversupply Watch (< 0.20), Saturation Risk (< 0.10) | Thresholds are placeholders to calibrate with real placement data |
| **Trend flag** | Tightening / Worsening supply glut when forecast coverage moves ±8% against the trailing 12 months | Early-warning component |
| **Severity rank** | Order by net gap in persons, overall and within sector | 1 = largest surplus (or shortage) |

## 6. Scope
**In scope (ML):** forecasting the three targets, the derived gap and coverage, flags and rankings, uncertainty intervals, a repeatable training and forecasting pipeline, an export file schema.

**In scope (later phases, not ML):** the interactive dashboard, the API layer (Phase 9).

**Out of scope for this project version:**
* Multilingual interface (front-end work).
* Aggregating job-portal, NCS and PLFS sources into a composite demand index: the problem statement asks for it, but only one synthetic dataset is available. **v1 demand index = vacancies**; a composite index is deferred until real multi-source data exists **[CONFIRM]**.
* Individual-level matching of candidates to jobs.
* Trade-level forecasts (see Section 4).

## 7. Data and constraints
* **Allowed data:** `data/raw/lmis_district_monthly_2011_2026.csv` (and the quarterly version for roll-ups). Reference: `docs/reference/DATA_SOURCES_AND_METHODOLOGY.md`.
* **Prohibited data:** everything under `Archived/` and the root-level copy `lmis_employment_monthly_2016_2025.csv` (identical to the archived file; deleted in Phase 2). The previous dataset must not be used for training, evaluation or comparison.
* **Known limitations (updated after Phase 2, see Section 13):**
  * The data is synthetic (v2 panel, recalibrated in Phase 2).
  * The last two months (Nov–Dec 2026) lie beyond today's date and are simulated.
  * IT-ITeS hub/periphery disparity is ~20×, above the 4–8× in the brief, by deliberate choice.
  * Supply is still only a proxy for training capacity: seekers plus the two new seat/outturn columns, all simulated.
  * There is no trade-level detail, only sector × district.

## 8. Success criteria
All measured on a held-out, time-based test period (Section 9).

**Forecast accuracy (WAPE = sum of absolute errors ÷ sum of actuals)**
| Target | Must beat | Acceptance |
|---|---|---|
| Employed | Best of seasonal-naive / seasonal-naive+drift | WAPE ≤ 2% and ≥ 20% better than the best baseline |
| Vacancies | same | WAPE ≤ 7% and ≥ 20% better than the best baseline |
| Seekers | same | WAPE ≤ 6% and ≥ 20% better than the best baseline |

* **Bias:** absolute aggregate bias ≤ 2% per target.
* **Horizon stability:** WAPE at h=12 no more than 1.5× WAPE at h=1.
* **Interval calibration:** empirical coverage of the 90% interval between 85% and 95%.
* **Equity check:** WAPE for the weakest district tier no more than 1.5× the overall WAPE, so peripheral and tribal districts are not poorly served.
* **Ranking quality:** Spearman correlation between forecast and actual gap ranking ≥ 0.90 (persons-level), measured on the test period.
* **Flag quality:** where the actual data produces more than one status within a sector, flag recall and precision ≥ 0.70; otherwise report as "not measurable on this data".
* **Reproducibility:** re-running the pipeline with the same data gives identical outputs.

Thresholds are set from what the data can support: the generator injects roughly 5–6% noise into vacancies and seekers, so a WAPE well below that is not achievable. **[CONFIRM]**

## 9. Validation protocol
* Time-based splits only; no random shuffling. A row may use only information available at its forecast origin.
* Early-stopping fold: train through 2023-12, validate on 2024. Test fold: train through 2024-12, test on 2025-01 to 2026-12. Final model trains on all data.
* Windows touching COVID (2020-03 to 2022-02) and the e-Shram roll-out ramp are excluded from training, because they are shocks the model cannot anticipate. This is documented, not hidden.
* Baselines are always reported alongside the model: last value, seasonal naive, seasonal naive + drift.

## 10. Risks
| Risk | Effect | Mitigation |
|---|---|---|
| Supply is only a proxy (no seats/outturn) | The gap may not reflect training capacity | State it clearly; keep the pipeline target-agnostic so real supply data can replace it |
| Synthetic data with known flaws | Results may not transfer to real data | Fix or document flaws in Phase 2–3; re-validate on real data when available |
| Little variation inside sectors | District rankings are mostly size-driven | Report this honestly; do not over-claim district-level insight |
| Unforecastable shocks (COVID-like) | Intervals understate tail risk | State intervals cover normal regimes only |
| Thresholds are arbitrary | Flags may mislead | Mark as placeholders; calibrate in Phase 8 with real data |

## 11. Mapping to the problem statement's expected outcomes
| # | Expected outcome | Where it's addressed |
|---|---|---|
| 1 | Forecasting dashboard for pilot sectors/states | Forecast outputs (Phases 6–8); dashboard in Phase 9 |
| 2 | Documented method for a single demand index | v1 = vacancies; composite index deferred (Section 6) |
| 3 | Early-warning flags for saturation/shortage | Section 5 flags (Phase 5–8) |
| 4 | API/export layer | Phase 9 |
| 5 | Multilingual accessible interface | Out of ML scope |

## 12. Sign-off checklist
Approved by the project owner in chat after Phase 1 was presented.
- [x] Targets and horizon (Section 4)
- [x] Supply = e-Shram seekers for now (Section 5)
- [x] Trade-level forecasting is out of scope (Section 4, 6)
- [x] v1 demand index = vacancies; composite index deferred (Section 6)
- [x] Success thresholds (Section 8)
- [x] `Archived/` and the root-level copy of the old dataset are off limits (Section 7)

**Exit criterion for Phase 1:** all boxes above ticked. ✔ Phase 2 (Data Collection) started after that.

## 13. Amendment log
| After | Change | Type |
|---|---|---|
| Phase 2 | Section 7 known limitations rewritten: the 42% cap, fixed vacancy/seeker ratios and missing training-capacity data were defects of the v1 panel and no longer apply | Factual correction |
| Phase 2 | Section 5 and 7 notes: the root-level duplicate was deleted; seat/outturn columns now exist | Factual correction |
| Phase 3 | Equity check (Section 8): district tier is now available as `Econ_Tier` in the processed tables | Factual correction |
| Phase 5 | Provisional-prototype scores for 2025–26 removed from deferred amendment 2 and replaced by validation-year evidence (test-period integrity, Phase 5 Section 9) | Factual correction |

**Deferred amendments (decision made by the project owner, to be revisited in Phase 8):**
1. Whether supply should be redefined as seekers plus training outturn.
2. Whether the accuracy thresholds in Section 8 need revising. They were set from the v1 noise floor. On the Phase 4 validation year, even the last-value baseline errs by about 5% (1 month) to 10% (6 months) for vacancies, against a perfect-level floor of about 3.9%, so the 7% target is only reachable at short horizons. To be settled in Phase 8 per horizon.
