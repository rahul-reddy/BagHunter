"""Versioned full-history stages cannot advance on missing gates or hindsight."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from packages.data.fixture import fixture
from packages.research.discovery import DiscoveryPolicy, classify, discover, ranking_snapshot
from packages.research.reports import stage_history_report
from packages.research.stage_evidence import filing_inflections
from packages.shared.models import Fact


def feature(**changes):
    return {
        "eligible": True,
        "close": 102,
        "ema_21": 100,
        "ema_8": 101,
        "return_21d": 0.05,
        "relative_strength_63d": 0.02,
        "dollar_volume_20d": 2_000_000,
        "relative_volume": 1.5,
        "base_width_60d": 0.2,
        "breakout_reference": 101,
        "technical": {"base_duration_windows": 20},
        "relative_evidence": {"rank_percentile_63d": 0.8},
        "sector_breadth": 0.5,
        "filing_inflections": {
            "revenue_growth": 0.1,
            "signals": [{"kind": "a"}, {"kind": "b"}],
            "distinct_accessions": ["a", "b"],
        },
    } | changes


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "IGNITION"),
        ({"technical": {}}, "WATCH"),
        ({"technical": {"base_duration_windows": 19}}, "WATCH"),
        ({"relative_evidence": {}}, "WATCH"),
        ({"relative_evidence": {"rank_percentile_63d": 0.799}}, "WATCH"),
        ({"relative_volume": 1.49}, "WATCH"),
        ({"base_width_60d": 0.401}, "WATCH"),
        ({"close": 101}, "WATCH"),
        ({"dollar_volume_20d": 999_999}, "WATCH"),
        ({"eligible": False}, "INVALIDATED"),
        ({"close": 130}, "EXTENDED/AGING"),
    ],
)
def test_ignition_requires_every_frozen_gate(changes, expected):
    assert classify(feature(**changes), DiscoveryPolicy())[0] == expected


def test_emerging_needs_original_breakout_and_confirmation_needs_all_evidence():
    p = DiscoveryPolicy()
    assert classify(feature(relative_volume=1), p, "WATCH", 0)[0] == "WATCH"
    active = feature(trigger_reference=100, relative_volume=1)
    assert classify(active, p, "IGNITION", 1)[0] == "EMERGING"
    assert classify(active, p, "EMERGING", 3)[0] == "CONFIRMED"
    for patch in [
        {"sector_breadth": None},
        {"sector_breadth": 0.49},
        {"filing_inflections": {"signals": [{"kind": "a"}], "distinct_accessions": ["a", "b"]}},
        {
            "filing_inflections": {
                "signals": [{"kind": "a"}, {"kind": "b"}],
                "distinct_accessions": ["a"],
            }
        },
    ]:
        assert classify(active | patch, p, "EMERGING", 3)[0] == "EMERGING"
    assert classify(active | {"filing_inflections": {}}, p, "EMERGING", 3)[0] == "WATCH"
    assert (
        classify(active | {"close": 99, "dollar_volume_20d": 1}, p, "EMERGING", 3)[0]
        == "INVALIDATED"
    )
    assert (
        classify(active | {"filing_inflections": {"revenue_growth": -0.2}}, p, "CONFIRMED", 3)[0]
        == "INVALIDATED"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"breakout_lookback": 21},
        {"min_base_duration_windows": 0},
        {"min_relative_rank": 1.01},
        {"max_base_stretch": 0},
        {"min_inflection_signals": 1},
        {"min_inflection_filings": 1},
        {"invalidate_revenue_growth": 0.01},
        {"min_peer_participation": float("nan")},
    ],
)
def test_v2_policy_bounds_fail_closed(changes):
    with pytest.raises(ValidationError):
        DiscoveryPolicy(**changes)


def fact(year, metric, value, accession=None):
    return Fact(
        security_id="fixture",
        metric=metric,
        unit="USD",
        value=value,
        period_end=f"{year}-12-31",
        accepted_at=f"{year + 1}-02-01T12:00:00Z",
        published_at=f"{year + 1}-02-01T12:00:00Z",
        accession=accession or str(year),
        source_id="fictional-source",
        source_url="https://example.invalid/fictional.htm",
    )


def test_filing_signals_cite_actual_lagged_inputs_and_ignore_future_amendments():
    facts = [
        fact(2020, "annual_revenue", 100),
        fact(2021, "annual_revenue", 110),
        fact(2022, "annual_revenue", 132),
        fact(2021, "annual_operating_income", 11),
        fact(2022, "annual_operating_income", 26.4),
    ]
    clock = datetime(2023, 2, 2, 12, tzinfo=UTC)
    result = filing_inflections(facts, "fixture", clock)
    assert {s["kind"] for s in result["signals"]} == {
        "POSITIVE_REVENUE_GROWTH",
        "REVENUE_GROWTH_ACCELERATION",
        "OPERATING_MARGIN_IMPROVEMENT",
    }
    assert all(
        max(datetime.fromisoformat(c["published_at"]), datetime.fromisoformat(c["accepted_at"]))
        + timedelta(hours=24)
        <= clock
        for c in result["citations"]
    )
    future = fact(2022, "annual_revenue", 999).model_copy(
        update={
            "published_at": clock,
            "accepted_at": clock,
            "accession": "amended",
            "amended": True,
        }
    )
    assert filing_inflections(facts + [future], "fixture", clock) == result
    earlier = filing_inflections(facts, "fixture", clock - timedelta(seconds=1))
    assert "OPERATING_MARGIN_IMPROVEMENT" not in {s["kind"] for s in earlier["signals"]}
    mixed = [
        f.model_copy(update={"accession": "other"}) if f.metric == "annual_operating_income" else f
        for f in facts
    ]
    assert "OPERATING_MARGIN_IMPROVEMENT" not in {
        s["kind"] for s in filing_inflections(mixed, "fixture", clock)["signals"]
    }


def test_overflow_never_creates_a_positive_filing_inflection():
    result = filing_inflections(
        [fact(2021, "annual_revenue", 1e-300), fact(2022, "annual_revenue", 1e300)],
        "fixture",
        datetime(2024, 1, 1, tzinfo=UTC),
    )
    assert result["revenue_growth"] is None
    assert result["signals"] == []


def test_filing_period_freshness_is_bounded_and_does_not_fill_absent_evidence():
    facts = [fact(2021, "annual_revenue", 100), fact(2022, "annual_revenue", 120)]
    result = filing_inflections(facts, "fixture", datetime(2024, 1, 1, tzinfo=UTC), 365)
    assert result["status"] == "STALE_PERIOD"
    assert result["revenue_growth"] is None
    assert result["signals"] == []
    assert result["citations"] == []
    with pytest.raises(ValueError):
        filing_inflections(facts, "fixture", datetime(2024, 1, 1), 365)


def test_legacy_history_export_never_claims_full_scope():
    row = {"stage": "WATCH", "session": "2022-01-03"}
    report = stage_history_report(
        {
            "run_id": "legacy",
            "asof": "2022-01-03T23:00:00Z",
            "signals": [{"security_id": "fixture", "stage_history": [row]}],
        }
    )
    assert report["history_scope"] == "LEGACY_ARCHIVED_WINDOW"
    assert report["policy"] is None
    assert report["histories"] == {"fixture": [row]}


def test_full_history_prefix_is_independent_of_later_data_and_tracks_expired_instruments():
    data = fixture()
    sessions = sorted({b.session for b in data.bars})
    end = datetime.combine(sessions[151], datetime.min.time(), UTC).replace(hour=23)
    short = data.model_copy(update={"bars": [b for b in data.bars if b.session <= sessions[151]]})
    first = discover(short, end - timedelta(days=7), DiscoveryPolicy())
    result = discover(short, end, DiscoveryPolicy())
    ranked = ranking_snapshot(short, end, DiscoveryPolicy())
    for full, compact in zip(result["signals"], ranked, strict=True):
        for field in (
            "score",
            "components",
            "weights",
            "completeness",
            "latest_included_publication",
        ):
            assert full[field] == compact[field]
        assert not {"stage", "stage_history", "stage_reason"} & compact.keys()
    assert result["history_scope"] == "FULL_KNOWABLE_HISTORY"
    for security_id, rows in first["history"].items():
        assert [
            r
            for r in result["history"][security_id]
            if r["asof"] <= first["signals"][0]["asof_time"]
        ] == rows
    assert all(len(rows) == 32 for rows in result["history"].values())
    missing_id = short.instruments[0].security_id
    missing = short.model_copy(
        update={
            "bars": [
                b
                for b in short.bars
                if not (b.security_id == missing_id and b.session == sessions[151])
            ]
        }
    )
    incomplete = discover(missing, end, DiscoveryPolicy())
    stale = next(s for s in incomplete["signals"] if s["security_id"] == missing_id)
    assert stale["stage"] == "WATCH" and not stale["stage_history"][-1]["fresh_price"]
    assert stale["relative_evidence"]["rank_percentile_63d"] is None
    for signal in incomplete["signals"]:
        assert missing_id not in {
            r["security_id"] for r in signal["relative_evidence"]["references"]
        }
    benchmark_gap = short.model_copy(
        update={
            "bars": [
                b
                for b in short.bars
                if not (b.security_id == "fx-market" and b.session == sessions[151])
            ]
        }
    )
    without_benchmark = discover(benchmark_gap, end, DiscoveryPolicy())
    assert without_benchmark["benchmark_return_63d"] is None
    assert all(s["relative_strength_63d"] is None for s in without_benchmark["signals"])
    target = short.instruments[0]
    expired = short.model_copy(
        update={
            "instruments": [
                i.model_copy(update={"last_seen": sessions[145]})
                if i.security_id == target.security_id
                else i
                for i in short.instruments
            ]
        }
    )
    archived = discover(expired, end, DiscoveryPolicy())
    assert archived["history"][target.security_id][-1]["stage"] == "INVALIDATED"
    assert archived["history"][target.security_id][-1]["close"] is None
    assert target.security_id not in {s["security_id"] for s in archived["signals"]}


def test_replay_retains_original_trigger_and_records_exact_invalidation_reference():
    data = fixture()
    sessions = sorted({b.session for b in data.bars})[:152]
    target = data.instruments[0].security_id
    original = sorted((b for b in data.bars if b.security_id == target), key=lambda b: b.session)
    reference = max(b.high for b in original[110:130])
    prices = {
        sessions[130]: reference * 1.1,
        sessions[131]: reference * 1.08,
        sessions[132]: reference * 1.05,
        sessions[133]: reference * 0.99,
    }
    bars = []
    for bar in data.bars:
        if bar.session not in sessions:
            continue
        if bar.security_id == target and bar.session in prices:
            close = prices[bar.session]
            bar = bar.model_copy(
                update={
                    "close": close,
                    "open": close,
                    "high": close * 1.001,
                    "low": close * 0.999,
                    "volume": 100_000_000 if bar.session == sessions[130] else bar.volume,
                }
            )
        bars.append(bar)
    policy = DiscoveryPolicy(
        breakout_lookback=20,
        min_base_duration_windows=1,
        min_relative_rank=0,
        max_base_width=10,
        max_ema_stretch=100,
        max_base_stretch=100,
        min_dollar_volume=0,
    )
    end = datetime.combine(sessions[-1], datetime.min.time(), UTC).replace(hour=23)
    output = discover(data.model_copy(update={"bars": bars}), end, policy)
    history = {row["session"]: row for row in output["history"][target]}
    assert history[str(sessions[130])]["stage"] == "IGNITION"
    assert history[str(sessions[130])]["trigger_reference"] == reference
    assert history[str(sessions[132])]["evaluated_trigger_reference"] == reference
    failure = history[str(sessions[133])]
    assert failure["stage"] == "INVALIDATED"
    assert failure["evaluated_trigger_reference"] == reference
    assert failure["trigger_reference"] is None
