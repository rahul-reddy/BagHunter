"""Dated USD cap, volatility admission and earnings-only baseline boundaries."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from packages.backtest.constrained import (
    PortfolioPolicy,
    UnavailableRankingInputs,
    comparator_catalog,
    simulate,
)
from packages.data.fixture import fixture
from packages.research.admission import annual_earnings_growth, capitalization_at
from packages.shared.models import CapitalizationObservation, Fact

CLOCK = datetime(2020, 1, 3, 23, tzinfo=UTC)


def cap(**changes):
    return CapitalizationObservation(
        **{
            "security_id": "fx-compound",
            "observed_at": CLOCK - timedelta(days=1),
            "published_at": CLOCK - timedelta(days=1),
            "valid_until": CLOCK + timedelta(days=30),
            "value_usd": 100_000_000,
            "currency": "USD",
            "source_id": "fixture-v1",
            **changes,
        }
    )


def earnings(year, value, **changes):
    return Fact(
        **{
            "security_id": "fx-compound",
            "period_end": date(year, 12, 31),
            "accepted_at": datetime(year + 1, 1, 1, tzinfo=UTC),
            "published_at": datetime(year + 1, 1, 2, tzinfo=UTC),
            "metric": "annual_net_income",
            "value": value,
            "unit": "USD",
            "accession": f"fixture-{year}",
            "source_id": "fixture-v1",
            "source_url": "fixture://fixture-v1",
            **changes,
        }
    )


def test_capitalization_needs_known_publication_validity_and_declared_usd():
    row = cap()
    assert capitalization_at([row], row.security_id, CLOCK)["value_usd"] == 100_000_000
    assert capitalization_at(
        [row], row.security_id, CLOCK.astimezone(timezone(timedelta(hours=10)))
    ) == capitalization_at([row], row.security_id, CLOCK)
    future = cap(value_usd=200_000_000, published_at=CLOCK + timedelta(seconds=1))
    assert capitalization_at([row, future], row.security_id, CLOCK) == capitalization_at(
        [row], row.security_id, CLOCK
    )
    assert capitalization_at([row], row.security_id, row.valid_until)["value_usd"] is None
    assert (
        capitalization_at([row], row.security_id, CLOCK + timedelta(days=6))["status"]
        == "STALE_DATED_CAPITALIZATION"
    )
    assert capitalization_at([], row.security_id, CLOCK)["value_usd"] is None
    assert capitalization_at([cap(value_usd=0)], row.security_id, CLOCK)["value_usd"] == 0


def test_cap_revisions_conflicts_and_utc_age_do_not_create_convenient_values():
    row = cap()
    revised = cap(value_usd=120_000_000, published_at=CLOCK)
    assert capitalization_at([row, revised], row.security_id, CLOCK)["value_usd"] == 120_000_000
    conflicting = cap(value_usd=90_000_000, source_id="another-source")
    assert (
        capitalization_at([row, conflicting], row.security_id, CLOCK)["status"]
        == "AMBIGUOUS_DATED_CAPITALIZATION"
    )
    assert capitalization_at([row, revised], row.security_id, CLOCK) == capitalization_at(
        [revised, row], row.security_id, CLOCK
    )
    shifted = cap(observed_at=(CLOCK - timedelta(days=1)).astimezone(timezone(timedelta(hours=10))))
    assert capitalization_at([shifted], row.security_id, CLOCK, max_age_days=0)["value_usd"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "EUR"},
        {"value_usd": True},
        {"value_usd": "100"},
        {"value_usd": float("nan")},
        {"published_at": CLOCK - timedelta(days=2)},
        {"valid_until": CLOCK - timedelta(days=2)},
        {"published_at": datetime(2020, 1, 3)},
    ],
)
def test_invalid_cap_units_numbers_and_clocks_reject(changes):
    with pytest.raises(ValidationError):
        cap(**changes)


def test_earnings_growth_is_annual_income_not_revenue_and_uses_actual_lag():
    facts = [earnings(2018, 100), earnings(2019, 120)]
    result = annual_earnings_growth(facts, "fx-compound", CLOCK)
    assert result["value"] == pytest.approx(0.2)
    assert len(result["evidence"]) == 2
    before = datetime(2020, 1, 2, 23, 59, 59, tzinfo=UTC)
    assert annual_earnings_growth(facts, "fx-compound", before)["value"] is None
    revenue = [fact.model_copy(update={"metric": "annual_revenue"}) for fact in facts]
    assert annual_earnings_growth(revenue, "fx-compound", CLOCK)["value"] is None
    quarterly = [fact.model_copy(update={"metric": "quarterly_net_income"}) for fact in facts]
    assert annual_earnings_growth(quarterly, "fx-compound", CLOCK)["value"] is None


def test_earnings_revisions_and_future_updates_preserve_past_inputs():
    old = [earnings(2018, 100), earnings(2019, 120)]
    revision = earnings(
        2019,
        180,
        accepted_at=CLOCK + timedelta(days=1),
        published_at=CLOCK + timedelta(days=2),
        accession="revision",
    )
    assert annual_earnings_growth([revision, *old], "fx-compound", CLOCK) == annual_earnings_growth(
        old, "fx-compound", CLOCK
    )
    later = CLOCK + timedelta(days=3)
    assert annual_earnings_growth([revision, *old], "fx-compound", later)["value"] == pytest.approx(
        0.8
    )
    assert annual_earnings_growth([*old, revision], "fx-compound", later) == annual_earnings_growth(
        [revision, *old], "fx-compound", later
    )


@pytest.mark.parametrize(
    "mutation", ["zero_prior", "negative_prior", "gap", "stale", "unit", "conflict"]
)
def test_unsupported_earnings_are_missing_not_zero_or_older_usd_fallback(mutation):
    facts = [earnings(2018, 100), earnings(2019, 120)]
    clock = CLOCK
    if mutation == "zero_prior":
        facts[0] = earnings(2018, 0)
    elif mutation == "negative_prior":
        facts[0] = earnings(2018, -100)
    elif mutation == "gap":
        facts[0] = earnings(2017, 100)
    elif mutation == "stale":
        clock = datetime(2026, 1, 1, tzinfo=UTC)
    elif mutation == "unit":
        facts[1] = earnings(2019, 120, unit="EUR")
    else:
        facts.append(earnings(2019, 180))
    result = annual_earnings_growth(facts, "fx-compound", clock)
    assert result["value"] is None and result["status"] != "DATED_ANNUAL_NET_INCOME_GROWTH"
    assert (
        annual_earnings_growth([earnings(2018, 100), earnings(2019, 0)], "fx-compound", CLOCK)[
            "value"
        ]
        == -1
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"min_capitalization_usd": 200, "max_capitalization_usd": 100},
        {"min_capitalization_usd": True},
        {"max_annualized_volatility_20d": float("inf")},
        {"max_capitalization_age_days": False},
        {"max_annualized_volatility_20d": -1},
    ],
)
def test_invalid_admission_policies_reject(changes):
    with pytest.raises(ValidationError):
        PortfolioPolicy(**changes)


@pytest.fixture(scope="module")
def source():
    return fixture()


def test_required_capitalization_and_volatility_exclusions_are_retained(source):
    missing = simulate(source, PortfolioPolicy(min_capitalization_usd=1))
    assert missing["executions"] == []
    assert any(
        row["reason"] == "NO_KNOWN_DATED_USD_CAPITALIZATION" for row in missing["exclusions"]
    )
    volatile = simulate(source, PortfolioPolicy(max_annualized_volatility_20d=0))
    assert volatile["executions"] == []
    assert any(
        row["reason"] == "ABOVE_ANNUALIZED_20D_VOLATILITY_CEILING" for row in volatile["exclusions"]
    )
    external = source.model_copy(update={"mode": "EXTERNAL_UNVERIFIED"})
    with pytest.raises(ValueError, match="cannot relabel"):
        simulate(external, PortfolioPolicy())


def test_unavailable_earnings_comparator_is_retained_without_revenue_or_cash_metrics(source):
    with pytest.raises(UnavailableRankingInputs):
        simulate(source, PortfolioPolicy(selector="earnings_growth"))
    catalog = comparator_catalog(source, PortfolioPolicy())
    unavailable = [
        row for row in catalog["attempts"] if row["status"] == "UNAVAILABLE_DATED_ANNUAL_EARNINGS"
    ]
    assert len(unavailable) == 1 and unavailable[0]["metrics"] is None
    assert len(catalog["reports"]) == 7
    assert not any(row["policy"]["selector"] == "earnings_growth" for row in catalog["reports"])


def test_known_earnings_rank_has_citations_and_never_uses_future_revisions(source):
    facts = [
        earnings(year, value, security_id=sid)
        for sid, values in [
            ("fx-compound", [100, 110, 121, 133]),
            ("fx-failure", [100, 90, 80, 70]),
            ("fx-steady", [100, 200, 400, 800]),
        ]
        for year, value in zip(range(2017, 2021), values, strict=True)
    ]
    dataset = source.model_copy(update={"facts": [*source.facts, *facts]})
    policy = PortfolioPolicy(
        selector="earnings_growth",
        max_position=1,
        max_sector=1,
        min_dollar_volume=0,
        min_price=0.01,
    )
    report = simulate(dataset, policy)
    assert report["executions"] and report["executions"][0]["security_id"] == "fx-steady"
    evidence = report["allocation_ledger"][0]["targets"][0]["earnings_growth_evidence"]
    assert evidence["status"] == "DATED_ANNUAL_NET_INCOME_GROWTH" and len(evidence["evidence"]) == 2
    future = earnings(
        2021,
        1e12,
        accepted_at=datetime(2028, 1, 1, tzinfo=UTC),
        published_at=datetime(2028, 1, 2, tzinfo=UTC),
    )
    changed = simulate(dataset.model_copy(update={"facts": [future, *dataset.facts]}), policy)
    assert changed["rows"] == report["rows"] and changed["executions"] == report["executions"]


@pytest.mark.parametrize(
    "bounds,reason",
    [
        ({"min_capitalization_usd": 100_000_001}, "BELOW_DATED_CAPITALIZATION_FLOOR"),
        ({"max_capitalization_usd": 99_999_999}, "ABOVE_DATED_CAPITALIZATION_CEILING"),
    ],
)
def test_known_capitalization_limits_are_enforced_at_each_decision(source, bounds, reason):
    sessions = sorted({bar.session for bar in source.bars})
    records = []
    for index in range(260, min(1000, len(sessions) - 23), 42):
        clock = datetime.combine(sessions[index], datetime.min.time(), UTC) + timedelta(hours=23)
        for instrument in source.instruments:
            records.append(
                cap(
                    security_id=instrument.security_id,
                    observed_at=clock,
                    published_at=clock,
                    valid_until=clock + timedelta(days=1),
                )
            )
    dataset = source.model_copy(update={"market_caps": records})
    policy = PortfolioPolicy(min_dollar_volume=0, min_price=0.01, **bounds)
    report = simulate(dataset, policy)
    assert report["executions"] == []
    assert any(row["reason"] == reason for row in report["exclusions"])
    accepted = simulate(
        dataset,
        PortfolioPolicy(
            min_dollar_volume=0,
            min_price=0.01,
            min_capitalization_usd=100_000_000,
            max_capitalization_usd=100_000_000,
        ),
    )
    assert accepted["executions"]
    assert (
        accepted["allocation_ledger"][0]["targets"][0]["admission_evidence"]["capitalization"][
            "value_usd"
        ]
        == 100_000_000
    )
