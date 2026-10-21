"""Turn SEC companyfacts JSON into a clean quarterly revenue series.

Key facts about the source that drive this code:
* One fact = (tag, unit, start, end, value, filing). The same period appears in
  several filings (e.g. as a prior-year comparative), so we keep the value
  from the FIRST filing (what was known at the time, used for forecasting)
  and the LATEST filing (to measure restatements).
* 10-Qs report 3-month values and often year-to-date values; 10-Ks report the
  full year only. Fiscal Q4 is therefore usually derived as
  annual - 9-month YTD. We do this generally: two cumulative facts with the
  same start date whose end dates differ by one quarter give that quarter.
* Fiscal quarters are mapped to the nearest calendar quarter by end date so
  that companies with different fiscal years share one time axis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

FACT_COLUMNS = ["tag", "unit", "start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"]


def facts_to_frame(companyfacts: dict, tags: list[str], taxonomy: str = "us-gaap") -> pd.DataFrame:
    """Flatten the selected tags of a companyfacts document into one row per fact."""
    rows = []
    tax = companyfacts.get("facts", {}).get(taxonomy, {})
    for tag in tags:
        for unit, facts in tax.get(tag, {}).get("units", {}).items():
            for f in facts:
                rows.append({
                    "tag": tag, "unit": unit, "start": f.get("start"), "end": f.get("end"),
                    "val": f.get("val"), "accn": f.get("accn"), "fy": f.get("fy"), "fp": f.get("fp"),
                    "form": f.get("form"), "filed": f.get("filed"), "frame": f.get("frame"),
                })
    df = pd.DataFrame(rows, columns=FACT_COLUMNS)
    for col in ("start", "end", "filed"):
        df[col] = pd.to_datetime(df[col])
    df["val"] = pd.to_numeric(df["val"], errors="coerce").astype(float)
    df["days"] = (df["end"] - df["start"]).dt.days
    return df


def calendar_quarter(end: pd.Timestamp) -> pd.Period:
    """Nearest calendar quarter to a fiscal period end date.

    Shifting by +45 days and stepping back one quarter maps e.g. Apr 30 -> Q1,
    Jun 28 -> Q2, Jan 31 -> previous Q4.
    """
    return (pd.Timestamp(end) + pd.Timedelta(days=45)).to_period("Q") - 1


def _is_quarter(days) -> bool:
    return config.QUARTER_DAYS[0] <= days <= config.QUARTER_DAYS[1]


def period_vintages(facts: pd.DataFrame) -> pd.DataFrame:
    """One row per (tag, start, end) with first- and latest-reported values."""
    f = facts.sort_values(["filed", "accn"])
    g = f.groupby(["tag", "start", "end"], sort=False)
    out = g.agg(
        first_val=("val", "first"), first_filed=("filed", "first"), first_form=("form", "first"),
        latest_val=("val", "last"), latest_filed=("filed", "last"),
        n_filings=("accn", "nunique"), n_values=("val", "nunique"),
    ).reset_index()
    out["days"] = (out["end"] - out["start"]).dt.days
    return out


def _value_as_of(facts: pd.DataFrame, tag, start, end, as_of) -> float | None:
    """Latest value of a period known on or before `as_of` (point-in-time)."""
    m = facts[(facts["tag"] == tag) & (facts["start"] == start) & (facts["end"] == end) & (facts["filed"] <= as_of)]
    if m.empty:
        return None
    return float(m.sort_values(["filed", "accn"])["val"].iloc[-1])


def quarter_candidates(facts: pd.DataFrame) -> pd.DataFrame:
    """All direct and derived quarterly observations, per tag."""
    vint = period_vintages(facts)
    cols = ["tag", "start", "end", "value", "available_date", "latest_value", "latest_filed",
            "source", "n_filings", "n_values"]
    direct = vint[vint["days"].apply(_is_quarter)].rename(columns={
        "first_val": "value", "first_filed": "available_date", "latest_val": "latest_value"})
    direct = direct.assign(source="direct")[cols]

    derived_rows = []
    cumulative = vint[vint["days"] >= config.QUARTER_DAYS[0]]
    for (tag, start), grp in cumulative.groupby(["tag", "start"]):
        grp = grp.sort_values("end").reset_index(drop=True)
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp.loc[i], grp.loc[j]
                gap = (b["end"] - a["end"]).days
                if not _is_quarter(gap):
                    continue
                # Point-in-time: use A as known when B was first filed.
                a_val = _value_as_of(facts, tag, a["start"], a["end"], b["first_filed"])
                if a_val is None:
                    continue
                derived_rows.append({
                    "tag": tag, "start": a["end"] + pd.Timedelta(days=1), "end": b["end"],
                    "value": b["first_val"] - a_val, "available_date": b["first_filed"],
                    "latest_value": b["latest_val"] - a["latest_val"], "latest_filed": b["latest_filed"],
                    "source": "derived", "n_filings": int(b["n_filings"]), "n_values": int(b["n_values"]),
                })
    derived = pd.DataFrame(derived_rows, columns=cols)
    cand = pd.concat([direct, derived], ignore_index=True)
    for col in ("start", "end", "available_date", "latest_filed"):
        cand[col] = pd.to_datetime(cand[col])
    cand["quarter"] = cand["end"].apply(calendar_quarter)
    cand["days"] = (cand["end"] - cand["start"]).dt.days
    return cand


def build_quarterly(facts: pd.DataFrame, tags: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Select one revenue value per calendar quarter and collect diagnostics.

    Preference: direct over derived, then tag priority, then period length
    closest to 91 days, then earliest filing.
    """
    tags = tags or config.REVENUE_TAGS
    diag: dict = {}
    diag["non_usd_units"] = sorted({f"{t}:{u}" for t, u in facts[facts["unit"] != "USD"][["tag", "unit"]].itertuples(index=False)})
    usd = facts[(facts["unit"] == "USD") & facts["form"].isin(config.ALLOWED_FORMS) & facts["start"].notna()].copy()
    diag["excluded_forms"] = facts.loc[~facts["form"].isin(config.ALLOWED_FORMS), "form"].value_counts().to_dict()
    diag["tags_present"] = sorted(usd["tag"].unique().tolist())

    vint = period_vintages(usd)
    diag["n_periods"] = int(len(vint))
    diag["n_periods_multi_filing"] = int((vint["n_filings"] > 1).sum())
    diag["n_periods_conflicting_values"] = int((vint["n_values"] > 1).sum())

    cand = quarter_candidates(usd)
    if cand.empty:
        return pd.DataFrame(), diag
    cand["tag_rank"] = cand["tag"].map({t: i for i, t in enumerate(tags)})
    cand["src_rank"] = (cand["source"] == "derived").astype(int)
    cand["len_dev"] = (cand["days"] - 91).abs()

    # Tag disagreement: same quarter, different tags, first-reported values differ > 1%.
    disagreements = []
    for q, grp in cand[cand["source"] == "direct"].groupby("quarter"):
        per_tag = grp.groupby("tag")["value"].first()
        if len(per_tag) > 1 and per_tag.max() > 0 and (per_tag.max() / per_tag.min() - 1) > 0.01:
            disagreements.append({"quarter": str(q), **{k: float(v) for k, v in per_tag.items()}})
    diag["tag_disagreements"] = disagreements

    # Calendar-mapping collisions: two different period END dates in one quarter.
    ends = cand.groupby("quarter")["end"].nunique()
    diag["calendar_collisions"] = [str(q) for q in ends[ends > 1].index]

    best = (cand.sort_values(["quarter", "src_rank", "tag_rank", "len_dev", "available_date"])
                .groupby("quarter", as_index=False).first())
    best["restatement_pct"] = np.where(best["value"] != 0, best["latest_value"] / best["value"] - 1, np.nan)
    best["restated"] = best["restatement_pct"].abs() > 0.001
    best = best[best["quarter"] >= pd.Period(config.SERIES_START, "Q")]
    best = best.sort_values("quarter").reset_index(drop=True)
    keep = ["quarter", "start", "end", "value", "available_date", "latest_value", "latest_filed",
            "restatement_pct", "restated", "source", "tag", "n_filings", "n_values"]
    return best[keep], diag


def missing_quarters(series: pd.DataFrame) -> list[pd.Period]:
    if series.empty:
        return []
    full = pd.period_range(series["quarter"].min(), series["quarter"].max(), freq="Q")
    return [q for q in full if q not in set(series["quarter"])]


def contiguous_tail(series: pd.DataFrame) -> pd.DataFrame:
    """Longest run of consecutive quarters that ends at the latest quarter."""
    if series.empty:
        return series
    s = series.sort_values("quarter").reset_index(drop=True)
    ords = s["quarter"].apply(lambda p: p.ordinal).to_numpy()
    start = len(s) - 1
    while start > 0 and ords[start] - ords[start - 1] == 1:
        start -= 1
    return s.iloc[start:].reset_index(drop=True)


def concept_coverage(companyfacts: dict, concept: str) -> dict:
    """How many quarters a candidate driver concept covers (quarterly or instant)."""
    tax = companyfacts.get("facts", {}).get("us-gaap", {})
    if concept not in tax:
        return {"present": False, "n_quarters": 0, "first": None, "last": None, "kind": None}
    f = facts_to_frame(companyfacts, [concept])
    f = f[f["form"].isin(config.ALLOWED_FORMS)]
    instant = f["start"].isna()
    if instant.mean() > 0.5:
        ends, kind = f.loc[instant, "end"], "instant"
    else:
        ends, kind = f.loc[~instant & f["days"].apply(_is_quarter), "end"], "quarterly"
        if ends.empty:
            ends, kind = f.loc[~instant, "end"], "ytd/annual only"
    qs = sorted({calendar_quarter(e) for e in ends.dropna()})
    return {"present": True, "n_quarters": len(qs), "first": str(qs[0]) if qs else None,
            "last": str(qs[-1]) if qs else None, "kind": kind}
