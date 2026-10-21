from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastlab import backtest, metrics, models

from .conftest import make_series


def test_metric_values():
    a, f = [100, 200], [110, 180]
    assert metrics.mape(a, f) == pytest.approx(10.0)
    assert metrics.smape(a, f) == pytest.approx(np.mean([20 / 210, 40 / 380]) * 100)
    train = pd.Series([10, 20, 30, 40, 12, 22, 32, 42])  # seasonal diffs are all 2
    assert metrics.mase_scale(train) == pytest.approx(2.0)
    assert metrics.mase(a, f, 2.0) == pytest.approx(7.5)


def test_bootstrap_ci_is_deterministic_and_covers_truth():
    rng = np.random.default_rng(0)
    a, b = rng.normal(1.0, 0.2, 200), rng.normal(1.2, 0.2, 200)
    r1 = metrics.bootstrap_mean_diff(a, b, n=2000, seed=1)
    r2 = metrics.bootstrap_mean_diff(a, b, n=2000, seed=1)
    assert r1 == r2
    assert r1["ci_low"] < -0.2 < r1["ci_high"]       # true difference is -0.2
    assert r1["ci_high"] < 0
    clusters = np.repeat(np.arange(10), 20)
    rc = metrics.bootstrap_mean_diff(a, b, n=2000, seed=1, clusters=clusters)
    assert rc["mean_diff"] == pytest.approx(r1["mean_diff"])


def test_seasonal_naive_is_exact_on_pure_seasonal_series():
    y = make_series(n=20, growth=0.0, noise=0.0)
    fc = models.seasonal_naive(y, [1, 2, 3, 4])
    origin = y.index.max()
    for h, v in fc.items():
        assert v == pytest.approx(y[origin + h - 4])


def test_ets_tracks_clean_trend_seasonal_series():
    y = make_series(n=40, growth=0.02, noise=0.0)
    fc, ok = models.ets(y.iloc[:-4], [1, 2, 3, 4])
    assert ok
    err = [abs(fc[h] / y.iloc[-4 + h - 1] - 1) for h in range(1, 5)]
    assert max(err) < 0.03


def test_backtest_smoke(synth_panel):
    fc, meta = backtest.run_backtest(synth_panel, origins=backtest.fold_origins(synth_panel, n_folds=3))
    fm = backtest.fold_metrics(fc)
    cm = backtest.company_metrics(fm)
    sm = backtest.summary_metrics(fm, cm)
    assert set(sm["model"]) == {"naive", "seasonal_naive", "ets", "lgbm", "lgbm_macro"}
    assert len(fm) == 5 * 4 * 3            # models x companies x folds
    assert (fc.groupby(["model", "ticker", "origin"]).size() == 4).all()
    boot = backtest.bootstrap_table(fm)
    assert {"cells", "companies"} == set(boot["resample"])
    # Strongly seasonal synthetic data: naive must be the worst model.
    assert sm.set_index("model").loc["naive", "MASE"] == sm["MASE"].max()
