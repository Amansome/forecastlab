"""Leak-free feature engineering for the global LightGBM model.

Design rule: every feature row is built by `origin_features(history, ...)`
where `history` has ALREADY been truncated to quarters <= origin. Nothing in
this module can see a value after the origin; tests/test_leakage.py checks
this by corrupting the future and asserting features and forecasts do not
change.

Target: YoY log growth of the target quarter, log(y[t]) - log(y[t-4]),
with t = origin + h. For h <= 4 the base quarter t-4 is known at the origin,
so a forecast is y[t-4] * exp(predicted growth). Modelling growth instead of
levels lets one model serve companies whose revenue differs by 100x.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

MIN_HISTORY = 12  # quarters needed to compute 8 lags of YoY growth

BASE_FEATURES = [
    "h", "tq_1", "tq_2", "tq_3", "tq_4",
    "yoy_0", "yoy_1", "yoy_2", "yoy_3", "yoy_mean4", "yoy_mean8", "yoy_std8", "yoy_accel",
    "qoq_0", "base_yoy", "base_vs_trailing4", "level_vs_ma4",
]
MACRO_FEATURES = ["macro_retail_yoy", "macro_cpi_yoy", "macro_retail_yoy_chg"]


def origin_features(history: pd.Series, origin: pd.Period, h: int) -> dict:
    """Features for forecasting origin+h using only `history` (all <= origin)."""
    if history.index.max() > origin:
        raise ValueError("history contains data after the origin")
    l = np.log(history.astype(float))
    lag = lambda k: l[origin - k]                                     # noqa: E731
    yoy = [lag(k) - lag(k + 4) for k in range(8)]
    t = origin + h
    base = l[t - 4]
    trailing4 = np.log(np.mean(np.exp([lag(k) for k in range(4)])))
    f = {
        "h": h,
        **{f"tq_{i}": int(t.quarter == i) for i in range(1, 5)},
        "yoy_0": yoy[0], "yoy_1": yoy[1], "yoy_2": yoy[2], "yoy_3": yoy[3],
        "yoy_mean4": float(np.mean(yoy[:4])), "yoy_mean8": float(np.mean(yoy)),
        "yoy_std8": float(np.std(yoy, ddof=1)), "yoy_accel": yoy[0] - yoy[4],
        "qoq_0": lag(0) - lag(1),
        "base_yoy": base - l[t - 8],
        "base_vs_trailing4": base - trailing4,
        "level_vs_ma4": lag(0) - trailing4,
    }
    return f


def macro_features(macro: pd.DataFrame | None, as_of: pd.Timestamp) -> dict:
    """Latest macro values published on or before `as_of` (the forecast date)."""
    if macro is None:
        return {}
    pub = macro[macro["available_date"] <= as_of]
    if len(pub) < 2:
        return {k: np.nan for k in MACRO_FEATURES}
    last, prev = pub.iloc[-1], pub.iloc[-2]
    return {
        "macro_retail_yoy": last["macro_retail_yoy"],
        "macro_cpi_yoy": last["macro_cpi_yoy"],
        "macro_retail_yoy_chg": last["macro_retail_yoy"] - prev["macro_retail_yoy"],
        "_macro_quarter": str(last["quarter"]),
    }


def build_feature_table(series: dict[str, pd.Series], horizons=None, macro: pd.DataFrame | None = None,
                        cycle_dates: dict | None = None) -> pd.DataFrame:
    """All (ticker, origin, h) rows with features, base value, and target (NaN if unobserved)."""
    horizons = horizons or config.HORIZONS
    rows = []
    for ticker, y in series.items():
        y = y.sort_index()
        idx = y.index
        for i in range(MIN_HISTORY - 1, len(idx)):
            origin = idx[i]
            history = y.iloc[: i + 1]                     # truncation happens HERE, once
            as_of = cycle_dates.get(origin) if cycle_dates else None
            mf = macro_features(macro, as_of) if (macro is not None and as_of is not None) else {}
            for h in horizons:
                t = origin + h
                actual = y.get(t, np.nan)
                base = history[t - 4]
                rows.append({
                    "ticker": ticker, "origin": origin, "target_quarter": t,
                    "base": base, "actual": actual,
                    "target": np.log(actual) - np.log(base) if pd.notna(actual) else np.nan,
                    **origin_features(history, origin, h), **mf,
                })
    return pd.DataFrame(rows)


def feature_columns(table: pd.DataFrame, use_macro: bool) -> list[str]:
    cols = list(BASE_FEATURES)
    if use_macro and all(c in table.columns for c in MACRO_FEATURES):
        cols += MACRO_FEATURES
    return cols
