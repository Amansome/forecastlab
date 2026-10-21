"""Write reports/results.md from the backtest outputs (no hand-edited numbers)."""
from __future__ import annotations

import pandas as pd

from . import backtest, config


def _md(df: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def write_results(summary, company, horizon, boot, meta, panel) -> str:
    s = summary.copy()
    s["model"] = s["model"].map(backtest.MODEL_LABELS)
    s = s.rename(columns={"stability_fold_MAPE_std": "fold MAPE std", "stability_fold_MAPE_var": "fold MAPE var",
                          "companies_best_MASE": "# companies best", "MASE_median": "MASE median"})
    s = s[["model", "MAPE", "sMAPE", "MASE", "MASE median", "fold MAPE std", "fold MAPE var", "# companies best", "cells"]]
    mase_p = company.pivot(index="ticker", columns="model", values="MASE")
    mase_p = mase_p[[m for m in backtest.MODEL_LABELS if m in mase_p.columns]].reset_index()
    mape_p = company.pivot(index="ticker", columns="model", values="MAPE")
    mape_p = mape_p[[m for m in backtest.MODEL_LABELS if m in mape_p.columns]].reset_index()
    stab_p = company.pivot(index="ticker", columns="model", values="MAPE_fold_std")
    stab_p = stab_p[[m for m in backtest.MODEL_LABELS if m in stab_p.columns]].reset_index()
    hz = horizon.reset_index()
    b = boot[boot["metric"] == "MASE"].copy()
    b["significant (CI excludes 0)"] = ((b["ci_low"] > 0) | (b["ci_high"] < 0)).map({True: "yes", False: "no"})
    b = b[["model", "vs", "resample", "mean_diff", "ci_low", "ci_high", "significant (CI excludes 0)"]]
    o = meta["origins"]
    text = "\n".join([
        "# Backtest results", "",
        f"Rolling-origin, expanding window. {len(o)} fold origins ({o[0]} to {o[-1]}), horizons h=1..4, "
        f"{len(panel.series)} companies. Metrics are computed per (company, fold) over the 4 horizons, then averaged. "
        f"Common data end: {panel.end}. ETS fell back to seasonal naive {meta['ets_fallbacks']} time(s).", "",
        "## Aggregate", "", _md(s, "{:.3f}"), "",
        "Stability = per company, the std (and variance) of fold-level MAPE across folds, averaged over companies. Lower is more stable.", "",
        "## MASE by company", "", _md(mase_p, "{:.3f}"), "",
        "## MAPE % by company", "", _md(mape_p), "",
        "## Fold-to-fold std of MAPE by company", "", _md(stab_p), "",
        "## MAPE % by horizon", "", _md(hz), "",
        "## Bootstrap 95% CIs: mean MASE difference (LightGBM minus comparator; negative = LightGBM better)", "",
        "`cells` resamples (company, fold) pairs; `companies` resamples whole companies (respects correlation "
        "between overlapping folds of the same company, so it is the more conservative interval).", "",
        _md(b, "{:+.3f}"), "",
    ])
    (config.REPORTS / "results.md").write_text(text + "\n")
    return text
