"""Anaplan-style flat import file, data dictionary, and Pandera schema validation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandera.pandas as pa

from . import backtest, config
from .data import Panel
from .models import GlobalLGBM, ets, seasonal_naive

VERSION_NAMES = {"actual": "Actual", "lgbm": "Fcst_LightGBM", "lgbm_macro": "Fcst_LightGBM_Macro",
                 "ets": "Fcst_ETS", "seasonal_naive": "Fcst_SeasonalNaive"}
COLUMNS = ["Version", "Time Period", "Line Item", "Entity", "Value"]
ACTUAL_QUARTERS = 8  # how much actual history to include next to the forecasts

DATA_DICTIONARY = pd.DataFrame([
    ("Version", "text", "Anaplan version. 'Actual' = first-reported SEC revenue; 'Fcst_<model>' = forecast from that model.",
     "; ".join(VERSION_NAMES.values()), "Fcst_LightGBM"),
    ("Time Period", "text", "Quarter on the model calendar (calendar year). Fiscal quarters are mapped to the nearest calendar quarter end.",
     r"^Q[1-4] FY\d{2}$", "Q3 FY26"),
    ("Line Item", "text", "Anaplan line item.", "Revenue", "Revenue"),
    ("Entity", "text", "Company ticker (list dimension).", "; ".join(config.TICKERS), "AAPL"),
    ("Value", "number", "Quarterly revenue in USD millions, 3 decimals. Must be finite and > 0.", "> 0", "94930.000"),
], columns=["column", "type", "description", "allowed_values", "example"])


def time_period(q: pd.Period) -> str:
    return f"Q{q.quarter} FY{q.year % 100:02d}"


def _forecast_after_actuals(df: pd.DataFrame) -> bool:
    """Every forecast period must be later than the last actual for that entity."""
    to_ord = lambda s: s.str[5:].astype(int) * 4 + s.str[1].astype(int)  # noqa: E731
    d = df.assign(o=to_ord(df["Time Period"]))
    last_act = d[d["Version"] == "Actual"].groupby("Entity")["o"].max()
    f = d[d["Version"] != "Actual"]
    return bool((f["o"].to_numpy() > last_act.reindex(f["Entity"]).to_numpy()).all())


def build_schema(entities: list[str] | None = None) -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
    {
        "Version": pa.Column(str, pa.Check.isin(list(VERSION_NAMES.values()))),
        "Time Period": pa.Column(str, pa.Check.str_matches(r"^Q[1-4] FY\d{2}$")),
        "Line Item": pa.Column(str, pa.Check.isin(["Revenue"])),
        "Entity": pa.Column(str, pa.Check.isin(entities or config.TICKERS)),
        "Value": pa.Column(float, [pa.Check.gt(0), pa.Check(lambda s: np.isfinite(s), error="finite")]),
    },
    checks=[pa.Check(_forecast_after_actuals, error="forecast period not after last actual")],
    unique=["Version", "Time Period", "Line Item", "Entity"],
    strict=True, ordered=True, coerce=False,
    )


SCHEMA = build_schema()


def forecast_at(panel: Panel, table: pd.DataFrame, T: pd.Period, variants: dict) -> pd.DataFrame:
    """Forecasts for T+1..T+4 from every exported model, trained only on data <= T."""
    train, test = backtest.split_fold(table, T)
    backtest.assert_no_leakage(train, test, T, panel)
    rows = []
    for name, cols in variants.items():
        preds = GlobalLGBM(cols).fit(train).predict(test)
        rows += [{"ticker": t, "origin": str(T), "h": h, "target_quarter": str(T + h), "model": name, "forecast": p}
                 for t, h, p in zip(test["ticker"], test["h"], preds)]
    for ticker, y in panel.series.items():
        hist = y[y.index <= T]
        for name, fc in (("ets", ets(hist, config.HORIZONS)[0]), ("seasonal_naive", seasonal_naive(hist, config.HORIZONS))):
            rows += [{"ticker": ticker, "origin": str(T), "h": h, "target_quarter": str(T + h), "model": name, "forecast": v}
                     for h, v in fc.items()]
    return pd.DataFrame(rows)


def to_anaplan(panel: Panel, fc: pd.DataFrame) -> pd.DataFrame:
    T = pd.Period(fc["origin"].iloc[0], "Q")
    rows = []
    for ticker, y in panel.series.items():
        for q, v in y[(y.index <= T) & (y.index > T - ACTUAL_QUARTERS)].items():
            rows.append(("Actual", time_period(q), "Revenue", ticker, round(v / 1e6, 3)))
    for r in fc.itertuples():
        rows.append((VERSION_NAMES[r.model], time_period(pd.Period(r.target_quarter, "Q")), "Revenue", r.ticker,
                     round(r.forecast / 1e6, 3)))
    return pd.DataFrame(rows, columns=COLUMNS)


def run_export(panel: Panel, table: pd.DataFrame) -> pd.DataFrame:
    config.EXPORTS.mkdir(parents=True, exist_ok=True)
    variants = backtest.lgbm_variants(table)
    T = panel.end
    fc = forecast_at(panel, table, T, variants)
    fc.to_csv(config.REPORTS / f"forecasts_origin_{T}.csv", index=False)
    # Forecasts one cycle earlier, so the monitor can be run on actuals that have since arrived.
    forecast_at(panel, table, T - 1, variants).to_csv(config.REPORTS / f"forecasts_origin_{T - 1}.csv", index=False)
    flat = to_anaplan(panel, fc)
    validated = build_schema(list(panel.series)).validate(flat, lazy=True)
    validated.to_csv(config.EXPORTS / "anaplan_revenue_import.csv", index=False, float_format="%.3f")
    DATA_DICTIONARY.to_csv(config.EXPORTS / "data_dictionary.csv", index=False)
    (config.EXPORTS / "validation_report.txt").write_text(
        f"Pandera schema validation: PASSED\nrows={len(validated)}\norigin={T}\n"
        f"versions={sorted(validated['Version'].unique())}\nentities={sorted(validated['Entity'].unique())}\n"
        f"periods={sorted(validated['Time Period'].unique(), key=lambda s: (s[5:], s[:2]))}\n")
    print(f"[export] {len(validated)} rows validated -> exports/anaplan_revenue_import.csv (origin {T})")
    return validated
