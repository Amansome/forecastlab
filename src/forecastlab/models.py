"""Baselines (naive, seasonal naive, ETS) and the global LightGBM model."""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from . import config


def naive(history: pd.Series, horizons) -> dict[int, float]:
    """Last observed quarter, carried forward."""
    return {h: float(history.iloc[-1]) for h in horizons}


def seasonal_naive(history: pd.Series, horizons, m: int = config.SEASON) -> dict[int, float]:
    """Same quarter last year."""
    origin = history.index.max()
    return {h: float(history[origin + h - m]) for h in horizons}


def ets(history: pd.Series, horizons, m: int = config.SEASON) -> tuple[dict[int, float], bool]:
    """Damped additive-trend, additive-seasonal Holt-Winters on log revenue.

    Logs make seasonality multiplicative in levels. Returns (forecasts, ok);
    if the optimiser fails we fall back to seasonal naive and report it.
    """
    y = np.log(history.astype(float).to_numpy())
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add",
                                       seasonal_periods=m, initialization_method="estimated").fit()
            fc = fit.forecast(max(horizons))
        if not np.all(np.isfinite(fc)):
            raise ValueError("non-finite forecast")
        return {h: float(np.exp(fc[h - 1])) for h in horizons}, True
    except Exception:  # noqa: BLE001 - any optimiser failure falls back
        return seasonal_naive(history, horizons, m), False


class GlobalLGBM:
    """One LightGBM model pooled across companies, predicting YoY log growth."""

    def __init__(self, feature_cols: list[str], params: dict | None = None):
        self.feature_cols = feature_cols
        self.params = params or config.LGBM_PARAMS
        self.model: lgb.LGBMRegressor | None = None

    def fit(self, rows: pd.DataFrame) -> "GlobalLGBM":
        rows = rows.dropna(subset=["target"]).sort_values(["ticker", "origin", "h"])
        self.model = lgb.LGBMRegressor(**self.params)
        self.model.fit(rows[self.feature_cols], rows["target"])
        return self

    def predict_growth(self, rows: pd.DataFrame) -> np.ndarray:
        return self.model.predict(rows[self.feature_cols])

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        """Revenue forecast = base quarter (t-4) x exp(predicted YoY log growth)."""
        return rows["base"].to_numpy() * np.exp(self.predict_growth(rows))
