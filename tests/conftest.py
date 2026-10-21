"""Synthetic fixtures: tests never touch the network or the real data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastlab.data import panel_from_frame


def make_series(n=48, start="2012Q1", growth=0.015, season=(1.0, 1.04, 0.97, 1.18), noise=0.02, level=1e9, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.period_range(start, periods=n, freq="Q")
    trend = level * np.exp(growth * np.arange(n))
    s = np.array([season[p.quarter - 1] for p in idx])
    return pd.Series(trend * s * np.exp(rng.normal(0, noise, n)), index=idx)


def panel_frame(n=48, n_companies=4, seed=0):
    rows = []
    for i in range(n_companies):
        y = make_series(n=n, growth=0.01 + 0.005 * i, level=(i + 1) * 1e9, seed=seed + i)
        for q, v in y.items():
            rows.append({"ticker": f"C{i}", "quarter": str(q), "revenue": v,
                         "available_date": q.end_time.normalize() + pd.Timedelta(days=35 + 3 * i)})
    return pd.DataFrame(rows)


def macro_frame(start="2010Q1", n=60, seed=1):
    rng = np.random.default_rng(seed)
    q = pd.period_range(start, periods=n, freq="Q")
    return pd.DataFrame({"quarter": q.astype(str), "macro_retail_yoy": rng.normal(0.04, 0.02, n),
                         "macro_cpi_yoy": rng.normal(0.025, 0.01, n),
                         "available_date": [p.end_time.normalize() + pd.Timedelta(days=30) for p in q]})


@pytest.fixture
def synth_panel():
    return panel_from_frame(panel_frame(), macro_frame())


@pytest.fixture
def synth_frames():
    return panel_frame(), macro_frame()
