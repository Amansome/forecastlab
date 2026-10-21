# Data readiness: AMZN (AMAZON COM INC)

**Verdict: READY WITH CAVEATS**  
Sector: Retail / cloud | CIK 1018724 | fiscal year ends in Dec

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-06-30 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 6 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q3..2026Q2 (32); SalesRevenueNet: 2009Q1..2018Q2 (38) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 143 of 180 |
| Periods whose value changed between filings | 8 |
| Quarters restated >0.1% / >1% | 5 / 5 (max 33.8%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | 2011Q1, 2011Q2, 2011Q3 |
| Tag disagreements (>1%) | 23 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | 2009Q4, 2010Q4 |
| YoY moves > 50% (log) | none |

Largest restatements (first-reported vs latest-reported, USD):

- 2011Q1: 9,857,000,000 -> 13,185,000,000 (+33.76%)
- 2011Q2: 9,913,000,000 -> 12,834,000,000 (+29.47%)
- 2011Q3: 10,876,000,000 -> 13,806,000,000 (+26.94%)
- 2011Q4: 17,431,000,000 -> 21,268,000,000 (+22.01%)
- 2012Q4: 17,431,000,000 -> 21,268,000,000 (+22.01%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2018Q3 | SalesRevenueNet | RevenueFromContractWithCustomerExcludingAssessedTax | 7 | +0.00 |

Tag disagreements, any two tags >1% apart in the same quarter (first 5). Lower-priority tags are often components (e.g. product-only sales), so a disagreement is a flag to read, not an error:

- {'quarter': '2011Q1', 'SalesRevenueGoodsNet': 8698000000.0, 'SalesRevenueNet': 9857000000.0}
- {'quarter': '2011Q2', 'SalesRevenueGoodsNet': 8611000000.0, 'SalesRevenueNet': 9913000000.0}
- {'quarter': '2011Q3', 'SalesRevenueGoodsNet': 9382000000.0, 'SalesRevenueNet': 10876000000.0}
- {'quarter': '2012Q1', 'SalesRevenueGoodsNet': 11249000000.0, 'SalesRevenueNet': 13185000000.0}
- {'quarter': '2012Q2', 'SalesRevenueGoodsNet': 10791000000.0, 'SalesRevenueNet': 12834000000.0}

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | no | 0 | - | - |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 70 | 2008Q4..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 70 | 2008Q4..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 33 | 2017Q4..2026Q2 | instant |
| OperatingIncomeLoss (Operating income) | yes | 64 | 2008Q2..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 27 | 2008Q2..2017Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | no | 0 | - | - |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Retail sales proxies the online-store business; cloud (AWS) growth is not visible in companyfacts because segment data is excluded.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 6 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
