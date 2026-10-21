"""Load the processed panel into per-company series for modelling."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import config


@dataclass
class Panel:
    series: dict[str, pd.Series]          # ticker -> revenue (USD), contiguous PeriodIndex
    available: dict[str, pd.Series]       # ticker -> first filing date per quarter
    macro: pd.DataFrame | None            # quarterly macro features with available_date

    @property
    def end(self) -> pd.Period:
        """Last quarter that every company has reported (the common forecast origin)."""
        return min(s.index.max() for s in self.series.values())

    def cycle_date(self, q: pd.Period) -> pd.Timestamp:
        """When a forecast run at origin q can happen: after all companies filed quarter q."""
        dates = [a[q] for a in self.available.values() if q in a.index]
        return max(dates)


def _contiguous(s: pd.Series) -> pd.Series:
    s = s.sort_index()
    ords = [p.ordinal for p in s.index]
    i = len(ords) - 1
    while i > 0 and ords[i] - ords[i - 1] == 1:
        i -= 1
    return s.iloc[i:]


def panel_from_frame(df: pd.DataFrame, macro: pd.DataFrame | None = None) -> Panel:
    df = df.copy()
    df["quarter"] = pd.PeriodIndex(df["quarter"], freq="Q")
    df["available_date"] = pd.to_datetime(df["available_date"])
    series, avail = {}, {}
    for t, g in df.groupby("ticker", sort=False):
        s = _contiguous(g.set_index("quarter")["revenue"].astype(float))
        series[t] = s
        avail[t] = g.set_index("quarter")["available_date"].reindex(s.index)
    if macro is not None:
        macro = macro.copy()
        macro["quarter"] = pd.PeriodIndex(macro["quarter"], freq="Q")
        macro["available_date"] = pd.to_datetime(macro["available_date"])
        macro = macro.sort_values("quarter").reset_index(drop=True)
    return Panel(series, avail, macro)


def load_panel(use_macro: bool = True) -> Panel:
    df = pd.read_csv(config.DATA_PROCESSED / "quarterly_revenue.csv")
    df = df[df["ticker"].isin(config.TICKERS)]
    macro = None
    path = config.DATA_PROCESSED / "macro_quarterly.csv"
    if use_macro and path.exists():
        macro = pd.read_csv(path)
    return panel_from_frame(df, macro)
