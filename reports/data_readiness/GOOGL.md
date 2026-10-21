# Data readiness: GOOGL (Alphabet Inc.)

**Verdict: READY**  
Sector: Internet / advertising | CIK 1652044 | fiscal year ends in Dec

## Revenue series

| Check | Result |
|---|---|
| Quarters found | 48 (2014Q3 to 2026Q2) |
| Contiguous run used for modelling | 48 quarters from 2014Q3 (need >= 40) |
| Missing quarters | none |
| Latest period end / downloaded | 2026-06-30 / 2026-10-21 |
| Q4 / quarters derived from YTD or annual minus 9M | 12 |
| Tags used | RevenueFromContractWithCustomerExcludingAssessedTax: 2018Q4..2025Q1 (21); Revenues: 2014Q3..2026Q2 (27) |
| Non-USD units on revenue tags | none |
| Periods reported in >1 filing (duplicates) | 56 of 103 |
| Periods whose value changed between filings | 0 |
| Quarters restated >0.1% / >1% | 0 / 0 (max 0.0%) |
| Restatements that equal the next year's quarter (probable mis-dated XBRL facts) | none |
| Tag disagreements (>1%) | 0 |
| Calendar-mapping collisions | none |
| 14-week (53-week-year) quarters | none |
| QoQ moves > 50% (log) | none |
| YoY moves > 50% (log) | none |

Tag switches in the chosen series (overlap = quarters both tags report; a large median gap means a definitional break, e.g. an ASC 606 restatement or a component tag):

| From quarter | From tag | To tag | Overlap quarters | Median gap % |
|---|---|---|---|---|
| 2018Q4 | Revenues | RevenueFromContractWithCustomerExcludingAssessedTax | 22 | +0.00 |
| 2019Q1 | RevenueFromContractWithCustomerExcludingAssessedTax | Revenues | 22 | +0.00 |
| 2019Q2 | Revenues | RevenueFromContractWithCustomerExcludingAssessedTax | 22 | +0.00 |
| 2020Q4 | RevenueFromContractWithCustomerExcludingAssessedTax | Revenues | 22 | +0.00 |
| 2021Q3 | Revenues | RevenueFromContractWithCustomerExcludingAssessedTax | 22 | +0.00 |
| 2021Q4 | RevenueFromContractWithCustomerExcludingAssessedTax | Revenues | 22 | +0.00 |
| 2022Q1 | Revenues | RevenueFromContractWithCustomerExcludingAssessedTax | 22 | +0.00 |
| 2025Q2 | RevenueFromContractWithCustomerExcludingAssessedTax | Revenues | 22 | +0.00 |

## Candidate drivers in companyfacts

| Concept | Present | Quarters covered | Range | Kind |
|---|---|---|---|---|
| CostOfRevenue (Cost of revenue) | yes | 36 | 2014Q3..2026Q2 | quarterly |
| CostOfGoodsAndServicesSold (Cost of goods and services sold) | no | 0 | - | - |
| InventoryNet (Inventory (instant)) | yes | 32 | 2015Q4..2026Q2 | instant |
| AccountsReceivableNetCurrent (Accounts receivable (instant)) | yes | 45 | 2014Q4..2026Q2 | instant |
| ContractWithCustomerLiabilityCurrent (Deferred revenue / contract liability (instant)) | yes | 34 | 2017Q4..2026Q2 | instant |
| OperatingIncomeLoss (Operating income) | yes | 36 | 2014Q3..2026Q2 | quarterly |
| PaymentsToAcquirePropertyPlantAndEquipment (Capex (YTD duration)) | yes | 24 | 2015Q1..2026Q1 | quarterly |
| ResearchAndDevelopmentExpense (R&D expense) | yes | 36 | 2014Q3..2026Q2 | quarterly |
| SellingGeneralAndAdministrativeExpense (SG&A expense) | no | 0 | - | - |

Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented for future work and are **not** model inputs.

Sector note (a hypothesis, not tested here): Ad spend tracks nominal consumer activity; retail sales and CPI are weak proxies at best.

## Material gaps

- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.
- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.
- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+).
- 12 quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.
