# Data readiness: PG (PROCTER & GAMBLE Co)

**Verdict: READY WITH CAVEATS**  
Sector: Consumer staples | CIK 80424 | fiscal year ends in Jun

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 70 (2009Q1 to 2026Q2) |
| Contiguous run used for modelling | 70 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-06-30 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 6 |
| Tags used | Revenues: 2018Q3..2026Q2 (32); SalesRevenueNet: 2009Q1..2018Q2 (38) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 111 of 132 |
| Periods whose value changed between filings | 30 |
| Quarters restated >0.1% / >1% | 18 / 18 (max 9.7%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 0 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Largest restatements (first-reported vs latest-reported, USD):

- 2014Q3: 20,792,000,000 -> 18,771,000,000 (-9.72%)
- 2014Q4: 20,161,000,000 -> 18,495,000,000 (-8.26%)
- 2015Q2: 17,790,000,000 -> 16,553,000,000 (-6.95%)
- 2015Q1: 18,142,000,000 -> 16,930,000,000 (-6.68%)
- 2013Q4: 22,280,000,000 -> 21,099,000,000 (-5.30%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2018Q3 | SalesRevenueNet | Revenues | 5 | +0.00 |

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | no | 0 | - | - |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 27 | 2017Q3..2026Q1 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 69 | 2009Q2..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 69 | 2009Q2..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | no | 0 | - | - |
| OperatingIncomeLoss (Operating income) | yes | 66 | 2008Q3..2026Q1 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 18 | 2008Q3..2025Q3 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | yes | 16 | 2011Q2..2026Q2 | ytd/annual only |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 54 | 2008Q3..2026Q1 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Pricing drives recent growth, so CPI is a plausible driver; volume data is not in XBRL facts.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 6 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
