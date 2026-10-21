# Data readiness: NKE (NIKE, Inc.)

**Verdict: READY WITH CAVEATS**  
Sector: Consumer discretionary | CIK 320187 | fiscal year ends in May

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 71 (2009Q1 to 2026Q3) |
| Contiguous run used for modelling | 71 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-08-31 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 18 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2019Q1..2026Q3 (31); SalesRevenueNet: 2009Q1..2018Q4 (40) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 93 of 117 |
| Periods whose value changed between filings | 12 |
| Quarters restated >0.1% / >1% | 5 / 5 (max 12.9%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 0 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | 2020Q3 |
| YoY moves > 50% (log) | 2021Q2 |

Largest restatements (first-reported vs latest-reported, USD):

- 2011Q2: 5,766,000,000 -> 5,021,000,000 (-12.92%)
- 2012Q2: 6,470,000,000 -> 6,236,000,000 (-3.62%)
- 2012Q1: 5,846,000,000 -> 5,656,000,000 (-3.25%)
- 2011Q4: 5,731,000,000 -> 5,546,000,000 (-3.23%)
- 2012Q3: 6,669,000,000 -> 6,474,000,000 (-2.92%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2019Q1 | SalesRevenueNet | RevenueFromContractWithCustomerExcludingAssessedTax | 5 | +0.00 |

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | yes | 9 | 2008Q3..2011Q1 | quarterly |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 26 | 2018Q1..2026Q3 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 9 | 2009Q2..2011Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 70 | 2009Q2..2026Q3 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | no | 0 | - | - |
| OperatingIncomeLoss (Operating income) | no | 0 | - | - |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 19 | 2008Q3..2026Q3 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 55 | 2008Q3..2026Q3 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Inventory levels and retail sales are plausible drivers; FX exposure is material but not modelled.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 18 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
