# ForecastLab

A reproducible pipeline that forecasts quarterly revenue for 10 US public companies from free SEC EDGAR data. It compares naive, seasonal naive, and ETS baselines with a global LightGBM model under a rolling-origin backtest. Everything runs from one command. Every number in this README comes from files the pipeline writes under `reports/`.

> **Status: code complete and tested, but no results yet.** The pipeline has not been run on real data, because the build environment could not reach `data.sec.gov` or `fred.stlouisfed.org`. This README therefore contains no results table. Run `make reproduce` with network access, and the results appear in `reports/results.md`.

## Quickstart

```bash
python -m pip install -e ".[dev]"          # Python >= 3.11
export SEC_USER_AGENT="Your Name your.email@example.com"   # SEC requires a contact in the User-Agent
make test         # unit + leakage tests, no network needed
make reproduce    # ingest (cached) -> quality -> backtest -> SHAP -> export -> monitor
make offline      # rerun modelling from committed data/processed/ (no network)
make spark        # optional: PySpark re-implementation of features + LightGBM backtest, with parity check
```

The individual steps are also available, e.g. `python -m forecastlab backtest`, and `--no-macro` skips FRED.

## Pipeline

```
SEC companyfacts JSON ─┐                       ┌─ reports/data_readiness/<TICKER>.md
FRED RSAFS, CPIAUCNS ──┼─> data/raw (cache) ─> quality ─> data/processed/*.csv
                       │                                     │
                       └─────────────────────────────────────┴─> features (leak-free)
                                                                   │
                     backtest: 12 rolling origins x h=1..4 <───────┘
                       ├─ naive / seasonal naive / ETS (per company)
                       └─ LightGBM global model (with / without macro)
                     ─> metrics, stability, bootstrap CIs ─> reports/results.md + figures
                     ─> SHAP (out-of-sample) ─> reports/explainability.md
                     ─> Anaplan flat file + Pandera validation ─> exports/
                     ─> drift monitor on newly arrived actuals ─> reports/monitoring_*.md
```

## Data

* **Source.** SEC `companyfacts` API, one JSON per company, cached in `data/raw/edgar/` with a download manifest. Revenue tags, in priority order: `Revenues`, then `RevenueFromContractWithCustomerExcludingAssessedTax`, then `SalesRevenueNet`. The third tag is a documented fallback that recovers pre-2018 (pre-ASC 606) history. The tag behind every quarter is recorded.
* **First-reported values.** Each period appears in several filings. The model uses the value from the **first** filing, which is what was known at the time. The latest value is kept only to measure restatements.
* **Fiscal Q4.** 10-Ks report only the full year, so Q4 (and any missing quarter) is derived from two cumulative facts with the same start date, e.g. annual minus 9-month YTD. The subtraction is point-in-time: it uses the 9M value known on the 10-K filing date.
* **Calendar alignment.** Fiscal quarters are mapped to the nearest calendar quarter end. For example, Walmart's quarter ending Apr 30 becomes Q1.
* **Quality checks** (`reports/data_readiness/<TICKER>.md`): missing quarters, duplicate filings, values that changed between filings, restatements (>0.1% and >1%), non-USD units, excluded form types, tag disagreements, calendar collisions, 53-week quarters, QoQ/YoY outliers, and a READY / READY WITH CAVEATS / NOT READY verdict. Each report also lists candidate driver concepts and how many quarters they cover, plus the material gaps.
* **Macro (optional).** FRED `RSAFS` (retail sales) and `CPIAUCNS` (CPI, NSA). Each is converted to quarterly YoY log growth and treated as published 30 days after quarter end.

## Models

| Model | What it is |
|---|---|
| Naive | last quarter carried forward |
| Seasonal naive | same quarter last year |
| ETS | Holt-Winters on log revenue: damped additive trend, additive seasonality (period 4), fit per company per fold |
| LightGBM | one global model across companies. It predicts YoY log growth of the target quarter, and the forecast is y[t-4] x exp(growth). Features: horizon, target-quarter flags, the last 4 YoY growths, 4- and 8-quarter rolling means of YoY growth, YoY volatility, YoY acceleration, last QoQ change, the base quarter's own YoY growth, and the base quarter and latest quarter vs the trailing-4 average |
| LightGBM + macro | the same model plus retail sales YoY, CPI YoY, and the change in retail sales YoY |

LightGBM hyperparameters are fixed in `config.py` and were **not tuned on the backtest**. Tuning on the test folds would overstate accuracy.

## Backtest design

* **Rolling origin with an expanding window.** There are 12 fold origins, ending 4 quarters before the latest quarter all 10 companies have reported, so every fold has all four horizons observed. Each origin forecasts h = 1..4.
* **Metrics** per (company, fold), computed over the 4 horizons: MAPE, sMAPE, and MASE. MASE is scaled by the in-sample seasonal-naive MAE on that fold's training window.
* **Stability**: for each company, the std and variance of fold-level MAPE across folds, averaged over companies.
* **Bootstrap 95% CIs** on the mean MASE difference between LightGBM and each comparator. Two resampling schemes are reported: (company, fold) cells, and whole companies. The company-level bootstrap is the honest one, because consecutive folds overlap and are correlated.

## Leakage controls

1. Features are built only from a series already truncated at the origin. `origin_features` raises if it is handed future data.
2. A training row is used only if its **target** quarter is at or before the fold origin.
3. Every fold asserts at runtime that each training label was filed with the SEC on or before the forecast date. The forecast date is the day the last of the 10 companies filed the origin quarter. The same assertion covers macro features against their publication date.
4. The tests (`tests/test_leakage.py`) replace every revenue and macro value after the origin with random garbage, then assert that the features **and the full backtest forecasts of all five models** are bit-identical. They also check that the runtime assertion catches an injected future label and a label filed after the forecast date.

## Integration prototype (Anaplan-style)

`exports/anaplan_revenue_import.csv` has the columns `Version, Time Period, Line Item, Entity, Value`, in USD millions. Versions are `Actual` and `Fcst_<model>`. Time periods look like `Q3 FY26` on a calendar-year model calendar. `exports/data_dictionary.csv` documents every column. The file is validated by a Pandera schema (`export.build_schema`) that checks:

* types, allowed versions and entities, and the period format;
* values are finite and greater than zero;
* (Version, Time Period, Line Item, Entity) is unique;
* there are no extra columns;
* every forecast period falls after the entity's last actual.

## Monitoring

`python -m forecastlab monitor` compares stored forecasts with actuals that arrived after the forecast origin.

* A company is flagged when its absolute error exceeds **both** 8% and 2x its own backtest MAPE.
* The run recommends **RETRAIN** if at least 30% of companies breach, or if errors are systematically one-signed. It recommends **REVIEW** if any single company breaches, and **OK** otherwise.
* Two forecast files are checked: one from the previous origin, with real actuals for all companies, and one from the current origin, with actuals from any company that has already filed the next quarter.

## PySpark

`make spark` (`src/forecastlab/spark_backtest.py`) re-implements the feature step with Spark window functions. It runs the 12 LightGBM folds in parallel via `groupBy("fold").applyInPandas`, then compares the features and forecasts with the pandas pipeline. It runs in **local mode (`local[*]`), not on Databricks**. On a synthetic test panel it matched the pandas forecasts to about 1e-15 relative difference with zero future-label rows. It has **not yet been run on the real data.**

## Results

Not yet produced. See the status note at the top.

## Limitations (known before any results)

* Fifty or so quarters per company is a small sample. Ten companies and 12 overlapping folds give wide confidence intervals.
* Revenue history is the only company-specific input. Guidance, segments, product cycles, M&A, and FX are absent, and segment data is not in companyfacts at all.
* Retail sales (RSAFS) is the latest revised vintage, not the vintage available at the time. This is a mild, documented look-ahead in the macro variant only. CPI NSA is not revised. The revenue-only LightGBM has no such issue.
* Calendar mapping can put fiscal quarters up to about 45 days away from the calendar quarter end. 53-week years inflate one quarter by roughly 7.7%.
* Derived quarters (usually Q4) inherit any restatement in either component.

## Repository layout

```
src/forecastlab/   config, ingest, edgar (parsing), quality (checks + readiness), data, features,
                   models, metrics, backtest, explain (SHAP), export (Anaplan + Pandera), monitor,
                   plots, report, spark_backtest, cli
tests/             EDGAR parsing, leakage, metrics/models/backtest smoke, export schema, monitor
data/processed/    committed processed panel (raw cache in data/raw/ is git-ignored)
reports/           generated results, readiness reports, SHAP, monitoring, figures
exports/           Anaplan-style import file, data dictionary, validation report
```
