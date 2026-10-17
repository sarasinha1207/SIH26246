# Phase 2 – Data Collection

Status: **Audit complete, awaiting your decisions (Section 8).** Phase 2 closes only when the decisions in Section 8 are made and any chosen fixes are applied and re-audited.
Reproduce the audit: `python src/data_collection/validate_raw_data.py`

---

## 1. Goal and exit criteria
Phase 1 requires monthly district × sector data for demand (vacancies), supply (seekers) and employment, with enough history to validate a 12-month forecast. Phase 2 is complete when:
1. Every dataset the project will use is stored under `data/raw/`, with provenance and checksums recorded.
2. Every column is documented in a data dictionary.
3. The data is audited against the Phase 1 requirements and every gap or defect is either fixed or accepted in writing.
4. The forbidden data (`Archived/`) is excluded.

## 2. Inventory
| File | Rows × cols | Size | Role |
|---|---|---|---|
| `data/raw/lmis_district_monthly_2011_2026.csv` | 53,760 × 39 | 13.4 MB | Primary modelling dataset |
| `data/raw/lmis_district_quarterly_2011_2026.csv` | 17,920 × 38 | 4.3 MB | Quarterly roll-up of the monthly file (mean of 3 months) |
| `data/raw/NCO-Codes.xlsx` | 3,447 occupations | 0.2 MB | NCO-2015 reference taxonomy |

Checksums: `data/raw/DATA_MANIFEST.json` (re-verified on every audit run). Column definitions, units, ranges: `docs/reference/DATA_DICTIONARY.csv`. Generator method notes: `docs/reference/DATA_SOURCES_AND_METHODOLOGY.md`.

## 3. Provenance
* The panel is **synthetic**. It is produced by `src/data_generation/generate_lmis_master_dataset.py` (NumPy seed 42, so reproducible) and calibrated by its author to published Indian statistics (Census 2011 populations, PLFS-style participation rates, NIC/NCO/NSQF taxonomies, LGD district codes).
* It contains **no observed values**. The problem statement itself says dummy data will be provided for evaluation, so this is acceptable for the hackathon, but every result describes the simulator, not the labour market.
* The previous dataset in `Archived/` is excluded. No script reads it. The root-level `lmis_employment_monthly_2016_2025.csv` is byte-identical to an archived file and is also excluded.

## 4. Coverage
| Dimension | Coverage |
|---|---|
| Time | 2011-01 to 2026-12 (192 months / 64 quarters), no gaps |
| Geography | 56 districts: Maharashtra 36, Tamil Nadu 4, Delhi 11, West Bengal 5 |
| Sectors | Manufacturing, Construction, IT-ITeS, Healthcare, Textiles and Apparel |
| Series | 56 × 5 = 280 complete series |
| Targets (Phase 1) | `Total_Employed_Workers`, `Active_Job_Vacancies`, `eShram_Registered_Seekers` |
| Covariates | wage, unemployment rate, population, gender / age / education splits |

## 5. Requirements vs availability
| Phase 1 need | Available? | Note |
|---|---|---|
| Monthly district × sector history ≥ 10 years | Yes | 16 years |
| Demand signal (vacancies) | Yes (synthetic) | Generated as a share of employment × noise |
| Supply signal | **Proxy only** | e-Shram seekers. No training-seat, enrolment or outturn data exists in the dataset |
| Trade-level detail | **No** | One NCO family per sector |
| Multiple demand sources (portals, NCS, EPFO) | **No** | Only one synthetic source |
| Real observed data | **No** | All values simulated |

## 6. Audit results (17 checks: 12 PASS, 4 WARN, 1 FAIL)
Results file: `reports/phase2_raw_data_checks.json`.

| Check | Result |
|---|---|
| Shapes, no nulls, unique keys, complete 280 × 192 / 280 × 64 grid | PASS |
| 56 districts / 4 states / 5 sectors | PASS |
| Gender, age and education counts sum exactly to total employed | PASS |
| Share columns sum to 100% (max deviation 0.01 pp) | PASS |
| No negative values; unemployment within 3.5–12% | PASS |
| Quarterly file reconciles to monthly means (max difference 0.67 persons) | PASS |
| Raw files match recorded checksums | PASS |
| District LGD codes unique and numeric | **WARN**: Nandurbar is `497A` |
| History does not extend beyond today | **WARN**: Nov–Dec 2026 are after 2026-10-18 |
| Employment-rate cap not binding | **WARN**: 25% of rows sit at the generator's 42% cap |
| Legacy dataset kept out of the repo root | **WARN**: duplicate copy still present |
| Sector NCO codes exist in NCO-2015 workbook | **FAIL**: Manufacturing `8110` and Textiles `8261` do not exist |

## 7. Issues found
| ID | Issue | Evidence | Impact | Recommended action |
|---|---|---|---|---|
| I1 | Two of the five NCO codes are invalid | `8110` and `8261` are absent from `NCO-Codes.xlsx`; the nearest, `8111`, is "Miners and Quarriers". `7111` (House Builders), `2511` and `2211` are valid | NCO-coded outputs would be wrong for 2 sectors. No effect on forecasts, because the code is constant per sector | Correct the codes (see crosswalk below) |
| I2 | Employment cap distorts the data | Density multipliers imply sector employment of up to ~97% of the labour force (Manufacturing hub: 0.18 × 5.4 ≈ 0.97), so the generator clips at 42%. The clip binds on 64% of Manufacturing rows. Result: April-2020 Manufacturing employment is −9% versus Feb-2020, not the documented −38%; cross-district disparity is also compressed | Understates the Manufacturing COVID shock and hides district differences. Cannot be undone in preprocessing because the information is lost at generation | Recalibrate shares and multipliers in the generator so the cap is not needed, then regenerate |
| I3 | District disparity far above spec | Pune ÷ Gadchiroli IT-ITeS employment ≈ 53× (2026). The source doc says 60.48× and marks it PASS against a 4–8× requirement | Documentation is wrong; or the data is, if 4–8× is the real requirement | Decide which is intended; fix the generator or the doc |
| I4 | Invalid LGD code `497A` for Nandurbar | Check C05 | Joins to LGD master data would fail | Replace with the real LGD code |
| I5 | Last two months are in the future | Data ends 2026-12; today is 2026-10-18 | The 2027 forecast starts from simulated "history" | Treat the file as hypothetical full history (accept) or truncate at the last real month |
| I6 | Vacancies and seekers are fixed ratios of employment | Coverage (vacancies ÷ seekers) varies only ±10% within a sector | District gap rankings within a sector will be mostly size-driven | Accept as a data limitation; state it in results |
| I7 | Duplicate legacy file in repo root and git | `lmis_employment_monthly_2016_2025.csv` | Risk of accidental use | Remove it (it is tracked in git, so needs your approval) |

**NCO crosswalk proposal for I1** (families verified present in `NCO-Codes.xlsx`):
* Manufacturing: `7223` Metal Working Machine Tool Setters and Operators, `8212` Electrical and Electronic Equipment Assemblers, `8131` Chemical Products Plant and Machine Operators.
* Textiles and Apparel: `8153` Sewing Machine Operators, `8152` Weaving and Knitting Machine Operators, `8151` Fibre Preparing, Spinning and Winding Machine Operators.
* A sector spans many families, so a list per sector is more accurate than one code. Pick a single anchor code per sector if you need to keep the one-column schema.

## 8. Decisions needed from you
| # | Decision | Recommendation |
|---|---|---|
| D1 | Accept this synthetic panel as the project's only dataset? | Yes: the problem statement provides dummy data for evaluation |
| D2 | Fix generator defects (I1–I4) and regenerate before Phase 3, or freeze this version and only document the defects? | **Regenerate.** I2 loses information at generation time and cannot be repaired later. I will keep the seed, recalibrate, re-run the audit and update the manifest |
| D3 | NCO codes: use the crosswalk above? (Single anchor code or list per sector) | List per sector, with an anchor code in the existing column |
| D4 | Disparity target: should the Pune ÷ Gadchiroli gap be 4–8× as the doc requires, or is the current ~53× acceptable? | 4–8× if you want to follow the spec |
| D5 | Months after today (Nov–Dec 2026): keep as hypothetical history? | Keep, documented |
| D6 | Delete the root-level duplicate of the archived dataset? | Yes |

## 9. Optional: path to real data
The data is simulated. If real data becomes available, the pipeline is designed to accept it with the same columns. Sources already cited in the project's reference documents: MoSPI PLFS (mospi.gov.in), e-Shram (eshram.gov.in), LGD (lgdirectory.gov.in), Census 2011 (censusindia.gov.in), NCVET/NSQF (ncvet.gov.in). Training-seat and outturn data, which would replace the seekers proxy, would have to come from MSDE's own training-management systems; none is in this project yet.
