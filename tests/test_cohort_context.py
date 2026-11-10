"""Dated industry matching and benchmark-proxy contexts cannot consume future metadata."""

from datetime import UTC, date, datetime, timedelta, timezone

import pyarrow as pa
import pytest
from pydantic import ValidationError

from packages.data.fixture import fixture
from packages.research.cohort_context import benchmark_regime, industry_at
from packages.research.outcomes import matched_pairs
from packages.shared.models import IndustryClassification

CLOCK = datetime(2020, 1, 1, 23, tzinfo=UTC)


@pytest.fixture(scope="module")
def source():
    return fixture()


def classification(**changes):
    return IndustryClassification(
        **{
            "security_id": "fx-compound",
            "industry": "Fixture parts",
            "industry_version": "v1",
            "valid_from": date(2019, 1, 1),
            "published_at": datetime(2019, 1, 1, tzinfo=UTC),
            "source_id": "fixture-source",
            **changes,
        }
    )


def labels():
    return [
        {"security_id": sid, "anchor": "2020-01-01", "horizon_years": 1, "max_multiple": value}
        for sid, value in [("fx-compound", 6), ("fx-failure", 1), ("fx-steady", 1)]
    ]


def test_industry_requires_publication_and_half_open_validity_without_period_backdating():
    row = classification(published_at=CLOCK + timedelta(seconds=1), valid_to=date(2021, 1, 1))
    assert industry_at([row], row.security_id, CLOCK)["industry"] is None
    after = industry_at([row], row.security_id, CLOCK + timedelta(seconds=1))
    assert (
        after["industry"] == "Fixture parts"
        and after["latest_publication"] == row.published_at.isoformat()
    )
    assert industry_at([row], row.security_id, datetime(2021, 1, 1, tzinfo=UTC))["industry"] is None
    assert after == industry_at(
        [row],
        row.security_id,
        (CLOCK + timedelta(seconds=1)).astimezone(timezone(timedelta(hours=5))),
    )


def test_immutable_revisions_future_rows_and_order_leave_past_classification_unchanged():
    old = classification()
    revised = classification(
        industry="Newer classification", published_at=datetime(2021, 1, 1, tzinfo=UTC)
    )
    past = industry_at([old], old.security_id, CLOCK)
    assert industry_at([revised, old], old.security_id, CLOCK) == past
    later = datetime(2022, 1, 1, tzinfo=UTC)
    assert industry_at([old, revised], old.security_id, later)["industry"] == revised.industry
    assert industry_at([old, revised], old.security_id, later) == industry_at(
        [revised, old], old.security_id, later
    )


def test_conflicting_sources_and_overlapping_classes_remain_ambiguous():
    rows = [classification(), classification(industry="Conflicting", source_id="another-source")]
    context = industry_at(rows, "fx-compound", CLOCK)
    assert context["status"] == "AMBIGUOUS_KNOWN_CLASSIFICATION" and context["industry"] is None
    overlapping = classification(industry="Overlapping", valid_from=date(2019, 6, 1))
    assert industry_at([rows[0], overlapping], "fx-compound", CLOCK)["industry"] is None


def test_matching_uses_dated_industry_instead_of_current_sector_and_records_legacy_proxy(source):
    history = [
        classification(),
        classification(security_id="fx-failure", industry="Wrong industry"),
        classification(security_id="fx-steady"),
    ]
    pairs = matched_pairs(source.instruments, labels(), CLOCK, 7, industry_history=history)
    assert len(pairs) == 1 and pairs[0]["control_security_id"] == "fx-steady"
    assert pairs[0]["matching_basis"] == "DATED_INDUSTRY_METADATA"
    assert pa.Table.from_pylist(pairs).num_rows == 1
    assert all(isinstance(value, str) for value in pairs[0]["strata"])
    assert pairs[0]["control_sampling_probability"] == 1
    assert pairs[0]["case_industry_context"]["latest_publication"] <= CLOCK.isoformat()
    assert pairs == matched_pairs(
        list(reversed(source.instruments)),
        list(reversed(labels())),
        CLOCK,
        7,
        industry_history=list(reversed(history)),
    )
    legacy = matched_pairs(source.instruments, labels(), CLOCK, 7)
    assert legacy[0]["control_security_id"] == "fx-failure"
    assert legacy[0]["matching_basis"] == "EXPLICIT_SECTOR_PROXY"


def test_missing_ambiguous_and_future_industry_are_not_promoted_into_matches(source):
    case = classification()
    assert matched_pairs(source.instruments, labels(), CLOCK, 7, industry_history=[case]) == []
    conflicting = classification(industry="Conflict", source_id="conflict")
    assert (
        matched_pairs(source.instruments, labels(), CLOCK, 7, industry_history=[case, conflicting])
        == []
    )
    baseline = source.industry_history
    future = classification(
        security_id="fx-failure", industry="Future", published_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert matched_pairs(
        source.instruments, labels(), CLOCK, 7, industry_history=baseline
    ) == matched_pairs(source.instruments, labels(), CLOCK, 7, industry_history=[future, *baseline])


@pytest.mark.parametrize(
    "changes",
    [
        {"published_at": datetime(2020, 1, 1)},
        {"valid_to": date(2019, 1, 1)},
        {"industry": " "},
        {"industry_version": " v1"},
    ],
)
def test_invalid_industry_clocks_intervals_and_labels_reject(changes):
    with pytest.raises(ValidationError):
        classification(**changes)


@pytest.mark.parametrize("change,tag", [(-0.1, "DOWN_63D"), (0, "FLAT_63D"), (0.1, "UP_63D")])
def test_benchmark_proxy_has_hand_calculated_return_and_known_input_clock(source, change, tag):
    known = sorted(
        [b for b in source.bars if b.security_id == "fx-market" and b.session <= CLOCK.date()],
        key=lambda b: b.session,
    )[-64:]
    prices = {bar.session: 100 * (1 + change) if i == 63 else 100 for i, bar in enumerate(known)}
    bars = [
        bar.model_copy(
            update={
                "open": prices[bar.session],
                "high": prices[bar.session],
                "low": prices[bar.session],
                "close": prices[bar.session],
            }
        )
        if bar.security_id == "fx-market" and bar.session in prices
        else bar
        for bar in source.bars
    ]
    context = benchmark_regime(source.model_copy(update={"bars": bars}), CLOCK)
    assert context["return_63d"] == pytest.approx(change) and context["regime"] == tag
    assert context["latest_publication"] <= CLOCK.isoformat()
    assert "NOT_MACRO_REGIME" in context["scope"]


def test_future_prices_future_benchmark_and_input_order_do_not_change_dated_context(source):
    baseline = benchmark_regime(source, CLOCK)
    future = source.bars[-1].model_copy(
        update={
            "security_id": "fx-market",
            "session": date(2030, 1, 1),
            "available_at": datetime(2030, 1, 1, 23, tzinfo=UTC),
            "close": 1e100,
        }
    )
    benchmark = next(i for i in source.instruments if i.security_type == "benchmark")
    future_master = benchmark.model_copy(
        update={"security_id": "future-benchmark", "first_seen": date(2027, 1, 1)}
    )
    changed = source.model_copy(
        update={
            "bars": [future, *reversed(source.bars)],
            "instruments": [future_master, *source.instruments],
        }
    )
    assert benchmark_regime(changed, CLOCK) == baseline


@pytest.mark.parametrize("mutation", ["missing_anchor", "missing_interior", "short", "ambiguous"])
def test_missing_or_ambiguous_benchmark_never_becomes_flat_or_zero(source, mutation):
    known = sorted(
        [b for b in source.bars if b.security_id == "fx-market" and b.session <= CLOCK.date()],
        key=lambda b: b.session,
    )
    missing = known[-1].session if mutation == "missing_anchor" else known[-10].session
    bars = [
        b
        for b in source.bars
        if b.security_id != "fx-market"
        or (b.session != missing and (mutation != "short" or b.session >= known[-10].session))
    ]
    instruments = source.instruments
    if mutation == "ambiguous":
        benchmark = next(i for i in source.instruments if i.security_type == "benchmark")
        instruments = [
            *instruments,
            benchmark.model_copy(update={"security_id": "second-benchmark"}),
        ]
    result = benchmark_regime(
        source.model_copy(update={"bars": bars, "instruments": instruments}), CLOCK
    )
    assert result["regime"] == "UNAVAILABLE" and result["return_63d"] is None


def test_duplicate_known_benchmark_and_invalid_matching_labels_reject(source):
    known = next(
        b for b in source.bars if b.security_id == "fx-market" and b.session == CLOCK.date()
    )
    with pytest.raises(ValueError, match="Duplicate"):
        benchmark_regime(source.model_copy(update={"bars": [*source.bars, known]}), CLOCK)
    for rows in [
        [*labels(), labels()[0]],
        [{**labels()[0], "max_multiple": float("nan")}],
        [{**labels()[0], "max_multiple": True}],
    ]:
        with pytest.raises(ValueError):
            matched_pairs(source.instruments, rows, CLOCK, 7)


def test_cohort_grid_retains_dated_industry_and_benchmark_context_separate_from_outcomes(source):
    from packages.research.cohorts import cohort_grid

    report = cohort_grid(source)
    assert report["labels"] and all(
        "benchmark_context" in row and "industry_context" in row for row in report["labels"]
    )
    row = next(
        r
        for r in report["labels"]
        if r["anchor"] == "2020-01-01" and r["security_id"] == "fx-compound"
    )
    assert row["industry_asof"] == "Fixture industrial components"
    assert row["industry_context"]["latest_publication"] <= "2020-01-01T23:00:00+00:00"
    assert row["benchmark_context"] == benchmark_regime(source, CLOCK)
    assert row["regime"] == row["benchmark_context"]["regime"]
