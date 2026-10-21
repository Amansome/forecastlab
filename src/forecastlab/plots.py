"""Figures for the README."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import backtest, config  # noqa: E402

COLORS = {"naive": "#9e9e9e", "seasonal_naive": "#e08214", "ets": "#2c7fb8", "lgbm": "#1a9850", "lgbm_macro": "#7b3294"}


def _grid(n):
    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4 * ((n + 1) // 2), 6.5), sharex=False)
    return fig, axes.ravel()


def revenue_overview(panel) -> None:
    fig, axes = _grid(len(panel.series))
    for ax, (t, y) in zip(axes, panel.series.items()):
        ax.plot(y.index.to_timestamp(), y.values / 1e9, color="#333")
        ax.set_title(t, fontsize=10)
        ax.tick_params(labelsize=7)
    fig.suptitle("Quarterly revenue, first-reported (USD bn), contiguous modelling window")
    fig.tight_layout()
    fig.savefig(config.FIGURES / "revenue_overview.png", dpi=110)
    plt.close(fig)


def backtest_h1(panel, fc: pd.DataFrame, models=("seasonal_naive", "ets", "lgbm")) -> None:
    fig, axes = _grid(len(panel.series))
    h1 = fc[fc["h"] == 1]
    first = pd.Period(h1["target_quarter"].min(), "Q") - 8
    for ax, (t, y) in zip(axes, panel.series.items()):
        yy = y[y.index >= first]
        ax.plot(yy.index.to_timestamp(), yy.values / 1e9, color="black", lw=1.5, label="actual")
        for m in models:
            g = h1[(h1["ticker"] == t) & (h1["model"] == m)]
            ax.plot(pd.PeriodIndex(g["target_quarter"], freq="Q").to_timestamp(), g["forecast"] / 1e9,
                    color=COLORS[m], lw=1, marker=".", label=backtest.MODEL_LABELS[m])
        ax.set_title(t, fontsize=10)
        ax.tick_params(labelsize=7)
    axes[0].legend(fontsize=6)
    fig.suptitle("Backtest: one-quarter-ahead forecasts vs actual (USD bn)")
    fig.tight_layout()
    fig.savefig(config.FIGURES / "backtest_h1.png", dpi=110)
    plt.close(fig)


def mase_by_company(cm: pd.DataFrame) -> None:
    p = cm.pivot(index="ticker", columns="model", values="MASE")
    p = p[[m for m in backtest.MODEL_LABELS if m in p.columns]]
    ax = p.plot.bar(figsize=(11, 4), color=[COLORS[m] for m in p.columns], width=0.8)
    ax.axhline(1.0, color="black", lw=0.8, ls="--")
    ax.set_ylabel("MASE (lower is better)")
    ax.set_title("MASE by company (mean over folds, h=1..4). Dashed line = in-sample seasonal naive error")
    ax.legend([backtest.MODEL_LABELS[m] for m in p.columns], fontsize=7)
    plt.tight_layout()
    plt.savefig(config.FIGURES / "mase_by_company.png", dpi=110)
    plt.close()


def mape_by_fold(fm: pd.DataFrame) -> None:
    p = fm.groupby(["origin", "model"])["MAPE"].mean().unstack()
    p = p[[m for m in backtest.MODEL_LABELS if m in p.columns]]
    ax = p.plot(figsize=(10, 4), color=[COLORS[m] for m in p.columns], marker="o")
    ax.set_ylabel("MAPE % (mean over companies)")
    ax.set_xlabel("fold origin")
    ax.set_title("Error by fold (stability across origins)")
    ax.legend([backtest.MODEL_LABELS[m] for m in p.columns], fontsize=7)
    plt.tight_layout()
    plt.savefig(config.FIGURES / "mape_by_fold.png", dpi=110)
    plt.close()
