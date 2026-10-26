"""Finite inputs must never silently produce infinite factors, wealth or risk outputs."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from packages.backtest.risk import daily_risk
from packages.backtest.validation import performance
from packages.research.features import snapshot
from packages.research.fundamentals import statement_ratios
from packages.shared.models import Bar, Fact, Instrument

CLOCK = datetime(2020, 5, 1, 23, tzinfo=UTC)


def fact(period, amount, metric="annual_revenue", unit="USD"):
    return Fact(
        security_id="fixture",
        period_end=period,
        accepted_at="2019-02-01T12:00:00Z",
        published_at="2019-02-02T00:00:00Z",
        metric=metric,
        value=amount,
        unit=unit,
        accession=period,
        source_id="fixture",
        source_url="https://example.invalid/fixture",
    )


def inputs(close=10, volume=100):
    instrument = Instrument(
        security_id="fixture",
        ticker="FX",
        name="Fixture",
        sector="Fixture",
        first_seen="2010-01-01",
    )
    bars = [
        Bar(
            security_id="fixture",
            session=date(2020, 1, 1) + timedelta(days=i),
            available_at=datetime(2020, 1, 1, 22, tzinfo=UTC) + timedelta(days=i),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=volume,
            source_id="fixture",
        )
        for i in range(121)
    ]
    return instrument, bars


def test_financial_overflow_stays_null_with_source_citations_and_missing_weight():
    facts = [fact("2017-12-31", 1e-300), fact("2018-12-31", 1e300)]
    result = statement_ratios(facts, "fixture", CLOCK)
    assert result["revenue_growth"] is None and "revenue_growth" in result["numeric_limits"]
    assert len(result["citations"]) == 2
    instrument, bars = inputs()
    feature = snapshot(instrument, bars, facts, CLOCK)
    assert feature["components"]["fundamental_inflection"] is None
    assert feature["missing_weight_penalty"] >= 25
    json.dumps(result, allow_nan=False)
    json.dumps(feature, allow_nan=False)
    result = statement_ratios(
        [fact("2018-12-31", 1e-300), fact("2018-12-31", 1e300, "annual_operating_income")],
        "fixture",
        CLOCK,
    )
    assert result["operating_margin"] is None and "operating_margin" in result["numeric_limits"]


@pytest.mark.parametrize("unit,period", [("EUR", "2018-12-31"), ("USD", "2016-12-31")])
def test_snapshot_growth_requires_compatible_currency_and_adjacent_annual_periods(unit, period):
    instrument, bars = inputs()
    result = snapshot(
        instrument, bars, [fact(period, 100, unit=unit), fact("2017-12-31", 200)], CLOCK
    )
    if unit == "EUR":
        assert result["revenue_growth"] is None
    else:
        # Explicitly make a two-year gap rather than comparing adjacent annual ends.
        result = snapshot(
            instrument, bars, [fact("2015-12-31", 100), fact("2017-12-31", 200)], CLOCK
        )
        assert result["revenue_growth"] is None


@pytest.mark.parametrize("case", ["return", "dollar_volume", "integer_volume"])
def test_invalid_derived_price_volume_fails_before_scoring(case):
    instrument, bars = inputs(
        1e-300 if case == "return" else 1e300,
        100 if case == "return" else 10**1000 if case == "integer_volume" else 10**20,
    )
    if case == "return":
        bars[-1] = bars[-1].model_copy(
            update={"open": 1e300, "high": 1e300, "low": 1e300, "close": 1e300}
        )
    with pytest.raises(ValueError, match="finite|Nonfinite"):
        snapshot(instrument, bars, [], CLOCK)


def test_risk_and_compounded_wealth_reject_unrepresentable_outputs():
    with pytest.raises(ValueError, match="finite|Nonfinite"):
        daily_risk(
            [{"date": "2020-01-01", "equity": 1e-300}, {"date": "2020-01-02", "equity": 1e300}]
        )
    rows = [
        {"entry": "2020-01-01", "exit": "2020-01-02", "return": 1e308},
        {"entry": "2020-01-03", "exit": "2020-01-04", "return": 1e308},
    ]
    with pytest.raises(ValueError, match="finite|Nonfinite"):
        performance(rows, "return")


def test_daily_risk_is_stable_under_large_finite_scale_changes():
    curve = [
        {"date": f"2020-01-{i + 1:02}", "equity": value}
        for i, value in enumerate([100, 110, 103, 112, 108])
    ]
    scaled = [row | {"equity": row["equity"] * 1e200} for row in curve]
    left, right = daily_risk(curve), daily_risk(scaled)
    for field in ("total_return", "max_drawdown", "annualized_volatility", "skewness"):
        assert left[field] == pytest.approx(right[field])
    json.dumps(right, allow_nan=False)
