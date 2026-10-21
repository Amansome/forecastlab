"""Leakage tests: nothing after the forecast origin may influence a forecast."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastlab import backtest, features
from forecastlab.data import panel_from_frame


def _corrupt_after(frames, T):
    """Replace every revenue and macro value after T with garbage."""
    df, macro = frames[0].copy(), frames[1].copy()
    after = pd.PeriodIndex(df["quarter"], freq="Q") > T
    df.loc[after, "revenue"] = df.loc[after, "revenue"] * np.random.default_rng(0).uniform(0.2, 5.0, after.sum())
    m_after = pd.PeriodIndex(macro["quarter"], freq="Q") > T
    macro.loc[m_after, ["macro_retail_yoy", "macro_cpi_yoy"]] = 9.99
    return df, macro


def test_origin_features_rejects_future_history(synth_panel):
    y = next(iter(synth_panel.series.values()))
    with pytest.raises(ValueError):
        features.origin_features(y, y.index[20], 1)


def test_features_unchanged_when_future_is_corrupted(synth_frames):
    clean = panel_from_frame(*synth_frames)
    T = clean.end - 6
    dirty = panel_from_frame(*_corrupt_after(synth_frames, T))
    ft_clean = backtest.build_table(clean)
    ft_dirty = backtest.build_table(dirty)
    cols = features.feature_columns(ft_clean, use_macro=True) + ["base"]
    a = ft_clean[ft_clean["origin"] <= T].reset_index(drop=True)
    b = ft_dirty[ft_dirty["origin"] <= T].reset_index(drop=True)
    pd.testing.assert_frame_equal(a[cols], b[cols])


def test_training_labels_never_after_origin(synth_panel):
    table = backtest.build_table(synth_panel)
    for T in backtest.fold_origins(synth_panel, n_folds=4):
        train, test = backtest.split_fold(table, T)
        assert train["target_quarter"].max() <= T
        assert (train["origin"] < T).all()
        assert (test["origin"] == T).all()
        backtest.assert_no_leakage(train, test, T, synth_panel)


def test_assert_no_leakage_catches_injected_future_label(synth_panel):
    table = backtest.build_table(synth_panel)
    T = backtest.fold_origins(synth_panel, n_folds=1)[0]
    train, test = backtest.split_fold(table, T)
    leaky = pd.concat([train, table[(table["target_quarter"] > T) & table["target"].notna()].head(1)])
    with pytest.raises(AssertionError):
        backtest.assert_no_leakage(leaky, test, T, synth_panel)


def test_assert_no_leakage_catches_label_filed_after_forecast_date(synth_panel):
    table = backtest.build_table(synth_panel)
    T = backtest.fold_origins(synth_panel, n_folds=1)[0]
    train, test = backtest.split_fold(table, T)
    ticker = train["ticker"].iloc[0]
    q = T - 1                                      # not T itself: that would move the forecast date too
    synth_panel.available[ticker][q] = synth_panel.cycle_date(T) + pd.Timedelta(days=400)
    with pytest.raises(AssertionError):
        backtest.assert_no_leakage(train, test, T, synth_panel)


def test_macro_uses_only_published_values(synth_frames):
    macro = panel_from_frame(*synth_frames).macro
    as_of = pd.Timestamp("2015-06-01")
    f = features.macro_features(macro, as_of)
    # 2015Q1 data is published 2015-04-30; 2015Q2 not until 2015-07-30.
    assert f["_macro_quarter"] == "2015Q1"


def test_end_to_end_forecasts_unchanged_when_future_is_corrupted(synth_frames):
    """Strongest check: full backtest forecasts for origin T are bit-identical
    whether the data after T is real or garbage."""
    clean = panel_from_frame(*synth_frames)
    T = clean.end - 6
    dirty = panel_from_frame(*_corrupt_after(synth_frames, T))
    fc_clean, _ = backtest.run_backtest(clean, origins=[T])
    fc_dirty, _ = backtest.run_backtest(dirty, origins=[T])
    key = ["ticker", "h", "model"]
    a = fc_clean.sort_values(key).reset_index(drop=True)
    b = fc_dirty.sort_values(key).reset_index(drop=True)
    np.testing.assert_allclose(a["forecast"], b["forecast"], rtol=0, atol=0)
    assert set(a["model"]) == {"naive", "seasonal_naive", "ets", "lgbm", "lgbm_macro"}
