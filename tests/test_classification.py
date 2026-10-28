"""Independent confusion counts, mature horizons, frozen ranks and missing-label boundaries."""

import importlib
from datetime import UTC, date, datetime

import pytest

from packages.backtest.classification import (
    _uncertainty,
    classification_metrics,
    evaluate_classification,
)
from packages.data.fixture import fixture
from packages.pipeline import DEFAULT_ASOF
from packages.research.discovery import DiscoveryPolicy


@pytest.fixture(scope="module")
def source():
    return fixture()


@pytest.fixture(scope="module")
def report(source):
    return evaluate_classification(source, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy())


def test_independent_confusion_counts_and_undefined_denominators():
    value = classification_metrics([True, False, True, False], [0, 1])
    assert [
        value[key]
        for key in ("true_positives", "false_positives", "false_negatives", "true_negatives")
    ] == [1, 1, 1, 1]
    assert value["precision_at_budget"] == value["recall"] == value["base_rate"] == 0.5
    assert value["lift"] == 1 and value["false_positive_rate"] == 0.5
    empty_positive = classification_metrics([False, False], [0])
    assert empty_positive["precision_at_budget"] == empty_positive["base_rate"] == 0
    assert empty_positive["recall"] is None and empty_positive["lift"] is None
    assert classification_metrics([], [])["precision_at_budget"] is None
    missing = classification_metrics([True, None, False], [0, 1])
    assert missing["precision_at_budget"] is None and missing["recall"] is None
    assert missing["base_rate"] is None and missing["lift"] is None
    assert missing["precision_missingness_bounds"] == [0.5, 1]
    assert missing["base_rate_missingness_bounds"] == [1 / 3, 2 / 3]
    assert missing["confusion_counts_basis"] == "KNOWN_LABELS_ONLY_UNKNOWN_NOT_FILLED"


@pytest.mark.parametrize(
    "labels,selected",
    [([1], [0]), ([True], [True]), ([True], [0, 0]), ([True], [-1]), ([True], [1])],
)
def test_invalid_labels_or_selection_cannot_be_counted(labels, selected):
    with pytest.raises(ValueError):
        classification_metrics(labels, selected)


def test_all_declared_horizon_threshold_family_attempts_are_retained(report):
    assert len(report["snapshots"]) == 4
    assert len(report["attempts"]) == 4 * 4 * 2 * 3
    assert len(report["summaries"]) == 4 * 2 * 3
    assert report["calibration"]["status"] == "UNAVAILABLE_RANKS_ARE_NOT_PROBABILITIES"
    assert report["calibration"]["brier_score"] is None
    for point in report["snapshots"]:
        assert "fx-market" not in point["population_ids"]
        for feature in point["features"]:
            assert feature["asof_time"] == point["anchor"]
            assert feature["price_session"] == point["anchor"][:10]
            assert feature["latest_included_publication"] <= point["anchor"]
    for row in report["attempts"]:
        assert row["metrics"]["population"] == len(row["labels"])
        if row["status"] == "HORIZON_NOT_MATURED":
            assert all(
                label["hit"] is None and label["max_multiple"] is None for label in row["labels"]
            )
        if row["anchor"] == "2019-01-01":
            assert row["selected_ids"] == []  # No silent warmup or lower-budget fallback.
    assert all(
        summary["uncertainty"]["precision_interval_95"] is None for summary in report["summaries"]
    )


def test_future_bars_and_future_identity_cannot_change_known_predictions_or_labels(source, report):
    cutoff = datetime.fromisoformat(DEFAULT_ASOF)
    future = [
        bar.model_copy(
            update={
                "open": bar.open * 2,
                "close": bar.close * 2,
                "high": bar.high * 2,
                "low": bar.low * 2,
            }
        )
        if bar.available_at > cutoff
        else bar
        for bar in source.bars
    ]
    extra = source.instruments[0].model_copy(
        update={"security_id": "future-id", "first_seen": date(2025, 1, 1)}
    )
    changed = evaluate_classification(
        source.model_copy(update={"bars": future, "instruments": [*source.instruments, extra]}),
        cutoff,
        DiscoveryPolicy(),
    )
    assert changed["snapshots"] == report["snapshots"]
    assert changed["attempts"] == report["attempts"]
    assert changed["dataset_sha256"] != report["dataset_sha256"]


def test_labels_never_enter_rank_construction_and_input_order_does_not_choose_ties(
    source, report, monkeypatch
):
    module = importlib.import_module("packages.backtest.classification")
    original = module.outcome

    def changed_outcome(*args):
        return original(*args) | {"max_multiple": 100.0}

    monkeypatch.setattr(module, "outcome", changed_outcome)
    altered = evaluate_classification(
        source, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy()
    )
    assert altered["snapshots"] == report["snapshots"]
    assert altered["attempts"] != report["attempts"]
    monkeypatch.setattr(module, "outcome", original)
    reordered = source.model_copy(
        update={
            name: list(reversed(getattr(source, name)))
            for name in ("instruments", "bars", "facts", "actions", "symbols")
        }
    )
    assert (
        evaluate_classification(reordered, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy())[
            "attempts"
        ]
        == report["attempts"]
    )


def test_missing_outcome_and_budget_are_not_filled_or_dropped(source):
    modified = source.model_copy(
        update={
            "bars": [
                bar
                for bar in source.bars
                if bar.security_id != "fx-steady" or bar.session <= date(2020, 1, 31)
            ]
        }
    )
    result = evaluate_classification(
        modified, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy()
    )
    partial = [row for row in result["attempts"] if row["status"] == "PARTIAL_LABEL_COVERAGE"]
    assert partial and all(row["metrics"]["base_rate"] is None for row in partial)
    assert all(
        any(label["security_id"] == "fx-steady" and label["hit"] is None for label in row["labels"])
        for row in partial
    )
    too_many = evaluate_classification(
        source, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy(), budget=4
    )
    assert all(row["selected_ids"] == [] for row in too_many["attempts"])
    assert all(row["metrics"]["precision_at_budget"] is None for row in too_many["attempts"])


def test_whole_horizon_must_mature_even_for_earlier_known_delist(source):
    clock = datetime(2022, 5, 1, 23, tzinfo=UTC)
    result = evaluate_classification(source, clock, DiscoveryPolicy())
    row = next(
        row
        for row in result["attempts"]
        if row["anchor"] == "2021-01-01" and row["horizon_years"] == 2
    )
    assert row["status"] == "HORIZON_NOT_MATURED"
    assert (
        next(label for label in row["labels"] if label["security_id"] == "fx-failure")["hit"]
        is None
    )


def test_conservative_horizon_clock_and_equivalent_timezones(source):
    before = evaluate_classification(
        source, datetime(2021, 1, 1, 22, 59, 59, tzinfo=UTC), DiscoveryPolicy()
    )
    after = evaluate_classification(source, datetime(2021, 1, 1, 23, tzinfo=UTC), DiscoveryPolicy())

    def choose(report):
        return next(
            row
            for row in report["attempts"]
            if row["anchor"] == "2020-01-01" and row["horizon_years"] == 1
        )

    assert choose(before)["status"] == "HORIZON_NOT_MATURED"
    assert choose(after)["status"] == "CALCULATED_FIXTURE_CLASSIFICATION"
    equivalent = evaluate_classification(
        source, datetime.fromisoformat("2021-01-02T00:00:00+01:00"), DiscoveryPolicy()
    )
    assert after == equivalent


@pytest.mark.parametrize(
    "settings", [{"seed": -1}, {"seed": True}, {"budget": 0}, {"budget": 51}, {"budget": True}]
)
def test_declared_settings_are_bounded(source, settings):
    with pytest.raises(ValueError, match="Bounded integer"):
        evaluate_classification(
            source, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy(), **settings
        )


def test_duplicate_instruments_and_known_bars_are_invalid_not_double_weighted(source):
    for changed in [
        source.model_copy(update={"instruments": [*source.instruments, source.instruments[0]]}),
        source.model_copy(update={"bars": [*source.bars, source.bars[0]]}),
    ]:
        with pytest.raises(ValueError, match="identities|Duplicate"):
            evaluate_classification(
                changed, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy()
            )


def test_intervals_require_complete_nonoverlapping_clusters_and_no_undefined_resample_filtering():
    rows = []
    for year in range(2010, 2016):
        labels = [{"security_id": "one", "hit": True}, {"security_id": "two", "hit": False}]
        rows.append(
            {
                "anchor": f"{year}-01-01",
                "horizon_end": f"{year + 1}-01-01",
                "labels": labels,
                "selected_ids": ["one"],
                "metrics": classification_metrics([True, False], [0]),
            }
        )
    result = _uncertainty(rows, 7)
    assert result == _uncertainty(rows, 7)
    assert result["precision_interval_95"] == [1, 1]
    assert result["recall_interval_95"] == [1, 1] and result["lift_interval_95"] == [2, 2]
    overlap = [row | {"horizon_end": f"{int(row['anchor'][:4]) + 3}-01-01"} for row in rows]
    assert _uncertainty(overlap, 7)["precision_interval_95"] is None
    all_negative = [
        row
        | {
            "labels": [dict(item, hit=False) for item in row["labels"]],
            "metrics": classification_metrics([False, False], [0]),
        }
        for row in rows
    ]
    null = _uncertainty(all_negative, 7)
    assert null["precision_interval_95"] == [0, 0]
    assert null["recall_interval_95"] is None and null["lift_interval_95"] is None


@pytest.mark.parametrize("missing_day", [date(2020, 6, 1), date(2021, 1, 1)])
def test_one_missing_interior_or_terminal_weekday_is_not_a_complete_maximum_label(
    source, missing_day
):
    changed = source.model_copy(
        update={
            "bars": [
                bar
                for bar in source.bars
                if not (bar.security_id == "fx-compound" and bar.session == missing_day)
            ]
        }
    )
    report = evaluate_classification(
        changed, datetime.fromisoformat(DEFAULT_ASOF), DiscoveryPolicy()
    )
    row = next(
        row
        for row in report["attempts"]
        if row["anchor"] == "2020-01-01" and row["horizon_years"] == 1
    )
    label = next(label for label in row["labels"] if label["security_id"] == "fx-compound")
    assert label["hit"] is None and label["coverage_flag"] == "MISSING_WEEKDAY_PRICE_SESSIONS"
    assert label["missing_price_sessions"] == 1
