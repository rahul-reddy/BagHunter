"""Frozen date-safe diagnostic boundaries, not empirical strategy evidence."""

import copy
import json
from datetime import UTC, datetime

import pytest

from packages.backtest.negative_controls import negative_controls

CLOCK = datetime(2023, 5, 1, tzinfo=UTC)


def window(day="2023-01-01", entry="2023-01-02", exit_day="2023-02-01"):
    return {
        "decision": day,
        "entry": entry,
        "exit": exit_day,
        "label_available_at": exit_day + "T23:00:00Z",
        "eligible_count": 3,
        "candidates": [
            {
                "security_id": f"fixture-{i}",
                "identity_first_seen": "2010-01-01",
                "signal_score": 3 - i,
                "signal_at": day + "T23:00:00Z",
                "latest_publication": day + "T22:00:00Z",
                "net_return": value,
            }
            for i, value in enumerate((0.3, 0.1, -0.1))
        ],
    }


def run(windows, **settings):
    return negative_controls(windows, CLOCK, 7, permutations=100, **settings)


def test_permutations_are_reproducible_date_local_and_inputs_remain_frozen():
    windows = [window(), window("2023-02-10", "2023-02-11", "2023-03-10")]
    for candidate in windows[1]["candidates"]:
        candidate["net_return"] += 0.5
    original = copy.deepcopy(windows)
    result = run(windows)
    assert result == run(list(reversed(windows)))
    assert result["observed"]["mean_selected_net_return"] == pytest.approx(0.55)
    assert result["observed"]["mean_excess_versus_date_peers"] == pytest.approx(0.2)
    assert result["candidate_observations"] == 6 and result["windows"] == 2
    assert result["observed"]["precision_at_budget"] == 1
    assert result["observed"]["date_balanced_base_rate"] == pytest.approx(5 / 6)
    assert result["date_local_permutations"]["mean_excess_95_range"][0] >= -0.2 - 1e-12
    assert result["date_local_permutations"]["mean_excess_95_range"][1] <= 0.2 + 1e-12
    assert windows == original
    json.dumps(result, allow_nan=False)
    for row in result["window_details"]:
        assert row["irrelevant_feature_at"] < row["decision"] < row["entry"] <= row["exit"]


def test_reordered_candidate_pools_and_future_label_changes_cannot_change_frozen_ranks():
    original = window()
    changed = copy.deepcopy(original)
    changed["candidates"].reverse()
    assert run([original]) == run([changed])
    for candidate in changed["candidates"]:
        candidate["net_return"] = -candidate["net_return"]
    before, after = run([original]), run([changed])
    assert before["window_details"][0]["selected_ids"] == after["window_details"][0]["selected_ids"]
    assert (
        before["window_details"][0]["irrelevant_selected_ids"]
        == after["window_details"][0]["irrelevant_selected_ids"]
    )
    assert before["observed"] != after["observed"]
    future = window("2023-06-01", "2023-06-02", "2023-07-01")
    baseline = run([original, future])
    future["candidates"] = [{"secret_future_label": "MUST NOT BE INSPECTED"}]
    assert baseline == run([original, future])
    assert baseline["excluded_windows"]["unmatured"] == ["2023-06-01"]


@pytest.mark.parametrize(
    "change",
    [
        "future_predictor",
        "naive",
        "duplicate_id",
        "missing_peer",
        "nonfinite_score",
        "missing_outcome",
        "loss_below_capital",
        "date",
        "premature_outcome",
        "duplicate_date",
    ],
)
def test_invalid_availability_coverage_or_numeric_data_rejects(change):
    item = window()
    rows = [item]
    first = item["candidates"][0]
    if change == "future_predictor":
        first["latest_publication"] = "2023-01-02T00:00:00Z"
    if change == "naive":
        first["signal_at"] = "2023-01-01T23:00:00"
    if change == "duplicate_id":
        first["security_id"] = "fixture-1"
    if change == "missing_peer":
        item["candidates"].pop()
    if change == "nonfinite_score":
        first["signal_score"] = float("inf")
    if change == "missing_outcome":
        first["net_return"] = None
    if change == "loss_below_capital":
        first["net_return"] = -1.01
    if change == "date":
        item["entry"] = item["decision"]
    if change == "premature_outcome":
        item["label_available_at"] = "2023-01-20T00:00:00Z"
    if change == "duplicate_date":
        rows *= 2
    with pytest.raises(ValueError):
        run(rows)


def test_empty_thin_and_degenerate_pools_are_explicit_and_budget_is_not_lowered():
    assert run([])["status"] == "NO_TESTABLE_WINDOWS"
    thin = window()
    thin["candidates"] = thin["candidates"][:1]
    thin["eligible_count"] = 1
    result = run([thin])
    assert result["windows"] == 0 and result["observed"]["precision_at_budget"] is None
    assert result["excluded_windows"]["insufficient_peers"] == [thin["decision"]]
    assert run([window()], budget=4)["windows"] == 0
    flat = window()
    for candidate in flat["candidates"]:
        candidate["net_return"] = 0.1
    result = run([flat])
    assert result["status"] == "DEGENERATE_RETURN_NULL"
    assert result["date_local_permutations"]["mean_excess_95_range"] == [0, 0]
    assert result["label_variable_windows"] == 0


def test_predated_noise_requires_identity_known_on_prior_date_and_clock_maturity():
    item = window()
    item["candidates"][0]["identity_first_seen"] = item["decision"]
    result = run([item])
    assert result["windows"] == 1
    assert result["predated_irrelevant_feature"]["windows"] == 0
    assert result["predated_irrelevant_feature"]["mean_selected_net_return"] is None
    assert result["predated_irrelevant_feature"]["identity_unavailable_dates"] == [item["decision"]]
    item["candidates"][0]["identity_first_seen"] = "2023-01-02"
    with pytest.raises(ValueError, match="identity was not known"):
        run([item])
    item = window()
    before = negative_controls([item], datetime(2023, 2, 1, 22, 59, tzinfo=UTC), 7)
    at = negative_controls([item], datetime(2023, 2, 1, 23, tzinfo=UTC), 7)
    assert before["windows"] == 0 and at["windows"] == 1


@pytest.mark.parametrize(
    "settings",
    [
        {"permutations": 19},
        {"permutations": 1001},
        {"budget": True},
        {"hit_threshold": float("nan")},
    ],
)
def test_bounded_settings(settings):
    with pytest.raises(ValueError):
        negative_controls([window()], CLOCK, 7, **settings)


def test_input_resource_bounds_and_noncanonical_dates_reject():
    with pytest.raises(ValueError, match="settings exceed"):
        run([window()] * 2001)
    item = window()
    item["candidates"] *= 7000
    item["eligible_count"] = len(item["candidates"])
    with pytest.raises(ValueError, match="candidate count"):
        run([item])
    item = window()
    item["decision"] = "20230101"
    with pytest.raises(ValueError, match="Canonical"):
        run([item])
