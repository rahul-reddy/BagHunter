"""Dated event vectors, retrospective grouping isolation and complete cohort accounting."""

import inspect
import json
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo

import pytest
from pydantic import ValidationError

from packages.data.fixture import fixture
from packages.research import event_paths
from packages.research.event_paths import (
    EventPathPolicy,
    event_report,
    event_rows,
    event_study,
    path_snapshot,
)
from packages.research.features import facts_at
from packages.research.outcomes import matched_pairs
from packages.shared.models import Fact


@pytest.fixture(scope="module")
def study():
    data = fixture()
    return data, event_study(data, EventPathPolicy())


def anchor(report, day="2020-01-01"):
    return next(a for a in report["anchors"] if a["anchor"] == day)


def member(row, sid="fx-compound"):
    return next(m for m in row["members"] if m["security_id"] == sid)


def test_declared_calendar_offsets_and_original_matching_evidence(study):
    data, report = study
    assert len(report["anchors"]) == 17 and report["points"] == 240
    row = anchor(report)
    points = member(row)["points"]
    assert [p["offset"] for p in points] == [-120, -60, -20, 0, 20]
    assert [p["point_session"] for p in points] == [
        "2019-07-17",
        "2019-10-09",
        "2019-12-04",
        "2020-01-01",
        "2020-01-29",
    ]
    assert all(p["status"] == "AVAILABLE" for p in points)
    assert points[-1]["timing"] == "POST_ANCHOR_DESCRIPTIVE_ONLY"
    assert row["eligible"] == 3 and row["cases"] == 1
    pair = row["pairs"][0]
    assert pair["case_security_id"] == "fx-compound"
    assert pair["control_security_id"] == "fx-failure"
    assert pair["control_weight"] == 1 and pair["max_hit_threshold"] == 5
    current = next(
        b for b in data.bars if b.security_id == "fx-compound" and str(b.session) == "2020-01-01"
    )
    previous = next(
        b for b in data.bars if b.security_id == "fx-compound" and str(b.session) == "2019-10-04"
    )
    assert points[3]["snapshot"]["return_63d"] == pytest.approx(current.close / previous.close - 1)


def test_all_points_respect_their_own_publication_clock_and_interface(study):
    _, report = study
    assert set(inspect.signature(path_snapshot).parameters) == {
        "instrument",
        "bars",
        "facts",
        "symbols",
        "clock",
    }
    for row in event_rows(report):
        point = row["snapshot"]
        if point is None:
            assert row["status"] != "AVAILABLE"
            continue
        assert not {"outcome", "max_multiple", "stage", "score", "outcome_group"} & point.keys()
        clock = datetime.fromisoformat(row["asof_time"])
        assert datetime.fromisoformat(point["latest_included_publication"]) <= clock
        assert datetime.fromisoformat(point["technical"]["latest_available_at"]) <= clock
        for fact in point["evidence"]:
            assert datetime.fromisoformat(fact["published_at"]) + timedelta(hours=24) <= clock
            assert datetime.fromisoformat(fact["accepted_at"]) + timedelta(hours=24) <= clock


def test_later_prices_cannot_change_pre_anchor_features(study):
    data, report = study
    changed = data.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        "close": b.close * 1.2,
                        "open": b.open * 1.2,
                        "high": b.high * 1.2,
                        "low": b.low * 1.2,
                    }
                )
                if str(b.session) > "2020-01-01"
                else b
                for b in data.bars
            ]
        }
    )
    future = event_study(changed, EventPathPolicy())
    before = member(anchor(report))["points"]
    after = member(anchor(future))["points"]
    assert after[:4] == before[:4]
    assert after[4]["snapshot"]["close"] != before[4]["snapshot"]["close"]


def test_outcome_group_changes_do_not_change_snapshot_vectors(study, monkeypatch):
    data, report = study
    original = event_paths.outcome
    monkeypatch.setattr(
        event_paths, "outcome", lambda *a, **k: original(*a, **k) | {"max_multiple": 2}
    )
    changed = event_study(data, EventPathPolicy())
    assert event_rows(changed) == event_rows(report)
    assert anchor(changed)["pairs"] == [] and anchor(report)["pairs"]


def test_missing_anchor_quote_and_late_publication_stay_missing(study):
    data, _ = study

    def change(remove):
        result = []
        for bar in data.bars:
            if bar.security_id == "fx-compound" and str(bar.session) == "2020-01-01":
                if remove:
                    continue
                bar = bar.model_copy(update={"available_at": datetime(2020, 1, 2, tzinfo=UTC)})
            result.append(bar)
        return event_study(data.model_copy(update={"bars": result}), EventPathPolicy())

    for remove in (False, True):
        selected = member(anchor(change(remove)))
        assert selected["points"][3]["status"] == "NO_QUOTE_AVAILABLE_AT_POINT"
        assert selected["points"][3]["snapshot"] is None
        if remove:
            assert selected["outcome"]["coverage_flag"] == "MISSING_ANCHOR_QUOTE"
            assert selected["outcome_group"] == "MISSING"


def test_early_history_delisted_peers_and_unmatched_cases_are_retained(study):
    data, report = study
    early = member(report["anchors"][0])["points"]
    assert early[0]["status"] == "OUTSIDE_FIXTURE_CALENDAR"
    assert early[3]["status"] == "INSUFFICIENT_PRICE_HISTORY"
    failed = member(anchor(report, "2022-04-01"), "fx-failure")
    assert failed["points"][4]["status"] == "INELIGIBLE_AT_POINT"
    assert failed["outcome"]["delisted"] is True
    assert failed["outcome"]["terminal_total_return"] == -1
    changed = data.model_copy(
        update={
            "instruments": [
                i.model_copy(update={"sector": "Other"}) if i.security_id == "fx-failure" else i
                for i in data.instruments
            ]
        }
    )
    unmatched = anchor(event_study(changed, EventPathPolicy()))
    assert unmatched["unmatched_cases"] == ["fx-compound"] and unmatched["pairs"] == []
    assert unmatched["eligible"] == 3


def test_processing_lag_and_equivalent_utc_clock(study):
    data, _ = study
    instrument = data.instruments[0]
    fact = next(
        f
        for f in data.facts
        if f.security_id == instrument.security_id and f.period_end.year == 2020
    )
    before = fact.published_at + timedelta(hours=24) - timedelta(seconds=1)
    after = before + timedelta(seconds=1)

    def get(clock):
        return path_snapshot(instrument, data.bars, data.facts, data.symbols, clock)

    assert fact.accession not in {f["accession"] for f in get(before)["evidence"]}
    assert fact.accession in {f["accession"] for f in get(after)["evidence"]}
    assert get(after) == get(after.astimezone(timezone(timedelta(hours=5))))


def test_configurable_matching_uses_actual_horizons_and_thresholds(study):
    data, _ = study
    clock = datetime(2020, 1, 1, 23, tzinfo=UTC)
    labels = [
        {"security_id": sid, "anchor": "2020-01-01", "horizon_years": 2, "max_multiple": value}
        for sid, value in [("fx-compound", 20), ("fx-failure", 19.99)]
    ]
    result = matched_pairs(
        data.instruments, labels, clock, 7, horizon_years=2, max_hit_threshold=20
    )
    assert len(result) == 1 and result[0]["horizon_years"] == 2
    assert result == matched_pairs(
        data.instruments,
        labels,
        clock.astimezone(timezone(timedelta(hours=5))),
        7,
        horizon_years=2,
        max_hit_threshold=20,
    )
    assert matched_pairs(data.instruments, labels, clock, 7) == []
    assert not any(
        a["cases"] for a in event_study(data, EventPathPolicy(max_hit_threshold=20))["anchors"]
    )
    for changes in (
        {"horizon_years": 4},
        {"max_hit_threshold": float("inf")},
        {"max_hit_threshold": 0},
    ):
        with pytest.raises(ValueError):
            matched_pairs(data.instruments, labels, clock, 7, **changes)
    with pytest.raises(ValidationError):
        EventPathPolicy(horizon_years=4)
    assert (
        EventPathPolicy().model_dump_json()
        == EventPathPolicy(max_hit_threshold=5).model_dump_json()
    )


def test_resource_and_invalid_data_boundaries_fail_closed(study, monkeypatch):
    data, _ = study
    with pytest.raises(ValueError, match="nonempty"):
        event_study(data.model_copy(update={"bars": []}), EventPathPolicy())
    weekend = data.bars[0].model_copy(update={"session": date(2019, 1, 5)})
    with pytest.raises(ValueError, match="weekend"):
        event_study(data.model_copy(update={"bars": data.bars + [weekend]}), EventPathPolicy())
    with pytest.raises(ValueError, match="32 unique"):
        event_study(
            data.model_copy(update={"instruments": data.instruments + [data.instruments[0]]}),
            EventPathPolicy(),
        )
    long = data.bars[0].model_copy(update={"session": date(1990, 1, 1)})
    with pytest.raises(ValueError, match="bounded"):
        event_study(data.model_copy(update={"bars": data.bars + [long]}), EventPathPolicy())
    limits = [
        data.bars[0].model_copy(update={"session": d}) for d in (date(2000, 1, 3), date(2016, 2, 1))
    ]
    with pytest.raises(ValueError, match="64-anchor"):
        event_study(data.model_copy(update={"bars": limits}), EventPathPolicy())
    monkeypatch.setattr(event_paths, "MAX_POINTS", 1)
    with pytest.raises(ValueError, match="point budget"):
        event_study(data, EventPathPolicy())


def test_tail_points_and_missing_horizons_are_not_omitted(study):
    data, _ = study
    truncated = data.model_copy(
        update={"bars": [b for b in data.bars if str(b.session) <= "2023-01-10"]}
    )
    row = anchor(event_study(truncated, EventPathPolicy()), "2023-01-02")
    assert row["eligible"] == row["missing_outcomes"] == 2
    assert all(m["points"][-1]["status"] == "OUTSIDE_FIXTURE_CALENDAR" for m in row["members"])


def test_markdown_is_run_bound_and_explicit_about_hindsight(study):
    _, report = study
    text = event_report(report, "test-run")
    assert "Run test-run" in text and "post-anchor descriptive hindsight" in text
    assert "fx-compound" in text and "fx-failure" in text
    assert "first public" in text and "sampling weight 1" in text
    assert "unavailable in this archive" in event_report(None, "legacy")
    assert text == event_report(json.loads(json.dumps(report, sort_keys=True)), "test-run")


class SyntheticOffsetChange(tzinfo):
    """Deterministic forward clock transition without an external timezone database."""

    def utcoffset(self, value):
        return timedelta(hours=-4 if value and value.month == 3 and value.day >= 8 else -5)

    def dst(self, value):
        return self.utcoffset(value) - timedelta(hours=-5)


def test_filing_lag_uses_elapsed_utc_hours_across_offset_changes():
    stamp = datetime(2026, 3, 7, 20, tzinfo=SyntheticOffsetChange())
    fact = Fact(
        security_id="clock-boundary",
        period_end=date(2025, 12, 31),
        accepted_at=stamp,
        published_at=stamp,
        metric="annual_revenue",
        value=1,
        unit="USD",
        accession="synthetic",
        source_id="synthetic",
        source_url="fixture://clock-boundary",
    )
    published = stamp.astimezone(UTC)
    assert facts_at([fact], "clock-boundary", published + timedelta(hours=23, minutes=59)) == []
    assert facts_at([fact], "clock-boundary", published + timedelta(hours=24)) == [fact]
    assert facts_at([fact], "clock-boundary", published + timedelta(hours=24), lag_hours=25) == []
    assert facts_at([fact], "clock-boundary", published, lag_hours=0) == [fact]


def test_repeated_local_hour_cannot_hide_invalid_fact_order():
    class RepeatedHour(tzinfo):
        def utcoffset(self, value):
            return timedelta(hours=-5 if value.fold else -4)

        def dst(self, value):
            return timedelta(0)

    zone = RepeatedHour()
    base = dict(
        security_id="clock-boundary",
        period_end=date(2025, 12, 31),
        metric="annual_revenue",
        value=1,
        unit="USD",
        source_id="synthetic",
        source_url="fixture://clock-boundary",
    )
    older = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    newer = datetime(2026, 11, 1, 1, tzinfo=zone, fold=1)
    first = Fact(**base, accepted_at=older, published_at=older, accession="older")
    latest = Fact(**base, accepted_at=newer, published_at=newer, accession="newer")
    known = facts_at([latest, first], "clock-boundary", newer.astimezone(UTC) + timedelta(hours=24))
    assert [f.accession for f in known] == ["older", "newer"]
    with pytest.raises(ValidationError, match="invalid filing timeline"):
        Fact(
            security_id="clock-boundary",
            period_end=date(2025, 12, 31),
            accepted_at=datetime(2026, 11, 1, 1, tzinfo=zone, fold=1),
            published_at=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0),
            metric="annual_revenue",
            value=1,
            unit="USD",
            accession="synthetic",
            source_id="synthetic",
            source_url="fixture://clock-boundary",
        )
