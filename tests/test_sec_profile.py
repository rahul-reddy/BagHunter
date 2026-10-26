"""Availability, revision, denominator and citation boundaries for descriptive SEC profiles."""

import copy

import pytest

from packages.research.sec_profile import financial_profile


def fact(period, value, metric="annual_revenue", **changes):
    return {
        "security_id": "entity",
        "period_end": period,
        "value": value,
        "metric": metric,
        "unit": "USD",
        "accepted_at": "2023-02-01T12:00:00Z",
        "published_at": "2023-02-02T00:00:00Z",
        "accession": "original",
        "amended": False,
        "source_id": "fixture",
        "source_url": "https://example.invalid/fixture",
        **changes,
    }


def profile(facts, **changes):
    return financial_profile(
        {
            "security_id": "entity",
            "asof": "2023-04-01T00:00:00Z",
            "processing_lag_hours": 24,
            "facts": facts,
            **changes,
        }
    )


def test_profile_growth_margins_and_exact_evidence_do_not_mutate_inputs():
    facts = [
        fact("2020-12-31", 100),
        fact("2021-12-31", 120),
        fact("2022-12-31", 180),
        fact("2022-12-31", -18, "annual_operating_income"),
        fact("2022-12-31", 36, "annual_operating_cashflow"),
    ]
    before = copy.deepcopy(facts)
    result = profile(facts)
    row = result["latest"]
    assert row["revenue_growth"] == 0.5
    assert row["growth_acceleration"] == pytest.approx(0.3)
    assert row["operating_margin"] == -0.1 and row["cashflow_margin"] == 0.2
    assert row["net_margin"] is None
    assert row["citations"] == [facts[2], facts[1], facts[3], facts[4]]
    assert facts == before


def test_same_day_revision_uses_acceptance_tiebreak_and_future_facts_are_inert():
    old = fact("2022-12-31", 100)
    revised = fact("2022-12-31", 200, accepted_at="2023-02-01T18:00:00Z", accession="revision")
    future = fact(
        "2022-12-31", 300, accepted_at="2023-05-01T00:00:00Z", published_at="2023-05-02T00:00:00Z"
    )
    assert profile([old, revised, future]) == profile([old, revised])
    assert profile([revised, old])["latest"]["revenue"] == 200
    assert profile([old], asof="2023-02-02T23:59:59Z")["latest"] is None
    assert profile([old], asof="2023-02-03T00:00:00Z")["latest"]["revenue"] == 100


@pytest.mark.parametrize("prior", [0, -100])
def test_nonpositive_denominator_and_gaps_never_invent_growth(prior):
    assert (
        profile([fact("2021-12-31", prior), fact("2022-12-31", 100)])["latest"]["revenue_growth"]
        is None
    )
    assert (
        profile([fact("2020-12-31", 100), fact("2022-12-31", 200)])["latest"]["revenue_growth"]
        is None
    )


def test_margins_require_same_period_currency_and_positive_revenue():
    facts = [
        fact("2022-12-31", 100),
        fact("2021-12-31", 30, "annual_net_income"),
        fact("2022-12-31", 20, "annual_operating_income", unit="EUR"),
    ]
    row = profile(facts)["latest"]
    assert row["net_margin"] is None and row["operating_margin"] is None
    assert (
        profile([fact("2022-12-31", 0), fact("2022-12-31", 20, "annual_net_income")])["latest"][
            "net_margin"
        ]
        is None
    )
    assert profile([fact("2022-12-31", 100, unit="EUR")])["latest"]["revenue"] is None


def test_overflow_is_missing_and_entity_or_clock_mismatch_rejects():
    assert (
        profile([fact("2021-12-31", 1e-300), fact("2022-12-31", 1e300)])["latest"]["revenue_growth"]
        is None
    )
    with pytest.raises(ValueError, match="entity mismatch"):
        profile([fact("2022-12-31", 1, security_id="other")])
    with pytest.raises(ValueError, match="availability policy"):
        profile([], asof="2023-04-01T00:00:00")
