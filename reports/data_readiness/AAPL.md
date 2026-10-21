# Data readiness: AAPL (Apple Inc.)

**Verdict: READY**  
Sector: Technology hardware | CIK 320193 | fiscal year ends in Sep

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-06-27 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 6 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q4..2026Q2 (31); Revenues: 2018Q3..2018Q3 (1); SalesRevenueNet: 2009Q1..2018Q2 (38) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 107 of 140 |
| Periods whose value changed between filings | 5 |
| Quarters restated >0.1% / >1% | 2 / 2 (max 23.7%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 0 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | 2011Q4, 2016Q4, 2022Q4 |
| QoQ moves > 50% (log) | 2014Q4, 2016Q4, 2017Q4, 2020Q4 |
| YoY moves > 50% (log) | 2010Q2, 2010Q3, 2010Q4, 2011Q1, 2011Q2, 2011Q4 |

Largest restatements (first-reported vs latest-reported, USD):

- 2009Q3: 9,870,000,000 -> 12,207,000,000 (+23.68%)
- 2009Q2: 8,337,000,000 -> 9,734,000,000 (+16.76%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2018Q3 | SalesRevenueNet | Revenues | 8 | +0.00 |
| 2018Q4 | Revenues | RevenueFromContractWithCustomerExcludingAssessedTax | 5 | +0.00 |

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | no | 0 | - | - |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 70 | 2008Q3..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 70 | 2008Q3..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 32 | 2018Q3..2026Q2 | instant |
| OperatingIncomeLoss (Operating income) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 13 | 2013Q4..2025Q4 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 55 | 2008Q2..2026Q2 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Product launch cycles (e.g. a September launch) drive Q4/Q1 peaks; no launch calendar is in this data.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 6 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
- 53-week fiscal years add a 14th week to some quarters, inflating those quarters by ~7.7% versus a 13-week quarter.
