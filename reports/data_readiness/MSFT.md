# Data readiness: MSFT (MICROSOFT CORPORATION)

**Verdict: READY WITH CAVEATS**  
Sector: Software | CIK 789019 | fiscal year ends in Jun

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-06-30 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 6 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q2..2026Q2 (33); Revenues: 2009Q1..2010Q4 (8); SalesRevenueNet: 2011Q1..2018Q1 (29) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 111 of 165 |
| Periods whose value changed between filings | 10 |
| Quarters restated >0.1% / >1% | 4 / 4 (max 9.8%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 10 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Largest restatements (first-reported vs latest-reported, USD):

- 2017Q2: 23,317,000,000 -> 25,605,000,000 (+9.81%)
- 2016Q3: 20,453,000,000 -> 21,928,000,000 (+7.21%)
- 2016Q4: 24,090,000,000 -> 25,826,000,000 (+7.21%)
- 2017Q1: 22,090,000,000 -> 23,212,000,000 (+5.08%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2011Q1 | Revenues | SalesRevenueNet | 7 | +0.00 |
| 2018Q2 | SalesRevenueNet | RevenueFromContractWithCustomerExcludingAssessedTax | 7 | +5.08 |

Tag disagreements, any two tags >1% apart in the same quarter (first 5). Lower-priority tags are often components (e.g. product-only sales), so a disagreement is a flag to read, not an error:

- {'quarter': '2015Q3', 'SalesRevenueGoodsNet': 15219000000.0, 'SalesRevenueNet': 20379000000.0}
- {'quarter': '2015Q4', 'SalesRevenueGoodsNet': 17974000000.0, 'SalesRevenueNet': 23796000000.0}
- {'quarter': '2016Q1', 'SalesRevenueGoodsNet': 14321000000.0, 'SalesRevenueNet': 20531000000.0}
- {'quarter': '2016Q3', 'RevenueFromContractWithCustomerExcludingAssessedTax': 21928000000.0, 'SalesRevenueGoodsNet': 13493000000.0, 'SalesRevenueNet': 20453000000.0}
- {'quarter': '2016Q4', 'RevenueFromContractWithCustomerExcludingAssessedTax': 25826000000.0, 'SalesRevenueGoodsNet': 16537000000.0, 'SalesRevenueNet': 24090000000.0}

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | yes | 30 | 2008Q3..2018Q1 | quarterly |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 27 | 2017Q3..2026Q1 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 69 | 2009Q2..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 69 | 2009Q2..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 34 | 2017Q2..2026Q2 | instant |
| OperatingIncomeLoss (Operating income) | yes | 60 | 2008Q3..2026Q1 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 54 | 2008Q3..2026Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | yes | 54 | 2008Q3..2026Q1 | quarterly |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | no | 0 | - | - |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Contract liabilities (deferred revenue) are a known leading indicator for subscription revenue.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 6 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
