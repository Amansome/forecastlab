"""Forecast accuracy metrics and bootstrap confidence intervals."""
from __future__ import annotations

import numpy as np
import pandas as pd


def mape(actual, forecast) -> float:
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    return float(np.mean(np.abs((a - f) / a)) * 100)


def smape(actual, forecast) -> float:
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    return float(np.mean(2 * np.abs(f - a) / (np.abs(a) + np.abs(f))) * 100)


def mase_scale(train: pd.Series, m: int = 4) -> float:
    """In-sample MAE of the seasonal naive forecast on the training window."""
    v = np.asarray(train, float)
    return float(np.mean(np.abs(v[m:] - v[:-m])))


def mase(actual, forecast, scale: float) -> float:
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    return float(np.mean(np.abs(a - f)) / scale)


def bootstrap_mean_diff(a: np.ndarray, b: np.ndarray, n: int = 5000, seed: int = 0,
                        clusters: np.ndarray | None = None) -> dict:
    """95% percentile CI for mean(a - b) over paired units.

    With `clusters`, whole clusters (companies) are resampled, which respects
    correlation between folds of the same company and gives wider intervals.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx = rng.integers(0, len(d), size=(n, len(d)))
        boots = d[idx].mean(axis=1)
    else:
        clusters = np.asarray(clusters)
        uniq = np.unique(clusters)
        groups = [d[clusters == c] for c in uniq]
        sums = np.array([g.sum() for g in groups])
        counts = np.array([len(g) for g in groups])
        pick = rng.integers(0, len(uniq), size=(n, len(uniq)))
        boots = sums[pick].sum(axis=1) / counts[pick].sum(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"mean_diff": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi),
            "share_resamples_a_lower": float(np.mean(boots < 0))}
