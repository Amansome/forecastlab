"""EDGAR parsing: quarter derivation, vintages, duplicates, units, calendar mapping."""
from __future__ import annotations

import pandas as pd

from forecastlab import edgar


def fact(start, end, val, filed, form="10-Q", accn=None, fp="Q1", fy=2022):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form,
            "accn": accn or f"acc-{filed}-{form}", "fy": fy, "fp": fp}


def companyfacts():
    """Fiscal year Oct-Sep (like Apple). FY2022 quarters: 100, 110, 120, Q4 derived = 500-330 = 170."""
    usd = [
        fact("2021-10-01", "2021-12-31", 100, "2022-02-01"),
        fact("2022-01-01", "2022-03-31", 110, "2022-05-01"),
        fact("2021-10-01", "2022-03-31", 210, "2022-05-01"),                 # 6M YTD
        fact("2022-04-01", "2022-06-30", 120, "2022-08-01"),
        fact("2021-10-01", "2022-06-30", 330, "2022-08-01"),                 # 9M YTD
        fact("2021-10-01", "2022-09-30", 500, "2022-11-01", form="10-K", fp="FY"),
        # FY2023 Q1, plus the FY2022 Q1 comparative re-reported later with a RESTATED value
        fact("2022-10-01", "2022-12-31", 130, "2023-02-01", fy=2023),
        fact("2021-10-01", "2021-12-31", 102, "2023-02-01", fy=2023),
        # duplicate filing of the same value (amendment)
        fact("2022-01-01", "2022-03-31", 110, "2022-06-01", form="10-Q/A", accn="amend"),
        # an 8-K value that must be ignored
        fact("2022-10-01", "2022-12-31", 999, "2023-01-15", form="8-K"),
    ]
    return {"entityName": "Test Co", "facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": usd}},
        "Revenues": {"units": {"EUR": [fact("2021-10-01", "2021-12-31", 90, "2022-02-01")]}},
    }}}


def test_build_quarterly_derives_q4_and_uses_first_reported_values():
    facts = edgar.facts_to_frame(companyfacts(), ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
    s, diag = edgar.build_quarterly(facts, ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
    got = s.set_index(s["quarter"].astype(str))
    assert got.loc["2021Q4", "value"] == 100           # first-reported, not the restated 102
    assert got.loc["2021Q4", "latest_value"] == 102
    assert bool(got.loc["2021Q4", "restated"])
    assert got.loc["2022Q3", "value"] == 170            # Q4 FY22 = 500 - 330
    assert got.loc["2022Q3", "source"] == "derived"
    assert got.loc["2022Q3", "available_date"] == pd.Timestamp("2022-11-01")
    assert got.loc["2022Q4", "value"] == 130            # 8-K value 999 ignored
    assert diag["non_usd_units"] == ["Revenues:EUR"]
    assert diag["n_periods_multi_filing"] >= 2
    assert diag["n_periods_conflicting_values"] == 1
    assert diag["excluded_forms"] == {"8-K": 1}


def test_derived_quarter_is_point_in_time():
    """Q4 must use the 9M YTD value as known when the 10-K was filed, not a later restatement."""
    cf = companyfacts()
    cf["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"].append(
        fact("2021-10-01", "2022-06-30", 300, "2023-08-01"))   # 9M restated AFTER the 10-K
    facts = edgar.facts_to_frame(cf, ["RevenueFromContractWithCustomerExcludingAssessedTax"])
    s, _ = edgar.build_quarterly(facts, ["RevenueFromContractWithCustomerExcludingAssessedTax"])
    q = s.set_index(s["quarter"].astype(str)).loc["2022Q3"]
    assert q["value"] == 170 and q["latest_value"] == 200


def test_tag_choice_is_point_in_time():
    cf = {"facts": {"us-gaap": {
        "SalesRevenueNet": {"units": {"USD": [fact("2016-01-01", "2016-03-31", 50, "2016-05-01"),
                                              fact("2016-04-01", "2016-06-30", 55, "2016-08-01")]}},
        # new tag: Q2 2016 only appears a year later as a comparative, with a different value
        "Revenues": {"units": {"USD": [fact("2016-04-01", "2016-06-30", 56, "2017-08-01"),
                                       fact("2016-07-01", "2016-09-30", 60, "2016-11-01")]}},
    }}}
    cf["facts"]["us-gaap"]["SalesRevenueNet"]["units"]["USD"].append(fact("2016-07-01", "2016-09-30", 59, "2016-11-01"))
    tags = ["Revenues", "SalesRevenueNet"]
    s, diag = edgar.build_quarterly(edgar.facts_to_frame(cf, tags), tags)
    got = s.set_index(s["quarter"].astype(str))
    assert got.loc["2016Q1", "tag"] == "SalesRevenueNet"    # fallback fills history
    # Q2: the value first filed (old tag, 2016-08-01) is used, not the later comparative
    assert got.loc["2016Q2", "value"] == 55 and got.loc["2016Q2", "tag"] == "SalesRevenueNet"
    assert got.loc["2016Q2", "latest_value"] == 56 and got.loc["2016Q2", "latest_tag"] == "Revenues"
    assert bool(got.loc["2016Q2", "restated"])
    # Q3: both tags filed the same day -> tag priority breaks the tie
    assert got.loc["2016Q3", "value"] == 60 and got.loc["2016Q3", "tag"] == "Revenues"
    assert len(diag["tag_disagreements"]) == 2              # 55 vs 56 and 59 vs 60 differ by > 1%
    assert diag["tag_switches"][0]["quarter"] == "2016Q3"


def test_calendar_quarter_mapping():
    cases = {"2023-04-30": "2023Q1", "2023-07-01": "2023Q2", "2023-09-30": "2023Q3",
             "2024-01-31": "2023Q4", "2024-02-03": "2023Q4", "2023-05-31": "2023Q2", "2023-12-31": "2023Q4"}
    for end, q in cases.items():
        assert str(edgar.calendar_quarter(pd.Timestamp(end))) == q, end


def test_missing_quarters_and_contiguous_tail():
    q = pd.PeriodIndex(["2020Q1", "2020Q2", "2020Q4", "2021Q1", "2021Q2"], freq="Q")
    s = pd.DataFrame({"quarter": q, "value": 1.0})
    assert [str(p) for p in edgar.missing_quarters(s)] == ["2020Q3"]
    assert [str(p) for p in edgar.contiguous_tail(s)["quarter"]] == ["2020Q4", "2021Q1", "2021Q2"]


def test_readiness_report_runs_and_flags_short_history():
    from forecastlab import config, quality
    cf = companyfacts()
    cf["facts"]["us-gaap"]["InventoryNet"] = {"units": {"USD": [
        {"end": "2022-03-31", "val": 5, "filed": "2022-05-01", "form": "10-Q", "accn": "x", "fy": 2022, "fp": "Q2"}]}}
    company = config.Company("TEST", 1, "Test Co", "Retail")
    series, q = quality.analyse_company(company, cf)
    assert q["verdict"] == "NOT READY"                     # 5 quarters is far too short
    assert q["n_derived"] == 1 and q["n_restated"] == 1
    assert q["drivers"]["InventoryNet"]["kind"] == "instant"
    md = quality.readiness_markdown(company, q)
    for section in ("## Revenue series", "## Candidate drivers", "## Material gaps", "first-reported"):
        assert section in md


def test_mis_tagged_fact_cannot_create_a_negative_quarter():
    """A bogus annual value under an equivalent tag must not yield a negative derived Q4."""
    usd_sales = [fact("2013-07-01", "2013-09-30", 20, "2013-10-25"), fact("2013-10-01", "2013-12-31", 21, "2014-01-25"),
                 fact("2013-07-01", "2014-03-31", 62, "2014-04-23"), fact("2014-01-01", "2014-03-31", 21, "2014-04-23"),
                 fact("2013-07-01", "2014-06-30", 83, "2014-08-08", form="10-K", fp="FY")]
    usd_rev = [fact("2013-07-01", "2013-09-30", 20, "2013-10-25"), fact("2013-10-01", "2013-12-31", 21, "2014-01-25"),
               fact("2013-07-01", "2014-06-30", 29, "2014-08-08", form="10-K", fp="FY")]   # mis-tagged subtotal
    cf = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": usd_rev}}, "SalesRevenueNet": {"units": {"USD": usd_sales}}}}}
    tags = ["Revenues", "SalesRevenueNet"]
    s, _ = edgar.build_quarterly(edgar.facts_to_frame(cf, tags), tags)
    q4 = s.set_index(s["quarter"].astype(str)).loc["2014Q2"]
    assert q4["value"] == 21 and q4["tag"] == "SalesRevenueNet"
    assert (s["value"] > 0).all()
