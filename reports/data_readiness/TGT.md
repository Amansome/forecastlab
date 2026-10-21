# Data readiness: TGT (Target Corporation)

**Verdict: READY WITH CAVEATS**  
Sector: Retail | CIK 27419 | fiscal year ends in Jan

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-08-01 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 7 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q1..2026Q2 (34); Revenues: 2009Q1..2013Q4 (20); SalesRevenueNet: 2014Q1..2017Q4 (16) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 141 of 180 |
| Periods whose value changed between filings | 19 |
| Quarters restated >0.1% / >1% | 9 / 8 (max 2.7%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 20 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | 2012Q4, 2017Q4, 2023Q4 |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Largest restatements (first-reported vs latest-reported, USD):

- 2014Q3: 17,732,000,000 -> 17,254,000,000 (-2.70%)
- 2014Q2: 17,406,000,000 -> 16,957,000,000 (-2.58%)
- 2014Q1: 17,050,000,000 -> 16,657,000,000 (-2.30%)
- 2018Q1: 16,556,000,000 -> 16,781,000,000 (+1.36%)
- 2017Q1: 16,017,000,000 -> 16,223,000,000 (+1.29%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2014Q1 | Revenues | SalesRevenueNet | 23 | -2.12 |
| 2018Q1 | SalesRevenueNet | RevenueFromContractWithCustomerExcludingAssessedTax | 6 | -0.13 |

Tag disagreements, any two tags >1% apart in the same quarter (first 5). Lower-priority tags are often components (e.g. product-only sales), so a disagreement is a flag to read, not an error:

- {'quarter': '2008Q2', 'Revenues': 15472000000.0, 'SalesRevenueNet': 14971000000.0}
- {'quarter': '2008Q3', 'Revenues': 15114000000.0, 'SalesRevenueNet': 14588000000.0}
- {'quarter': '2009Q1', 'Revenues': 14833000000.0, 'SalesRevenueNet': 14361000000.0}
- {'quarter': '2009Q2', 'Revenues': 15067000000.0, 'SalesRevenueNet': 14567000000.0}
- {'quarter': '2009Q3', 'Revenues': 15276000000.0, 'SalesRevenueNet': 14789000000.0}

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | no | 0 | - | - |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 60 | 2008Q2..2026Q2 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 73 | 2008Q2..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | no | 0 | - | - |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 2 | 2018Q4..2019Q4 | instant |
| OperatingIncomeLoss (Operating income) | yes | 52 | 2010Q2..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 18 | 2009Q1..2026Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 65 | 2008Q2..2026Q2 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): US retail sales (FRED RSAFS) is a direct demand proxy; inventory build is a lead indicator of expected sales.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 7 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
- 53-week fiscal years add a 14th week to some quarters, inflating those quarters by ~7.7% versus a 13-week quarter.
