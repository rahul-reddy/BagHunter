"""Independent arithmetic, publication boundaries and proxy denominators."""

import math
from datetime import UTC, datetime, timedelta, timezone
from statistics import pstdev

import pytest

from packages.research.technical import cross_section_evidence, technical_evidence, technical_report
from packages.shared.models import Bar

CLOCK = datetime(2022, 1, 1, 23, tzinfo=UTC)


def bars(closes):
    start = CLOCK - timedelta(days=len(closes) - 1)
    return [
        Bar(
            security_id="a",
            session=(start + timedelta(days=i)).date(),
            available_at=start + timedelta(days=i),
            open=c,
            close=c,
            high=c,
            low=c,
            volume=1000,
            source_id="synthetic-technical",
        )
        for i, c in enumerate(closes)
    ]


def test_exact_returns_highs_gaps_and_atr():
    history = bars([100 + i for i in range(120)] + [300])
    result = technical_evidence(history, "a", CLOCK)
    returns = [b.close / a.close - 1 for a, b in zip(history[:-1], history[1:], strict=True)]
    assert result["volatility_20d"] == pytest.approx(pstdev(returns[-20:]) * math.sqrt(252))
    assert result["volatility_60d"] == pytest.approx(pstdev(returns[-60:]) * math.sqrt(252))
    assert result["volatility_contraction"] == pytest.approx(
        pstdev(returns[-20:]) / pstdev(returns[-60:])
    )
    for n in (20, 60, 120):
        assert result[f"high_{n}_prior"] == 219
        assert result[f"distance_high_{n}"] == pytest.approx(300 / 219 - 1)
        assert result[f"breakout_{n}"] is True
    assert result["gap_open"] == pytest.approx(300 / 219 - 1)
    assert result["mean_absolute_gap_20d"] == pytest.approx(sum(abs(r) for r in returns[-20:]) / 20)
    assert result["atr_20"] == 5
    assert result["sma_200"] is None
    assert {r["field"]: r["reason"] for r in result["missing"]}[
        "sma_200"
    ] == "INSUFFICIENT_AVAILABLE_HISTORY"


def test_available_history_only_and_utc_clock():
    history = bars([100.0] * 61)
    expected = technical_evidence(history, "a", CLOCK)
    later = history[-1].model_copy(update={"session": (CLOCK + timedelta(days=1)).date()})
    delayed = history[-1].model_copy(update={"available_at": CLOCK + timedelta(seconds=1)})
    other = history[-1].model_copy(update={"security_id": "other"})
    assert technical_evidence(history + [later, delayed, other], "a", CLOCK) == expected
    assert (
        technical_evidence(history, "a", CLOCK.astimezone(timezone(timedelta(hours=5)))) == expected
    )
    assert expected["volatility_60d"] == 0
    assert expected["volatility_contraction"] is None
    assert {r["field"]: r["reason"] for r in expected["missing"]}[
        "volatility_contraction"
    ] == "ZERO_60D_REFERENCE_VOLATILITY"


@pytest.mark.parametrize("count", [0, 1, 20, 21, 60, 61, 120, 121, 200])
def test_minimum_history_is_explicit(count):
    result = technical_evidence(bars([10.0] * count), "a", CLOCK)
    assert (result["volatility_20d"] is not None) == (count >= 21)
    assert (result["volatility_60d"] is not None) == (count >= 61)
    assert (result["high_120_prior"] is not None) == (count >= 121)
    assert (result["sma_200"] is not None) == (count >= 200)
    assert (result["base_duration_windows"] is not None) == (count >= 21)
    if count >= 21:
        assert result["breakout_20"] is False


def test_contraction_and_base_duration_bounds():
    contraction = technical_evidence(
        bars([100.0 + i % 2 * 10 for i in range(40)] + [100.0] * 21), "a", CLOCK
    )
    assert contraction["volatility_contraction"] == 0
    result = technical_evidence(bars([100.0] * 400), "a", CLOCK)
    assert result["base_duration_windows"] == 252
    assert result["base_left_censored"] is True
    result = technical_evidence(bars([50.0] + [100.0] * 24), "a", CLOCK)
    assert result["base_duration_windows"] == 4
    assert result["base_left_censored"] is False
    result = technical_evidence(bars([50.0] + [100.0] * 20), "a", CLOCK)
    assert result["base_duration_windows"] == 0
    assert result["base_left_censored"] is False


def test_reject_ambiguous_history_and_numeric_overflow():
    history = bars([10.0] * 21)
    with pytest.raises(ValueError, match="Duplicate"):
        technical_evidence(history + history[:1], "a", CLOCK)
    with pytest.raises(ValueError, match="Aware"):
        technical_evidence(history, "a", CLOCK.replace(tzinfo=None))
    with pytest.raises(ValueError):
        technical_evidence(bars([1e-300, 1e300]), "a", CLOCK)
    with pytest.raises(ValueError):
        technical_evidence(history, "a", CLOCK, float("nan"))


def test_rank_ties_peer_exclusion_and_proxy_missingness():
    signals = [
        {"security_id": "a", "sector": "x", "return_63d": 0.1, "return_21d": 0.1},
        {"security_id": "b", "sector": "x", "return_63d": 0.3, "return_21d": -0.1},
        {"security_id": "c", "sector": "y", "return_63d": 0.3, "return_21d": 0.2},
    ]
    result = cross_section_evidence(signals)
    assert result == cross_section_evidence(list(reversed(signals)))
    assert "relative_evidence" not in signals[0]
    assert result["a"]["rank_percentile_63d"] == 0
    assert result["b"]["rank_percentile_63d"] == 0.75
    assert result["a"]["sector_rank_percentile_63d"] == 0
    assert result["b"]["sector_rank_percentile_63d"] == 1
    assert result["a"]["sector_relative_63d"] == pytest.approx(-0.2)
    assert result["a"]["sector_participation_21d"] == 0.5
    assert result["a"]["sector_dispersion_63d"] == pytest.approx(0.1)
    for name in (
        "sector_rank_percentile_63d",
        "sector_relative_63d",
        "sector_dispersion_63d",
        "sector_participation_21d",
    ):
        assert result["c"][name] is None
    assert cross_section_evidence([signals[0]])["a"]["rank_percentile_63d"] is None
    assert cross_section_evidence([signals[0] | {"sector": ""}])["a"]["sector_count"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        cross_section_evidence([signals[0], signals[0]])
    with pytest.raises(ValueError):
        cross_section_evidence([signals[0] | {"return_63d": float("inf")}])


def test_legacy_report_does_not_recalculate():
    minimal = technical_report({"run_id": "old", "mode": "FIXTURE", "signals": []})
    assert minimal["asof"] is None and minimal["signals"] == []
    assert technical_report(
        {"run_id": "old", "asof": "old", "mode": "FIXTURE", "signals": [{"security_id": "a"}]}
    )["signals"] == [{"security_id": "a", "technical": None, "relative_evidence": None}]
