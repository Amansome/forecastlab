"""Forecast drift monitoring: compare stored forecasts to actuals as they arrive.

Rule per company: flag DRIFT when the absolute % error exceeds BOTH an
absolute threshold (8%) and 2x that company's backtest MAPE for the model,
so a normally noisy company is not flagged for normal noise.
Portfolio recommendation:
* RETRAIN if >= 30% of checked companies drift, or errors share one sign for
  >= 80% of companies with mean |error| above half the absolute threshold
  (systematic bias, e.g. a macro shock the model has not seen);
* REVIEW if any company drifts (look at that company's filing first);
* OK otherwise.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def load_actuals(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.DATA_PROCESSED / "quarterly_revenue.csv")
    return df[["ticker", "quarter", "revenue", "available_date"]].rename(columns={"quarter": "target_quarter"})


def check_drift(forecasts: pd.DataFrame, actuals: pd.DataFrame, backtest_mape: pd.Series, model: str) -> tuple[pd.DataFrame, dict]:
    fc = forecasts[forecasts["model"] == model]
    m = fc.merge(actuals, on=["ticker", "target_quarter"], how="inner")
    m = m[m["target_quarter"].apply(lambda q: pd.Period(q, "Q")) > m["origin"].apply(lambda q: pd.Period(q, "Q"))]
    if m.empty:
        return m, {"status": "NO NEW ACTUALS", "n_checked": 0}
    m = m.copy()
    m["error_pct"] = (m["forecast"] - m["revenue"]) / m["revenue"] * 100
    m["ape_pct"] = m["error_pct"].abs()
    m["backtest_mape_pct"] = m["ticker"].map(backtest_mape)
    m["threshold_pct"] = np.maximum(config.DRIFT_ABS_APE * 100, config.DRIFT_REL_MULT * m["backtest_mape_pct"].fillna(0))
    m["drift"] = m["ape_pct"] > m["threshold_pct"]
    m["action"] = np.where(m["drift"], "REVIEW", "OK")

    # Use the earliest new quarter per company for the portfolio decision.
    first = m.sort_values("h").groupby("ticker").first()
    share = first["drift"].mean()
    signs = np.sign(first["error_pct"])
    same_sign = max((signs > 0).mean(), (signs < 0).mean())
    bias = first["error_pct"].mean()
    if share >= config.RETRAIN_SHARE:
        status, why = "RETRAIN", f"{share:.0%} of companies breached their threshold (>= {config.RETRAIN_SHARE:.0%})"
    elif same_sign >= 0.8 and len(first) >= 3 and abs(bias) > config.DRIFT_ABS_APE * 50:
        status, why = "RETRAIN", f"systematic bias: {same_sign:.0%} of errors share a sign, mean error {bias:+.1f}%"
    elif first["drift"].any():
        status, why = "REVIEW", "drift at: " + ", ".join(first.index[first["drift"]])
    else:
        status, why = "OK", "all errors within thresholds"
    return m, {"status": status, "reason": why, "n_checked": int(len(first)), "share_drifting": float(share),
               "mean_error_pct": float(bias), "same_sign_share": float(same_sign)}


def run_monitor(forecast_file: Path, model: str = "lgbm", actuals_path: Path | None = None) -> dict:
    forecasts = pd.read_csv(forecast_file)
    actuals = load_actuals(actuals_path)
    cm = pd.read_csv(config.REPORTS / "metrics_by_company.csv")
    bt = cm[cm["model"] == model].set_index("ticker")["MAPE"]
    checked, summary = check_drift(forecasts, actuals, bt, model)
    origin = forecasts["origin"].iloc[0]
    stem = f"monitoring_origin_{origin}_{model}"
    checked.to_csv(config.REPORTS / f"{stem}.csv", index=False)
    L = [f"# Drift check: {model} forecasts made at origin {origin}", "",
         f"**Recommendation: {summary['status']}** - {summary.get('reason', '')}", "",
         f"Thresholds: APE > max({config.DRIFT_ABS_APE:.0%}, {config.DRIFT_REL_MULT:g} x company backtest MAPE).", ""]
    if not checked.empty:
        L += ["| Company | Quarter | h | Actual ($M) | Forecast ($M) | Error % | Threshold % | Action |",
              "|---|---|---|---|---|---|---|---|"]
        for r in checked.sort_values(["ticker", "h"]).itertuples():
            L.append(f"| {r.ticker} | {r.target_quarter} | {r.h} | {r.revenue/1e6:,.0f} | {r.forecast/1e6:,.0f} | "
                     f"{r.error_pct:+.1f} | {r.threshold_pct:.1f} | {r.action} |")
    (config.REPORTS / f"{stem}.md").write_text("\n".join(L) + "\n")
    print(f"[monitor] origin {origin} {model}: {summary['status']} ({summary.get('n_checked', 0)} companies checked)")
    return summary
