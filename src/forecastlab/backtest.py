"""Rolling-origin (expanding window) backtest of baselines vs LightGBM.

For each fold origin T (the last quarter all companies have reported):
* baselines are fit per company on revenue up to T;
* LightGBM is trained on feature rows whose TARGET quarter is <= T (so every
  training label was public at the forecast date) and predicts h = 1..4.
Leakage is asserted inside every fold, not just in the tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, features
from .data import Panel
from .metrics import bootstrap_mean_diff, mape, mase, mase_scale, smape
from .models import GlobalLGBM, ets, naive, seasonal_naive

BASELINES = ["naive", "seasonal_naive", "ets"]
MODEL_LABELS = {"naive": "Naive", "seasonal_naive": "Seasonal naive", "ets": "ETS (damped, log)",
                "lgbm": "LightGBM (revenue features)", "lgbm_macro": "LightGBM + macro"}


def fold_origins(panel: Panel, n_folds: int = config.N_FOLDS) -> list[pd.Period]:
    last = panel.end - max(config.HORIZONS)       # every fold has all 4 horizons observed
    return [last - k for k in range(n_folds - 1, -1, -1)]


def cycle_dates(panel: Panel) -> dict:
    qs = sorted({q for s in panel.series.values() for q in s.index})
    return {q: panel.cycle_date(q) for q in qs}


def build_table(panel: Panel) -> pd.DataFrame:
    return features.build_feature_table(panel.series, config.HORIZONS, panel.macro, cycle_dates(panel))


def lgbm_variants(table: pd.DataFrame) -> dict[str, list[str]]:
    v = {"lgbm": features.feature_columns(table, use_macro=False)}
    if all(c in table.columns for c in features.MACRO_FEATURES):
        v["lgbm_macro"] = features.feature_columns(table, use_macro=True)
    return v


def split_fold(table: pd.DataFrame, T: pd.Period) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = table[(table["target_quarter"] <= T) & table["target"].notna()]
    test = table[table["origin"] == T]
    return train, test


def assert_no_leakage(train: pd.DataFrame, test: pd.DataFrame, T: pd.Period, panel: Panel) -> None:
    """Every label and input must be public at the fold's forecast date."""
    if len(train) and train["target_quarter"].max() > T:
        raise AssertionError(f"training label after origin {T}")
    if len(train) and train["origin"].max() >= T:
        raise AssertionError(f"training row with origin >= {T}")
    if not (test["origin"] == T).all():
        raise AssertionError("test rows from another origin")
    forecast_date = panel.cycle_date(T)
    for ticker, g in train.groupby("ticker"):
        avail = panel.available[ticker].reindex(g["target_quarter"])
        if (avail > forecast_date).any():
            raise AssertionError(f"{ticker}: a training label was filed after the forecast date {forecast_date.date()}")
    if "_macro_quarter" in test.columns and panel.macro is not None:
        mq = test["_macro_quarter"].dropna().unique()
        pub = panel.macro.set_index(panel.macro["quarter"].astype(str))["available_date"]
        if len(mq) and (pub.reindex(mq) > forecast_date).any():
            raise AssertionError("macro feature published after the forecast date")


def fit_fold(table: pd.DataFrame, T: pd.Period, cols: list[str]) -> tuple[GlobalLGBM, pd.DataFrame, pd.DataFrame]:
    train, test = split_fold(table, T)
    return GlobalLGBM(cols).fit(train), train, test


def run_backtest(panel: Panel, table: pd.DataFrame | None = None, origins=None) -> tuple[pd.DataFrame, dict]:
    table = build_table(panel) if table is None else table
    origins = origins or fold_origins(panel)
    variants = lgbm_variants(table)
    out, ets_failures = [], 0
    for T in origins:
        train, test = split_fold(table, T)
        assert_no_leakage(train, test, T, panel)
        lgbm_preds = {name: dict(zip(zip(test["ticker"], test["h"]), GlobalLGBM(cols).fit(train).predict(test)))
                      for name, cols in variants.items()}
        for ticker, y in panel.series.items():
            hist = y[y.index <= T]
            if (ticker, 1) not in lgbm_preds["lgbm"]:
                continue  # not enough history for this company at this origin
            scale = mase_scale(hist)
            e, ok = ets(hist, config.HORIZONS)
            ets_failures += not ok
            fc = {"naive": naive(hist, config.HORIZONS), "seasonal_naive": seasonal_naive(hist, config.HORIZONS), "ets": e}
            for name in variants:
                fc[name] = {h: lgbm_preds[name][(ticker, h)] for h in config.HORIZONS}
            for model, preds in fc.items():
                for h, f in preds.items():
                    t = T + h
                    out.append({"ticker": ticker, "origin": str(T), "h": h, "target_quarter": str(t),
                                "actual": float(y[t]), "model": model, "forecast": f, "mase_scale": scale})
        print(f"[backtest] fold origin {T}: train rows={len(train)}, test rows={len(test)}")
    return pd.DataFrame(out), {"ets_fallbacks": ets_failures, "origins": [str(o) for o in origins],
                               "variants": variants}


def fold_metrics(fc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, ticker, origin), g in fc.groupby(["model", "ticker", "origin"]):
        rows.append({"model": model, "ticker": ticker, "origin": origin,
                     "MAPE": mape(g["actual"], g["forecast"]), "sMAPE": smape(g["actual"], g["forecast"]),
                     "MASE": mase(g["actual"], g["forecast"], g["mase_scale"].iloc[0])})
    return pd.DataFrame(rows)


def company_metrics(fm: pd.DataFrame) -> pd.DataFrame:
    g = fm.groupby(["model", "ticker"])
    out = g[["MAPE", "sMAPE", "MASE"]].mean()
    out["MAPE_fold_std"] = g["MAPE"].std(ddof=1)
    out["MAPE_fold_var"] = g["MAPE"].var(ddof=1)
    return out.reset_index()


def summary_metrics(fm: pd.DataFrame, cm: pd.DataFrame) -> pd.DataFrame:
    s = fm.groupby("model").agg(MAPE=("MAPE", "mean"), sMAPE=("sMAPE", "mean"), MASE=("MASE", "mean"),
                                MASE_median=("MASE", "median"), cells=("MASE", "size"))
    s["stability_fold_MAPE_std"] = cm.groupby("model")["MAPE_fold_std"].mean()
    s["stability_fold_MAPE_var"] = cm.groupby("model")["MAPE_fold_var"].mean()
    best = cm.loc[cm.groupby("ticker")["MASE"].idxmin()]
    s["companies_best_MASE"] = best["model"].value_counts().reindex(s.index).fillna(0).astype(int)
    order = [m for m in MODEL_LABELS if m in s.index]
    return s.loc[order].reset_index()


def horizon_metrics(fc: pd.DataFrame) -> pd.DataFrame:
    fc = fc.assign(ape=(fc["forecast"] - fc["actual"]).abs() / fc["actual"] * 100)
    return fc.pivot_table(index="model", columns="h", values="ape", aggfunc="mean").add_prefix("MAPE_h")


def bootstrap_table(fm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    wide = {m: fm[fm["model"] == m].set_index(["ticker", "origin"]).sort_index() for m in fm["model"].unique()}
    for ml in [m for m in ("lgbm", "lgbm_macro") if m in wide]:
        for other in [m for m in MODEL_LABELS if m in wide and m != ml]:
            a, b = wide[ml], wide[other].reindex(wide[ml].index)
            for metric in ("MASE", "MAPE"):
                for kind, clusters in (("cells", None), ("companies", a.index.get_level_values("ticker").to_numpy())):
                    r = bootstrap_mean_diff(a[metric].to_numpy(), b[metric].to_numpy(), n=config.BOOTSTRAP_RESAMPLES,
                                            seed=config.BOOTSTRAP_SEED, clusters=clusters)
                    rows.append({"model": ml, "vs": other, "metric": metric, "resample": kind, **r})
    return pd.DataFrame(rows)
