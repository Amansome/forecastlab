# Data readiness: HD (The Home Depot, Inc.)

**Verdict: READY**  
Sector: Retail | CIK 354950 | fiscal year ends in Jan

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-08-02 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 7 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q3..2026Q2 (32); Revenues: 2009Q1..2010Q3 (7); SalesRevenueNet: 2010Q4..2018Q2 (31) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 103 of 143 |
| Periods whose value changed between filings | 0 |
| Quarters restated >0.1% / >1% | 0 / 0 (max 0.0%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 0 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | 2012Q4, 2018Q4, 2024Q4 |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2010Q4 | Revenues | SalesRevenueNet | 8 | +0.00 |
| 2018Q3 | SalesRevenueNet | RevenueFromContractWithCustomerExcludingAssessedTax | 7 | +0.00 |

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | no | 0 | - | - |
| InventoryNet (Inventory (instant)) | yes | 54 | 2011Q4..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 70 | 2008Q4..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 30 | 2018Q4..2026Q2 | instant |
| OperatingIncomeLoss (Operating income) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | no | 0 | - | - |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 55 | 2008Q2..2026Q2 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): US retail sales (FRED RSAFS) is a direct demand proxy; inventory build is a lead indicator of expected sales.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 7 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
- 53-week fiscal years add a 14th week to some quarters, inflating those quarters by ~7.7% versus a 13-week quarter.
