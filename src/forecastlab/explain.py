"""SHAP explanations computed out-of-sample: each fold's model explains its own test rows."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402

from . import backtest, config  # noqa: E402

FEATURE_DESCRIPTIONS = {
    "h": "forecast horizon in quarters (1-4)",
    "tq_1": "target quarter is calendar Q1", "tq_2": "target quarter is calendar Q2",
    "tq_3": "target quarter is calendar Q3", "tq_4": "target quarter is calendar Q4",
    "yoy_0": "YoY log growth of the latest reported quarter",
    "yoy_1": "YoY log growth one quarter earlier", "yoy_2": "YoY log growth two quarters earlier",
    "yoy_3": "YoY log growth three quarters earlier",
    "yoy_mean4": "mean YoY growth over the last 4 quarters (rolling mean)",
    "yoy_mean8": "mean YoY growth over the last 8 quarters (rolling mean)",
    "yoy_std8": "volatility of YoY growth over the last 8 quarters",
    "yoy_accel": "latest YoY growth minus YoY growth a year earlier (acceleration)",
    "qoq_0": "QoQ log change of the latest quarter",
    "base_yoy": "YoY growth the base quarter (t-4) itself had",
    "base_vs_trailing4": "base quarter vs trailing-4-quarter average (seasonal position)",
    "level_vs_ma4": "latest quarter vs trailing-4-quarter average",
    "macro_retail_yoy": "US retail sales YoY growth, latest published quarter",
    "macro_cpi_yoy": "US CPI YoY inflation, latest published quarter",
    "macro_retail_yoy_chg": "change in retail sales YoY growth vs prior quarter",
}


def oos_shap(panel, table: pd.DataFrame, variant: str, cols: list[str], origins) -> pd.DataFrame:
    frames = []
    for T in origins:
        model, _, test = backtest.fit_fold(table, T, cols)
        sv = shap.TreeExplainer(model.model).shap_values(test[cols])
        f = pd.DataFrame(sv, columns=cols, index=test.index).add_prefix("shap_")
        frames.append(pd.concat([test[["ticker", "origin", "target_quarter"] + cols], f], axis=1))  # "h" is a feature
    out = pd.concat(frames)
    out["origin"] = out["origin"].astype(str)
    out["target_quarter"] = out["target_quarter"].astype(str)
    return out


def run_explain(panel, table, forecasts: pd.DataFrame, company: pd.DataFrame, meta: dict) -> str:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    origins = [pd.Period(o, "Q") for o in meta["origins"]]
    md = ["# Explainability (SHAP, out-of-sample)", "",
          "SHAP values are computed by each fold's model on that fold's test rows only, so they describe "
          "what the model used when it made real backtest forecasts. Units are YoY log growth: a mean |SHAP| "
          "of 0.01 moves the forecast by roughly 1% of revenue.", ""]
    for variant, cols in meta["variants"].items():
        sh = oos_shap(panel, table, variant, cols, origins)
        sh.to_csv(config.REPORTS / f"shap_values_{variant}.csv", index=False)
        imp = sh[[f"shap_{c}" for c in cols]].abs().mean().rename(lambda c: c[5:]).sort_values(ascending=False)
        plt.figure()
        shap.summary_plot(sh[[f"shap_{c}" for c in cols]].to_numpy(), sh[cols], feature_names=cols, show=False, max_display=15)
        plt.title(f"SHAP summary - {backtest.MODEL_LABELS[variant]} (out-of-sample)")
        plt.tight_layout()
        plt.savefig(config.FIGURES / f"shap_summary_{variant}.png", dpi=130)
        plt.close("all")

        md += [f"## {backtest.MODEL_LABELS[variant]}", "", f"{len(sh)} out-of-sample rows ({len(origins)} folds).", "",
               "| Rank | Feature | Mean abs SHAP | Meaning |", "|---|---|---|---|"]
        md += [f"| {i+1} | `{f}` | {v:.4f} | {FEATURE_DESCRIPTIONS.get(f, '')} |" for i, (f, v) in enumerate(imp.items())]
        md += ["", f"![SHAP summary](figures/shap_summary_{variant}.png)", ""]

        fc = forecasts[forecasts["model"] == variant].copy()
        fc["ape_pct"] = (fc["forecast"] - fc["actual"]).abs() / fc["actual"] * 100
        worst = fc.sort_values("ape_pct", ascending=False).head(8).merge(sh, on=["ticker", "origin", "h", "target_quarter"])
        md += ["### Largest errors and what drove them", "",
               "| Company | Target | h | Actual ($M) | Forecast ($M) | APE % | Top 3 SHAP contributions |", "|---|---|---|---|---|---|---|"]
        for r in worst.itertuples():
            contrib = pd.Series({c: getattr(r, f"shap_{c}") for c in cols})
            top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(3)
            md.append(f"| {r.ticker} | {r.target_quarter} | {r.h} | {r.actual/1e6:,.0f} | {r.forecast/1e6:,.0f} | "
                      f"{r.ape_pct:.1f} | "
                      + ", ".join(f"{k} {v:+.3f}" for k, v in top.items()) + " |")
        cm = company.pivot(index="ticker", columns="model", values="MASE")
        base = [m for m in backtest.BASELINES if m in cm.columns]
        best_base = cm[base].min(axis=1)
        loses = cm[cm[variant] > best_base]
        md += ["", "### Companies where it does not beat the best baseline (MASE)", ""]
        if loses.empty:
            md.append("None: it has the lowest MASE for every company.")
        else:
            md += ["| Company | Model MASE | Best baseline | Baseline MASE |", "|---|---|---|---|"]
            for t, r in loses.iterrows():
                md.append(f"| {t} | {r[variant]:.3f} | {r[base].astype(float).idxmin()} | {best_base[t]:.3f} |")
        md.append("")
    text = "\n".join(md) + "\n"
    (config.REPORTS / "explainability.md").write_text(text)
    return text
