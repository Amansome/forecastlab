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


def equivalent_tag_groups(vint: pd.DataFrame, tol: float = 0.005) -> dict[str, str]:
    """Group tags that report the same number for the same periods.

    Two tags are equivalent if they overlap on >= 2 periods with a median
    relative gap below `tol`. Only equivalent tags may be combined when a
    quarter is derived by subtraction (e.g. annual `Revenues` minus 9M
    `RevenueFromContract...`), so a component tag is never mixed with a total.
    """
    tags = sorted(vint["tag"].unique())
    parent = {t: t for t in tags}

    def find(t):
        while parent[t] != t:
            t = parent[t]
        return t
    piv = vint.pivot_table(index=["start", "end"], columns="tag", values="first_val", aggfunc="first")
    for i, a in enumerate(tags):
        for b in tags[i + 1:]:
            both = piv[[a, b]].dropna()
            if len(both) >= 2 and (both[b] / both[a] - 1).abs().median() < tol:
                parent[find(b)] = find(a)
    return {t: find(t) for t in tags}


def quarter_candidates(facts: pd.DataFrame) -> pd.DataFrame:
    """All direct and derived quarterly observations, per tag."""
    vint = period_vintages(facts)
    groups = equivalent_tag_groups(vint)
    cols = ["tag", "start", "end", "value", "available_date", "latest_value", "latest_filed",
            "source", "n_filings", "n_values"]
    direct = vint[vint["days"].apply(_is_quarter)].rename(columns={
        "first_val": "value", "first_filed": "available_date", "latest_val": "latest_value"})
    direct = direct.assign(source="direct")[cols]

    derived_rows = []
    cumulative = vint[vint["days"] >= config.QUARTER_DAYS[0]].assign(group=lambda d: d["tag"].map(groups))
    for (_, start), grp in cumulative.groupby(["group", "start"]):
        grp = grp.sort_values("end").reset_index(drop=True)
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp.loc[i], grp.loc[j]
                gap = (b["end"] - a["end"]).days
                if not _is_quarter(gap):
                    continue
                # Point-in-time: use A as known when B was first filed.
                a_val = _value_as_of(facts, a["tag"], a["start"], a["end"], b["first_filed"])
                if a_val is None:
                    continue
                # Plausibility guard against mis-tagged facts: the derived quarter
                # must be positive and within 0.2x-5x of A's average quarter.
                value = b["first_val"] - a_val
                avg_q = a_val / max(1, round(a["days"] / 91))
                if not (0.2 * avg_q <= value <= 5 * avg_q):
                    continue
                derived_rows.append({
                    "tag": b["tag"], "start": a["end"] + pd.Timedelta(days=1), "end": b["end"],
                    "value": value, "available_date": b["first_filed"],
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

    Value used: the first-reported one (earliest filing across tags). The
    latest value of the highest-priority tag is kept to measure restatements.
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

    # Point-in-time value: the EARLIEST filing of any revenue tag for the quarter
    # (what the market first saw). Same-day ties go to directly reported over
    # derived (subtraction can amplify a mis-tagged fact), then tag priority.
    # Ranking tag priority first would pick prior-year comparatives filed a
    # year late after a tag switch.
    best = (cand.sort_values(["quarter", "available_date", "src_rank", "tag_rank", "len_dev"])
                .groupby("quarter", as_index=False).first())
    # "Latest" = the preferred definition as known today, to measure restatements
    # and definition changes (e.g. ASC 606) against the first-reported value.
    pref = (cand.sort_values(["quarter", "tag_rank", "src_rank", "len_dev"])
                .groupby("quarter")[["latest_value", "latest_filed", "tag"]].first())
    best = best.drop(columns=["latest_value", "latest_filed"]).join(
        pref.rename(columns={"tag": "latest_tag"}), on="quarter")
    # Level-break check wherever the chosen tag changes: compare the two tags on
    # quarters where both report (a component tag such as product-only sales
    # would show up as a large gap).
    by_tag = (cand.sort_values(["src_rank", "available_date"]).groupby(["quarter", "tag"])["value"].first().unstack())
    switches = []
    chosen = best.sort_values("quarter")[["quarter", "tag"]].to_numpy()
    for (q0, t0), (q1, t1) in zip(chosen[:-1], chosen[1:]):
        if t0 != t1:
            both = by_tag[[t0, t1]].dropna() if {t0, t1} <= set(by_tag.columns) else pd.DataFrame()
            ratio = (both[t1] / both[t0] - 1) if len(both) else pd.Series(dtype=float)
            switches.append({"quarter": str(q1), "from": t0, "to": t1, "n_overlap": int(len(both)),
                             "median_diff_pct": round(float(ratio.median()) * 100, 2) if len(ratio) else None})
    diag["tag_switches"] = switches

    best["restatement_pct"] = np.where(best["value"] != 0, best["latest_value"] / best["value"] - 1, np.nan)
    best["restated"] = best["restatement_pct"].abs() > 0.001
    best = best[best["quarter"] >= pd.Period(config.SERIES_START, "Q")]
    best = best.sort_values("quarter").reset_index(drop=True)
    keep = ["quarter", "start", "end", "value", "available_date", "latest_value", "latest_filed", "latest_tag",
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
