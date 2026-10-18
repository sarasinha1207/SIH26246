# Phase 2 – Data Collection

Status: **Approved.** The data has been regenerated, audited and documented; sign-off recorded in Section 8.
Re-run the audit any time: `python src/data_collection/validate_raw_data.py` (24 PASS · 2 WARN · 0 FAIL)

---

## 1. Goal and exit criteria
Phase 1 needs monthly district × sector data for demand (vacancies), supply and employment, with enough history to validate a 12-month forecast. Phase 2 is complete when:
1. Every dataset in use is stored under `data/raw/` with provenance and checksums. ✔
2. Every column is documented in a data dictionary. ✔
3. The data is audited against Phase 1 and each defect is fixed or accepted in writing. ✔ (Section 6, 7)
4. Forbidden data (`Archived/`) is excluded. ✔

## 2. Inventory
| File | Rows × cols | Role |
|---|---|---|
| `data/raw/lmis_district_monthly_2011_2026.csv` | 53,760 × 41 | Primary modelling dataset |
| `data/raw/lmis_district_quarterly_2011_2026.csv` | 17,920 × 40 | Quarterly roll-up (stocks = mean of 3 months; certified = sum) |
| `data/raw/district_catalog.csv` | 56 × 8 | District dimension: official LGD code and its source, 2011 population, growth, economic tier |
| `data/raw/sector_nco_crosswalk.csv` | 25 × 5 | Sector → NCO-2015 families (anchor + 4 more per sector) |
| `data/raw/NCO-Codes.xlsx` | 3,447 occupations | NCO-2015 reference taxonomy |

Checksums: `data/raw/DATA_MANIFEST.json`, verified on every audit run. Column definitions: `docs/reference/DATA_DICTIONARY.csv`. Method and calibration: `docs/reference/DATA_SOURCES_AND_METHODOLOGY.md`. The generator is reproducible (seed 42; regenerating gave byte-identical files).

## 3. Provenance
* The panel is **synthetic**, produced by `src/data_generation/generate_lmis_master_dataset.py` (v2) and calibrated to Indian statistics where verifiable. The problem statement itself says dummy data will be provided for evaluation.
* No observed values are included. Every result describes the simulator, not the labour market.
* v1 of the panel and generator are kept under `data/superseded/` and `src/data_generation/legacy/` only as an audit trail. They are not to be used.
* `Archived/` and the root-level `lmis_employment_monthly_2016_2025.csv` (identical to an archived file) are excluded from all code.

## 4. Coverage
| Dimension | Coverage |
|---|---|
| Time | 2011-01 to 2026-12 (192 months / 64 quarters), no gaps |
| Geography | 56 districts: Maharashtra 36, Tamil Nadu 4, Delhi 11, West Bengal 5; official LGD codes |
| Sectors | Manufacturing (NIC 10–12, 15–33), Construction, IT-ITeS, Healthcare, Textiles and Apparel |
| Series | 280 complete series |
| Demand | `Active_Job_Vacancies`, `Total_Employed_Workers` |
| Supply | `eShram_Registered_Seekers` (proxy), **new** `Training_Seats_Sanctioned`, `Trainees_Certified_Monthly` |
| Covariates | wage, unemployment, population, gender / age / education splits |

## 5. Requirements vs availability
| Phase 1 need | Available? | Note |
|---|---|---|
| Monthly district × sector history ≥ 10 years | Yes | 16 years |
| Demand signal | Yes (synthetic) | Driven by hiring climate and employment, with district-level variation |
| Supply signal | Yes (synthetic) | Seekers plus new training-seat and outturn columns |
| Trade-level detail | **No** | One NCO anchor per sector; the crosswalk lists families but there is no data by family |
| Multiple real demand sources (portals, NCS, EPFO) | **No** | Single synthetic source |
| Real observed data | **No** | All values simulated |

## 6. What changed in the regeneration (decisions D2–D4)
| ID | v1 defect | Result in v2 |
|---|---|---|
| I1 | NCO `8110`, `8261` invalid | 25/25 crosswalk families verified in `NCO-Codes.xlsx` (C11) |
| I2 | 42% cap distorted COVID and disparity | No clipping; Manufacturing COVID shock −37.8% (spec −38%), Construction −50.4% (−52%), Textiles −42.9% (−42%) (C12, C15) |
| I3 | Disparity 53× vs 4–8× spec | Manufacturing hub/periphery 4.2× (C13). IT-ITeS ≈ 20× kept deliberately (C13b, Section 7) |
| I4 | Invalid / wrong LGD codes | 56 unique official codes with source recorded (C05) |
| I6 | Vacancies and seekers fixed ratios | District-level spread in coverage (std of log ≈ 0.26–0.41 per sector, C16) |
| new | No training-capacity data | Seats and certified-trainee columns (C17, C18) |

## 7. Audit results (26 checks: 24 PASS, 2 WARN, 0 FAIL)
Full detail: `reports/phase2_raw_data_checks.json`. The two remaining warnings are accepted:
| Check | Warning | Treatment |
|---|---|---|
| C10 | Nov–Dec 2026 lie after today (2026-10-18) | Accepted: the panel is a hypothetical full history |
| C13b | IT-ITeS hub/periphery ratio is ~20×, above the 4–8× in the brief | Deliberate: real IT employment is far more concentrated. Say if you want 4–8× enforced instead |

**Verification status of inputs:** all 56 LGD codes are verified against the LGD district export (Kolkata also against a West Bengal state list). Chengalpattu's population matches a published district profile; Kanchipuram's is derived from the undivided Census total. Sector index paths, tier shares, vacancy and informal-share rates and skilling-seat levels are stylised assumptions, not observed. See Section 2 of the methodology doc.

**Defects found in a second, stricter review and fixed before sign-off:**
1. IT-ITeS graduate share fell below 80% in 653 of 10,752 rows (the audit only tested the mean). Now ≥ 80.4% in every row, and the audit tests the row minimum (C14).
2. A start-up ramp in 2011: 36 seekers month-on-month jumps > 25% versus ~4 per year later. Fixed; new check C20.
3. Count floors of 5/10/50 were binding on ~30 rows of the smallest series. Floors are now 1 and nothing sits on them (C15).
4. Kolkata's LGD code and the Kanchipuram population were unverified; now verified / derived as above.
5. Found during the Phase 3 review: the audit never tested the quarterly file's count identities. Check C07q now does (0 errors).

## 8. Decisions and sign-off
| # | Decision | Status |
|---|---|---|
| D1 | Synthetic panel is the project's only dataset | Applied |
| D2 | Regenerate with fixes | Done |
| D3 | NCO anchor + crosswalk list | Done |
| D4 | Disparity | Manufacturing 4–8× met; IT-ITeS ~20× kept by design – **approved** |
| D5 | Months after today kept as hypothetical history | **Approved** |
| D6 | Delete root-level duplicate of the archived dataset | **Done** (verified byte-identical to the archived copy first; C19 now PASS) |

**Impact on Phase 1 (deferred to Phase 8 by your decision; nothing changed):**
1. Supply was defined as e-Shram seekers because no capacity data existed. The panel now has seats and certified trainees; Phase 1 could be amended so supply = seekers + training outturn.
2. The Phase 1 accuracy thresholds (e.g. vacancies WAPE ≤ 7%) were set from the v1 noise floor. On the Phase 4 validation year the vacancy baselines err by about 5–10% depending on horizon, so the vacancy threshold may need revisiting in Phase 8. v2 vacancies have real dynamics rather than i.i.d. noise. (the provisional prototype's scores on the locked 2025–26 period were removed from this document; see `docs/phases/PHASE_5_FEATURE_ENGINEERING.md`, Section 9).

Sign-off (approved):
- [x] v2 panel accepted as the project dataset (D1–D3)
- [x] IT-ITeS disparity kept above 4–8× (D4)
- [x] Months after today kept (D5)
- [x] Root-level duplicate removed (D6)
- [x] Phase 1 amendments (supply definition, accuracy thresholds) deferred to Phase 8

Phase 3 (Data Cleaning & Preprocessing) has started.
