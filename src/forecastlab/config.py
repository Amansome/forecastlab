"""Central configuration: companies, XBRL tags, paths and backtest settings.

Everything that changes results lives here so a reviewer can see every
choice in one place. Model hyperparameters are fixed a priori and are NOT
tuned on the backtest folds.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.environ.get("FORECASTLAB_ROOT", Path(__file__).resolve().parents[2]))
DATA_RAW = ROOT / "data" / "raw"
EDGAR_CACHE = DATA_RAW / "edgar"
FRED_CACHE = DATA_RAW / "fred"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
READINESS = REPORTS / "data_readiness"
EXPORTS = ROOT / "exports"

# SEC asks automated clients to identify themselves with a contact address.
# Set SEC_USER_AGENT="Your Name your.email@example.com" before running ingest.
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "ForecastLab research project forecastlab@example.com")
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


@dataclass(frozen=True)
class Company:
    ticker: str
    cik: int
    name: str
    sector: str


COMPANIES: list[Company] = [
    Company("AAPL", 320193, "Apple Inc.", "Technology hardware"),
    Company("MSFT", 789019, "Microsoft Corp.", "Software"),
    Company("GOOGL", 1652044, "Alphabet Inc.", "Internet / advertising"),
    Company("AMZN", 1018724, "Amazon.com Inc.", "Retail / cloud"),
    Company("WMT", 104169, "Walmart Inc.", "Retail"),
    Company("TGT", 27419, "Target Corp.", "Retail"),
    Company("HD", 354950, "Home Depot Inc.", "Retail"),
    Company("KO", 21344, "Coca-Cola Co.", "Consumer staples"),
    Company("PG", 80424, "Procter & Gamble Co.", "Consumer staples"),
    Company("NKE", 320187, "Nike Inc.", "Consumer discretionary"),
]
TICKERS = [c.ticker for c in COMPANIES]

# Revenue tags in priority order. The first two are the tags named in the
# project brief. SalesRevenueNet is a documented fallback: it was the common
# pre-ASC 606 (pre-2018) tag, and without it most companies lose ~9 years of
# history. Which tag supplied each quarter is recorded and reported.
REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
]
ALLOWED_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT", "10-QT"}

# A fiscal quarter is 13 weeks (91 days) or 14 weeks in a 53-week year.
QUARTER_DAYS = (75, 105)
ANNUAL_DAYS = (350, 380)

# Candidate driver concepts checked for coverage in the readiness report.
# They are documented for future work; the model itself only uses revenue
# history plus (optionally) macro series.
DRIVER_CONCEPTS = {
    "CostOfRevenue": "Cost of revenue",
    "CostOfGoodsAndServicesSold": "Cost of goods and services sold",
    "InventoryNet": "Inventory (instant)",
    "AccountsReceivableNetCurrent": "Accounts receivable (instant)",
    "ContractWithCustomerLiabilityCurrent": "Deferred revenue / contract liability (instant)",
    "OperatingIncomeLoss": "Operating income",
    "PaymentsToAcquirePropertyPlantAndEquipment": "Capex (YTD duration)",
    "ResearchAndDevelopmentExpense": "R&D expense",
    "SellingGeneralAndAdministrativeExpense": "SG&A expense",
}

# FRED macro series (monthly). CPIAUCNS is not seasonally adjusted and is not
# revised after release. RSAFS (retail sales) IS revised; we only have the
# latest vintage, which is a known, documented look-ahead risk. The pipeline
# therefore reports the ML model with and without macro features.
FRED_SERIES = {
    "RSAFS": "Advance retail sales: retail and food services (SA, $M)",
    "CPIAUCNS": "CPI-U all items (NSA, index)",
}
# Days after calendar-quarter end before that quarter's macro data counts as
# published. The third month of a quarter is released ~2 weeks after month end.
MACRO_PUBLICATION_LAG_DAYS = 30

# Backtest design.
HORIZONS = [1, 2, 3, 4]
N_FOLDS = 12               # rolling origins, expanding training window
MIN_TRAIN_QUARTERS = 16    # minimum history before the first feature row
SEASON = 4
SERIES_START = "2009Q1"    # XBRL filings start 2009-2011

LGBM_PARAMS = dict(
    objective="l1",
    n_estimators=300,
    learning_rate=0.03,
    num_leaves=8,
    min_child_samples=20,
    subsample=1.0,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    random_state=42,
    deterministic=True,
    force_row_wise=True,
    n_jobs=1,
    verbose=-1,
)

BOOTSTRAP_RESAMPLES = 5000
BOOTSTRAP_SEED = 7

# Monitoring thresholds.
DRIFT_ABS_APE = 0.08       # flag if absolute % error > 8% ...
DRIFT_REL_MULT = 2.0       # ... AND > 2x the company's backtest MAPE
RETRAIN_SHARE = 0.3        # recommend retrain if >=30% of companies drift
