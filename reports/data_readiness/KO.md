# Data readiness: KO (COCA COLA CO)

**Verdict: READY WITH CAVEATS**  
Sector: Consumer staples | CIK 21344 | fiscal year ends in Dec

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 69 (2009Q1 to 2026Q1) |
| Contiguous run used for modelling | 69 quarters from 2009Q1 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-04-03 / 2026-10-21 - **STALE**: newer filings are missing from companyfacts |
| Q4 / quarters derived from YTD or annual minus 9M | 17 |
| Tags used | Revenues: 2018Q3..2026Q1 (31); SalesRevenueGoodsNet: 2009Q1..2018Q2 (38) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 90 of 118 |
| Periods whose value changed between filings | 5 |
| Quarters restated >0.1% / >1% | 5 / 5 (max 10.7%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 1 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Largest restatements (first-reported vs latest-reported, USD):

- 2017Q4: 7,512,000,000 -> 8,314,000,000 (+10.68%)
- 2018Q4: 7,058,000,000 -> 7,806,000,000 (+10.60%)
- 2019Q1: 8,020,000,000 -> 8,694,000,000 (+8.40%)
- 2018Q3: 8,245,000,000 -> 8,775,000,000 (+6.43%)
- 2018Q2: 8,927,000,000 -> 9,421,000,000 (+5.53%)

The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2018Q3 | SalesRevenueGoodsNet | Revenues | 5 | +0.00 |

Tag disagreements, any two tags >1% apart in the same quarter (first 5). Lower-priority tags are often components (e.g. product-only sales), so a disagreement is a flag to read, not an error:

- {'quarter': '2018Q2', 'Revenues': 9421000000.0, 'SalesRevenueGoodsNet': 8927000000.0}

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | no | 0 | - | - |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | yes | 26 | 2017Q3..2026Q1 | quarterly |
| InventoryNet (Inventory (instant)) | yes | 69 | 2008Q4..2026Q1 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 69 | 2008Q4..2026Q1 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | no | 0 | - | - |
| OperatingIncomeLoss (Operating income) | yes | 54 | 2008Q2..2026Q1 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 18 | 2009Q1..2026Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | no | 0 | - | - |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | yes | 54 | 2008Q2..2026Q1 | quarterly |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Pricing drives recent growth, so CPI is a plausible driver; volume data is not in XBRL facts.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 17 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
