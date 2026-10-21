"""Data quality checks, processed panel, and per-company data readiness reports."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config, edgar, ingest

SECTOR_DRIVER_NOTES = {
    "Retail": "US retail sales (FRED RSAFS) is a direct demand proxy; inventory build is a lead indicator of expected sales.",
    "Retail / cloud": "Retail sales proxies the online-store business; cloud (AWS) growth is not visible in companyfacts because segment data is excluded.",
    "Software": "Contract liabilities (deferred revenue) are a known leading indicator for subscription revenue.",
    "Internet / advertising": "Ad spend tracks nominal consumer activity; retail sales and CPI are weak proxies at best.",
    "Technology hardware": "Product launch cycles (e.g. a September launch) drive Q4/Q1 peaks; no launch calendar is in this data.",
    "Consumer staples": "Pricing drives recent growth, so CPI is a plausible driver; volume data is not in XBRL facts.",
    "Consumer discretionary": "Inventory levels and retail sales are plausible drivers; FX exposure is material but not modelled.",
}


def _fiscal_year_end(facts: pd.DataFrame) -> str:
    annual = facts[facts["days"].between(*config.ANNUAL_DAYS)]
    if annual.empty:
        return "unknown"
    return annual["end"].dt.strftime("%b").mode().iloc[0]


def analyse_company(company: config.Company, companyfacts: dict) -> tuple[pd.DataFrame, dict]:
    facts = edgar.facts_to_frame(companyfacts, config.REVENUE_TAGS)
    series, diag = edgar.build_quarterly(facts)
    q = {"ticker": company.ticker, "entity_name": companyfacts.get("entityName"), **diag}
    if series.empty:
        q.update(n_quarters=0, verdict="NOT READY")
        return series, q

    gaps = edgar.missing_quarters(series)
    tail = edgar.contiguous_tail(series)
    s = series.set_index("quarter")["value"]
    logv = np.log(s.where(s > 0))
    # Period arithmetic (not .shift) so gaps in the series do not misalign lags.
    qoq = pd.Series({p: logv[p] - logv.get(p - 1, np.nan) for p in logv.index})
    yoy = pd.Series({p: logv[p] - logv.get(p - 4, np.nan) for p in logv.index})
    restated = series[series["restated"]]
    material = series[series["restatement_pct"].abs() > 0.01]

    q.update({
        "fiscal_year_end": _fiscal_year_end(facts[facts["unit"] == "USD"]),
        "first_quarter": str(series["quarter"].min()), "last_quarter": str(series["quarter"].max()),
        "n_quarters": int(len(series)),
        "missing_quarters": [str(p) for p in gaps],
        "contiguous_start": str(tail["quarter"].min()), "n_contiguous": int(len(tail)),
        "n_derived": int((series["source"] == "derived").sum()),
        "n_restated": int(len(restated)), "n_material_restatements": int(len(material)),
        "max_abs_restatement_pct": float(series["restatement_pct"].abs().max()),
        "restatement_examples": [
            {"quarter": str(r.quarter), "first": float(r.value), "latest": float(r.latest_value),
             "pct": round(float(r.restatement_pct) * 100, 2)}
            for r in material.reindex(material["restatement_pct"].abs().sort_values(ascending=False).index).head(5).itertuples()
        ],
        "tag_by_quarter": series.groupby("tag")["quarter"].agg(lambda x: f"{x.min()}..{x.max()} ({len(x)})").to_dict(),
        "non_positive_values": [str(p) for p in s[s <= 0].index],
        "qoq_outliers": [str(p) for p, v in qoq.items() if abs(v) > 0.5],
        "yoy_outliers": [str(p) for p, v in yoy.items() if abs(v) > 0.5],
        "long_quarters_53wk": [str(r.quarter) for r in series.itertuples() if (r.end - r.start).days >= 97],
    })
    issues = 0
    issues += len(q["missing_quarters"]) > 0
    issues += q["n_material_restatements"] > 2
    issues += len(q["calendar_collisions"]) > 0
    issues += len(q["tag_disagreements"]) > 0
    issues += len(q["non_positive_values"]) > 0
    min_needed = config.MIN_TRAIN_QUARTERS + config.N_FOLDS + max(config.HORIZONS) + 8
    if q["n_contiguous"] < min_needed or q["non_positive_values"]:
        q["verdict"] = "NOT READY"
    elif issues:
        q["verdict"] = "READY WITH CAVEATS"
    else:
        q["verdict"] = "READY"
    q["min_contiguous_needed"] = min_needed
    q["drivers"] = {k: edgar.concept_coverage(companyfacts, k) for k in config.DRIVER_CONCEPTS}
    return series, q


def readiness_markdown(company: config.Company, q: dict) -> str:
    L = [f"# Data readiness: {company.ticker} ({q.get('entity_name')})", ""]
    L += [f"**Verdict: {q['verdict']}**  ", f"Sector: {company.sector} | CIK {company.cik} | fiscal year ends in {q.get('fiscal_year_end')}", ""]
    if not q.get("n_quarters"):
        return "\n".join(L + ["No usable revenue facts found."])
    L += ["## Revenue series", "",
          "| Check | Result |", "|---|---|",
          f"| Quarters found | {q['n_quarters']} ({q['first_quarter']} to {q['last_quarter']}) |",
          f"| Contiguous run used for modelling | {q['n_contiguous']} quarters from {q['contiguous_start']} (need >= {q['min_contiguous_needed']}) |",
          f"| Missing quarters | {', '.join(q['missing_quarters']) or 'none'} |",
          f"| Q4 / quarters derived from YTD or annual minus 9M | {q['n_derived']} |",
          f"| Tags used | {'; '.join(f'{k}: {v}' for k, v in q['tag_by_quarter'].items())} |",
          f"| Non-USD units on revenue tags | {', '.join(q['non_usd_units']) or 'none'} |",
          f"| Periods reported in >1 filing (duplicates) | {q['n_periods_multi_filing']} of {q['n_periods']} |",
          f"| Periods whose value changed between filings | {q['n_periods_conflicting_values']} |",
          f"| Quarters restated >0.1% / >1% | {q['n_restated']} / {q['n_material_restatements']} (max {q['max_abs_restatement_pct']*100:.1f}%) |",
          f"| Tag disagreements (>1%) | {len(q['tag_disagreements'])} |",
          f"| Calendar-mapping collisions | {', '.join(q['calendar_collisions']) or 'none'} |",
          f"| 14-week (53-week-year) quarters | {', '.join(q['long_quarters_53wk']) or 'none'} |",
          f"| QoQ moves > 50% (log) | {', '.join(q['qoq_outliers']) or 'none'} |",
          f"| YoY moves > 50% (log) | {', '.join(q['yoy_outliers']) or 'none'} |",
          ""]
    if q["restatement_examples"]:
        L += ["Largest restatements (first-reported vs latest-reported, USD):", ""]
        L += [f"- {r['quarter']}: {r['first']:,.0f} -> {r['latest']:,.0f} ({r['pct']:+.2f}%)" for r in q["restatement_examples"]]
        L += ["", "The model uses **first-reported** values (what was known at forecast time); restatements are reported, not silently absorbed.", ""]
    if q["tag_disagreements"]:
        L += ["Tag disagreements (first 5):", ""] + [f"- {d}" for d in q["tag_disagreements"][:5]] + [""]
    L += ["## Candidate drivers in companyfacts", "",
          "| Concept | Present | Quarters covered | Range | Kind |", "|---|---|---|---|---|"]
    for k, v in q["drivers"].items():
        rng = f"{v['first']}..{v['last']}" if v["first"] else "-"
        L.append(f"| {k} ({config.DRIVER_CONCEPTS[k]}) | {'yes' if v['present'] else 'no'} | {v['n_quarters']} | {rng} | {v['kind'] or '-'} |")
    L += ["", "Drivers used by the model: revenue history only (lags, rolling means, YoY growth, seasonality), "
          "plus FRED retail sales and CPI in the `lgbm_macro` variant. The concepts above are documented "
          "for future work and are **not** model inputs.", "",
          f"Sector note (a hypothesis, not tested here): {SECTOR_DRIVER_NOTES.get(company.sector, '-')}", "",
          "## Material gaps", "",
          "- Segment and geographic revenue are not in the companyfacts API (it excludes dimensional facts), so mix shifts are invisible.",
          "- Fiscal quarters are mapped to the nearest calendar quarter; a fiscal quarter can end up to ~45 days from the calendar quarter end.",
          "- Quarterly values are first-reported vintages reconstructed from filing dates; companyfacts only has facts filed in XBRL (2009+)."]
    if q["n_derived"]:
        L.append(f"- {q['n_derived']} quarters are derived by subtraction (usually Q4 = annual - 9M YTD), so they inherit any restatement in either component.")
    if q["long_quarters_53wk"]:
        L.append("- 53-week fiscal years add a 14th week to some quarters, inflating those quarters by ~7.7% versus a 13-week quarter.")
    return "\n".join(L) + "\n"


def macro_quarterly(refresh: bool = False) -> pd.DataFrame:
    """Quarterly YoY log growth of FRED series, with a publication date per quarter."""
    out = None
    for series in config.FRED_SERIES:
        m = ingest.fetch_fred(series, refresh=refresh)
        m["quarter"] = m["date"].dt.to_period("Q")
        qm = m.groupby("quarter")["value"].agg(["mean", "count"])
        qm = qm[qm["count"] == 3]["mean"]  # complete quarters only
        yoy = np.log(qm) - np.log(qm.reindex(qm.index - 4).to_numpy())
        col = {"RSAFS": "macro_retail_yoy", "CPIAUCNS": "macro_cpi_yoy"}[series]
        frame = yoy.rename(col).to_frame()
        out = frame if out is None else out.join(frame, how="outer")
    out = out.dropna().reset_index()
    out["available_date"] = out["quarter"].apply(lambda p: p.end_time.normalize() + pd.Timedelta(days=config.MACRO_PUBLICATION_LAG_DAYS))
    out["quarter"] = out["quarter"].astype(str)
    return out


def run_quality(with_macro: bool = True) -> pd.DataFrame:
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.READINESS.mkdir(parents=True, exist_ok=True)
    panels, summary = [], []
    for c in config.COMPANIES:
        cf = ingest.fetch_companyfacts(c.cik)
        series, q = analyse_company(c, cf)
        (config.READINESS / f"{c.ticker}.md").write_text(readiness_markdown(c, q))
        (config.READINESS / f"{c.ticker}.json").write_text(json.dumps(q, indent=2, default=str))
        if not series.empty:
            panels.append(series.assign(ticker=c.ticker))
        summary.append({k: q.get(k) for k in ["ticker", "verdict", "first_quarter", "last_quarter", "n_quarters",
                                               "n_contiguous", "contiguous_start", "n_derived", "n_restated",
                                               "n_material_restatements", "fiscal_year_end"]}
                       | {"missing_quarters": len(q.get("missing_quarters", [])),
                          "tag_disagreements": len(q.get("tag_disagreements", [])),
                          "calendar_collisions": len(q.get("calendar_collisions", []))})
        print(f"[quality] {c.ticker}: {q['verdict']} ({q.get('n_contiguous', 0)} contiguous quarters)")
    panel = pd.concat(panels, ignore_index=True)
    panel = panel.rename(columns={"value": "revenue", "latest_value": "latest_revenue",
                                  "start": "period_start", "end": "period_end"})
    panel["quarter"] = panel["quarter"].astype(str)
    cols = ["ticker", "quarter", "period_start", "period_end", "revenue", "available_date", "latest_revenue",
            "latest_filed", "restatement_pct", "source", "tag", "n_filings"]
    panel[cols].to_csv(config.DATA_PROCESSED / "quarterly_revenue.csv", index=False)
    summ = pd.DataFrame(summary)
    summ.to_csv(config.DATA_PROCESSED / "quality_summary.csv", index=False)
    if with_macro:
        macro_quarterly().to_csv(config.DATA_PROCESSED / "macro_quarterly.csv", index=False)
    return summ
