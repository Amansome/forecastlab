from __future__ import annotations

import pandas as pd
import pandera.errors as pe
import pytest

from forecastlab import backtest, export, monitor


def valid_frame():
    return pd.DataFrame([
        ("Actual", "Q1 FY26", "Revenue", "AAPL", 95000.0),
        ("Actual", "Q2 FY26", "Revenue", "AAPL", 94000.0),
        ("Fcst_LightGBM", "Q3 FY26", "Revenue", "AAPL", 101000.0),
        ("Fcst_ETS", "Q3 FY26", "Revenue", "AAPL", 99000.0),
    ], columns=export.COLUMNS)


def test_time_period_format():
    assert export.time_period(pd.Period("2026Q3", "Q")) == "Q3 FY26"
    assert export.time_period(pd.Period("2009Q1", "Q")) == "Q1 FY09"


def test_schema_accepts_valid_file():
    export.SCHEMA.validate(valid_frame())


@pytest.mark.parametrize("mutate", [
    lambda d: d.assign(Value=-1.0),                                          # negative value
    lambda d: d.assign(**{"Time Period": "2026Q3"}),                         # wrong period format
    lambda d: d.assign(Entity="ZZZZ"),                                       # unknown entity
    lambda d: pd.concat([d, d.tail(1)], ignore_index=True),                                  # duplicate key
    lambda d: d.assign(Extra=1),                                             # unexpected column
    lambda d: d.replace({"Q3 FY26": "Q1 FY26"}),                             # forecast not after actuals
])
def test_schema_rejects_bad_files(mutate):
    with pytest.raises((pe.SchemaError, pe.SchemaErrors)):
        export.SCHEMA.validate(mutate(valid_frame()), lazy=True)


def test_export_end_to_end_on_synthetic_panel(synth_panel):
    schema = export.build_schema(list(synth_panel.series))
    table = backtest.build_table(synth_panel)
    fc = export.forecast_at(synth_panel, table, synth_panel.end, backtest.lgbm_variants(table))
    flat = export.to_anaplan(synth_panel, fc)
    schema.validate(flat, lazy=True)
    assert list(flat.columns) == export.COLUMNS
    assert set(flat["Version"]) == {"Actual", "Fcst_LightGBM", "Fcst_LightGBM_Macro", "Fcst_ETS", "Fcst_SeasonalNaive"}


def _fc(errors):
    rows = []
    for i, e in enumerate(errors):
        rows.append({"ticker": f"C{i}", "origin": "2025Q4", "h": 1, "target_quarter": "2026Q1", "model": "lgbm",
                     "forecast": 100 * (1 + e)})
    return pd.DataFrame(rows), pd.DataFrame({"ticker": [f"C{i}" for i in range(len(errors))],
                                             "target_quarter": "2026Q1", "revenue": 100.0, "available_date": "2026-05-01"})


def test_monitor_ok_review_retrain():
    bt = pd.Series({f"C{i}": 3.0 for i in range(10)})
    fc, act = _fc([0.01, -0.02, 0.03, -0.01, 0.0, 0.02, -0.03, 0.01, -0.01, 0.0])
    assert monitor.check_drift(fc, act, bt, "lgbm")[1]["status"] == "OK"
    fc, act = _fc([0.20, -0.02, 0.03, -0.01, 0.0, 0.02, -0.03, 0.01, -0.01, 0.0])
    checked, s = monitor.check_drift(fc, act, bt, "lgbm")
    assert s["status"] == "REVIEW" and checked.set_index("ticker").loc["C0", "drift"]
    fc, act = _fc([0.20, 0.15, 0.12, 0.10, 0.0, 0.02, -0.03, 0.01, -0.01, 0.0])
    assert monitor.check_drift(fc, act, bt, "lgbm")[1]["status"] == "RETRAIN"
    fc, act = _fc([0.06, 0.05, 0.07, 0.05, 0.06, 0.05, 0.04, 0.06, 0.05, 0.07])   # no single breach, but biased
    assert monitor.check_drift(fc, act, bt, "lgbm")[1]["status"] == "RETRAIN"


def test_monitor_threshold_scales_with_backtest_error():
    fc, act = _fc([0.10])
    noisy = pd.Series({"C0": 8.0})                           # threshold = max(8, 16) = 16%
    assert monitor.check_drift(fc, act, noisy, "lgbm")[1]["status"] == "OK"
