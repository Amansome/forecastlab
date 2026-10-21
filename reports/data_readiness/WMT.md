# Data readiness: WMT (WALMART INC.)

**Verdict: READY WITH CAVEATS**  
Sector: Retail | CIK 104169 | fiscal year ends in Jan

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-07-31 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 7 |
| Tags used | Revenues: 2009Q1..2026Q2 (68); SalesRevenueNet: 2010Q4..2011Q4 (2) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 213 of 252 |
| Periods whose value changed between filings | 33 |
| Quarters restated >0.1% / >1% | 7 / 0 (max 0.7%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 3 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2010Q4 | Revenues | SalesRevenueNet | 41 | -0.74 |
| 2011Q1 | SalesRevenueNet | Revenues | 41 | +0.74 |
| 2011Q4 | Revenues | SalesRevenueNet | 41 | -0.74 |
| 2012Q1 | SalesRevenueNet | Revenues | 41 | +0.74 |

Tag disagreements, any two tags >1% apart in the same quarter (first 5). Lower-priority tags are often components (e.g. product-only sales), so a disagreement is a flag to read, not an error:

- {'quarter': '2016Q2', 'Revenues': 120854000000.0, 'SalesRevenueNet': 119405000000.0}
- {'quarter': '2017Q2', 'RevenueFromContractWithCustomerExcludingAssessedTax': 121949000000.0, 'Revenues': 123355000000.0, 'SalesRevenueNet': 121949000000.0}
- {'quarter': '2026Q1', 'RevenueFromContractWithCustomerExcludingAssessedTax': 175684000000.0, 'Revenues': 177751000000.0}

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | yes | 66 | 2008Q2..2026Q2 | quarterly |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | no | 0 | - | - |
| InventoryNet (Inventory (instant)) | yes | 73 | 2008Q2..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | no | 0 | - | - |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | no | 0 | - | - |
| OperatingIncomeLoss (Operating income) | yes | 55 | 2008Q2..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 18 | 2009Q1..2026Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 55 | 2008Q2..2026Q2 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): US retail sales (FRED RSAFS) is a direct demand proxy; inventory build is a lead indicator of expected sales.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 7 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
