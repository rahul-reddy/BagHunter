"""Fictional statement boundaries: duration, units, revisions, availability and citations."""

import copy
import json
from datetime import UTC, datetime

import pytest

from packages.data.sec_statements import normalize_statements, statement_analysis

CLOCK = datetime(2023, 5, 1, tzinfo=UTC)
ACC = "0000000001-23-000001"


def sources():
    return {
        "cik": 1,
        "filings": {
            "recent": {
                "accessionNumber": [ACC],
                "acceptanceDateTime": ["2023-04-01T12:00:00Z"],
                "filingDate": ["2023-04-01"],
                "form": ["10-Q"],
                "primaryDocument": ["fixture.htm"],
            }
        },
    }, {"cik": 1, "facts": {"us-gaap": {}}}


def add(company, concept, value, unit="USD", start="2023-01-01", end="2023-03-31", **extra):
    record = {"accn": ACC, "form": "10-Q", "filed": "2023-04-01", "end": end, "val": value, **extra}
    if start is not None:
        record["start"] = start
    company["facts"]["us-gaap"].setdefault(concept, {"units": {}})["units"].setdefault(
        unit, []
    ).append(record)
    return record


def normalize(submissions, company, clock=CLOCK):
    return normalize_statements(
        json.dumps(submissions).encode(), json.dumps(company).encode(), "entity", clock
    )


def test_direct_quarters_ytd_and_instants_keep_exact_periods_units_and_sources():
    submissions, company = sources()
    add(company, "Revenues", 120)
    add(company, "Revenues", 220, start="2022-10-01")
    add(company, "Revenues", 320, start="2022-07-01")
    add(company, "EarningsPerShareDiluted", 1.25, "USD/shares")
    add(company, "WeightedAverageNumberOfDilutedSharesOutstanding", 50, "shares")
    add(company, "Assets", 1000, start=None)
    add(company, "CommonStockSharesOutstanding", 60, "shares", start=None)
    original = copy.deepcopy((submissions, company))
    report = normalize(submissions, company)
    assert {f["basis"] for f in report["facts"]} == {"QUARTER", "YTD_6M", "YTD_9M", "INSTANT"}
    assert len(report["facts"]) == 7
    assert all(f["published_at"] == "2023-04-02T00:00:00Z" for f in report["facts"])
    assert all(f["source_url"].endswith("000000000123000001/fixture.htm") for f in report["facts"])
    assert {f["unit"] for f in report["facts"]} == {"USD", "USD/shares", "shares"}
    assert (submissions, company) == original


def test_annual_facts_require_annual_forms_and_no_fourth_quarter_is_inferred():
    submissions, company = sources()
    add(company, "Revenues", 400, start="2022-01-01", end="2022-12-31")
    assert normalize(submissions, company)["facts"] == []
    submissions["filings"]["recent"]["form"][0] = "10-K"
    company["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["form"] = "10-K"
    report = normalize(submissions, company)
    assert [f["basis"] for f in report["facts"]] == ["ANNUAL"]


def test_publication_and_processing_lag_and_future_invariance():
    submissions, company = sources()
    add(company, "Revenues", 100)
    assert normalize(submissions, company, datetime(2023, 4, 2, 23, 59, tzinfo=UTC))["facts"] == []
    baseline = normalize(submissions, company)
    index = submissions["filings"]["recent"]
    for field, value in {
        "accessionNumber": "0000000001-23-000002",
        "acceptanceDateTime": "2023-06-01T12:00:00Z",
        "filingDate": "2023-06-01",
        "form": "10-Q/A",
        "primaryDocument": "future.htm",
    }.items():
        index[field].append(value)
    add(company, "Revenues", 999, accn="0000000001-23-000002", form="10-Q/A", filed="2023-06-01")
    later = normalize(submissions, company)
    assert later["facts"] == baseline["facts"]
    assert later["excluded_counts"]["future_or_processing_lag"] == 1


@pytest.mark.parametrize("value", [True, "100", float("nan"), float("inf")])
def test_invalid_numeric_amounts_reject(value):
    submissions, company = sources()
    add(company, "Revenues", value)
    with pytest.raises(ValueError):
        normalize(submissions, company)


def test_share_counts_cannot_be_negative_and_unsupported_units_are_counted():
    submissions, company = sources()
    add(company, "Revenues", 100, "EUR")
    assert normalize(submissions, company)["excluded_counts"]["unsupported_unit"] == 1
    add(company, "CommonStockSharesOutstanding", -1, "shares", start=None)
    with pytest.raises(ValueError, match="nonnegative"):
        normalize(submissions, company)


def test_alias_conflicts_reject_and_same_value_aliases_deduplicate():
    submissions, company = sources()
    add(company, "Revenues", 100)
    row = add(company, "SalesRevenueNet", 100)
    assert len(normalize(submissions, company)["facts"]) == 1
    row["val"] = 101
    with pytest.raises(ValueError, match="Conflicting"):
        normalize(submissions, company)


@pytest.mark.parametrize("change", ["cik", "date", "path", "clock"])
def test_binding_and_timestamp_fail_closed(change):
    submissions, company = sources()
    row = add(company, "Revenues", 100)
    clock = CLOCK
    if change == "cik":
        company["cik"] = 2
    if change == "date":
        row["filed"] = "2023-04-03"
    if change == "path":
        submissions["filings"]["recent"]["primaryDocument"][0] = "../.env"
    if change == "clock":
        clock = datetime(2023, 5, 1)
    with pytest.raises(ValueError):
        normalize(submissions, company, clock)


def test_growth_dilution_margins_and_narrow_fcf_have_complete_citations():
    submissions, company = sources()
    for start, end, revenue, shares in [
        ("2022-01-01", "2022-03-31", 100, 50),
        ("2023-01-01", "2023-03-31", 120, 55),
    ]:
        add(company, "Revenues", revenue, start=start, end=end)
        add(
            company,
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            shares,
            "shares",
            start=start,
            end=end,
        )
    add(company, "OperatingIncomeLoss", -12)
    add(company, "NetCashProvidedByUsedInOperatingActivities", 30)
    add(company, "PaymentsToAcquirePropertyPlantAndEquipment", 10)
    report = normalize(submissions, company)
    row = statement_analysis(report)[0]
    assert row["values"]["revenue_yoy"] == pytest.approx(0.2)
    assert row["values"]["weighted_shares_yoy"] == pytest.approx(0.1)
    assert row["values"]["operating_margin"] == -0.1
    assert row["values"]["cfo_less_ppe"] == 20
    assert len(row["citations"]) == 7
    assert all(c in report["facts"] for c in row["citations"])


def test_revision_order_uses_acceptance_not_accession_and_different_periods_do_not_mix():
    submissions, company = sources()
    add(company, "Revenues", 100)
    add(company, "NetCashProvidedByUsedInOperatingActivities", 30)
    add(company, "PaymentsToAcquirePropertyPlantAndEquipment", 10, start="2023-01-02")
    report = normalize(submissions, company)
    revenue = next(f for f in report["facts"] if f["metric"] == "revenue")
    revision = revenue | {
        "value": 200,
        "accepted_at": "2023-04-01T18:00:00Z",
        "accession": "0000000001-23-000000",
    }
    rows = statement_analysis(report | {"facts": report["facts"] + [revision]})
    current = next(row for row in rows if row["period_start"] == "2023-01-01")
    assert current["values"]["revenue"] == 200
    assert current["values"]["cfo_less_ppe"] is None


@pytest.mark.parametrize("prior", [0, -100])
def test_yoy_missing_nonpositive_or_incomparable_prior_is_null(prior):
    submissions, company = sources()
    add(company, "Revenues", prior, start="2022-01-01", end="2022-03-31")
    add(company, "Revenues", 120)
    row = statement_analysis(normalize(submissions, company))[0]
    assert row["values"]["revenue_yoy"] is None


def test_missing_accessions_period_bounds_and_input_limits_are_explicit():
    submissions, company = sources()
    add(company, "Revenues", 1, accn="0000000001-20-000001")
    add(company, "Revenues", 2, start="2023-03-01")
    report = normalize(submissions, company)
    assert report["facts"] == []
    assert report["excluded_counts"]["missing_accession"] == 1
    assert report["excluded_counts"]["unsupported_form_period"] == 1
    company["facts"]["us-gaap"]["Revenues"]["units"]["USD"] = [{}] * 100_001
    with pytest.raises(ValueError, match="Invalid statement records"):
        normalize(submissions, company)
    with pytest.raises(ValueError, match="size exceeds"):
        normalize_statements(b"x" * (20 * 1024 * 1024 + 1), b"{}", "entity", CLOCK)


def test_narrow_fcf_needs_same_filing_and_nonnegative_ppe_and_ratios_stay_finite():
    submissions, company = sources()
    add(company, "Revenues", 1e-300)
    add(company, "OperatingIncomeLoss", 1e300)
    add(company, "NetCashProvidedByUsedInOperatingActivities", 30)
    add(company, "PaymentsToAcquirePropertyPlantAndEquipment", -10)
    report = normalize(submissions, company)
    row = statement_analysis(report)[0]
    assert row["values"]["operating_margin"] is None
    assert row["values"]["cfo_less_ppe"] is None
    for fact in report["facts"]:
        if fact["metric"] == "ppe_payments":
            fact["value"] = 10
            fact["accession"] = "0000000001-23-000002"
    assert statement_analysis(report)[0]["values"]["cfo_less_ppe"] is None


def test_shared_fundamental_revision_selection_breaks_publication_ties_by_acceptance():
    from packages.research.fundamentals import statement_ratios
    from packages.shared.models import Fact

    common = {
        "security_id": "entity",
        "period_end": "2022-12-31",
        "metric": "annual_revenue",
        "unit": "USD",
        "published_at": "2023-04-02T00:00:00Z",
        "source_id": "fixture",
        "source_url": "https://example.invalid/fixture",
    }
    old = Fact(**(common | {"accepted_at": "2023-04-01T12:00:00Z", "accession": "z", "value": 100}))
    new = Fact(**(common | {"accepted_at": "2023-04-01T18:00:00Z", "accession": "a", "value": 200}))
    assert statement_ratios([new, old], "entity", CLOCK)["revenue"] == 200
    assert statement_ratios([old, new], "entity", CLOCK)["revenue"] == 200


def test_analysis_period_bound_rejects_instead_of_truncating(monkeypatch):
    from packages.data import sec_statements

    submissions, company = sources()
    add(company, "Revenues", 100)
    add(company, "Assets", 1000, start=None)
    report = normalize(submissions, company)
    monkeypatch.setattr(sec_statements, "MAX_ANALYSIS_PERIODS", 1)
    with pytest.raises(ValueError, match="period count exceeds"):
        statement_analysis(report)
