"""Frozen-budget 5x/10x label diagnostics. Hindsight labels never enter dated ranks."""

import hashlib
import random
from datetime import UTC, date, datetime, timedelta
from typing import Any

from packages.data.finviz import _json
from packages.research.discovery import DiscoveryPolicy, ranking_snapshot
from packages.research.features import eligible, utc_asof
from packages.research.outcomes import outcome
from packages.shared.models import Dataset
from packages.shared.numeric import require_finite

VERSION = "frozen-multibagger-classification-v1"
FAMILIES = ("discovery_score", "momentum_63d", "seeded_random")
HORIZONS = (1, 2, 3, 5)
THRESHOLDS = (5, 10)


def classification_metrics(labels: list[bool | None], selected: list[int]) -> dict[str, Any]:
    if any(value is not None and type(value) is not bool for value in labels):
        raise ValueError("Classification labels must be boolean or explicitly missing")
    if len(selected) != len(set(selected)) or any(
        type(index) is not int or not 0 <= index < len(labels) for index in selected
    ):
        raise ValueError("Invalid selected classification indices")
    negatives = sum(value is False for value in labels)
    positives = sum(value is True for value in labels)
    missing = sum(value is None for value in labels)
    tp = sum(labels[index] is True for index in selected)
    fp = sum(labels[index] is False for index in selected)
    selected_missing = sum(labels[index] is None for index in selected)
    precision = tp / len(selected) if selected and not selected_missing else None
    base = positives / len(labels) if labels and not missing else None
    recall = tp / positives if positives and not missing else None
    return {
        "population": len(labels),
        "known_positives": positives,
        "unlabeled": missing,
        "selected": len(selected),
        "selected_unlabeled": selected_missing,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": positives - tp,
        "true_negatives": len(labels) - missing - positives - fp,
        "confusion_counts_basis": "KNOWN_LABELS_ONLY_UNKNOWN_NOT_FILLED",
        "false_positive_rate": fp / negatives if negatives and not missing else None,
        "precision_at_budget": precision,
        "base_rate": base,
        "recall": recall,
        "lift": precision / base
        if precision is not None and base is not None and base > 0
        else None,
        "precision_missingness_bounds": [
            tp / len(selected),
            (tp + selected_missing) / len(selected),
        ]
        if selected
        else None,
        "base_rate_missingness_bounds": [
            positives / len(labels),
            (positives + missing) / len(labels),
        ]
        if labels
        else None,
        "interpretation": "CLOSED_FIXTURE_COUNTS_NOT_PREDICTED_PROBABILITIES",
    }


def _anniversary(anchor: date, years: int) -> date:
    try:
        return anchor.replace(year=anchor.year + years)
    except ValueError:
        return anchor.replace(year=anchor.year + years, day=28)


def _pool_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels: list[bool | None] = []
    selected: list[int] = []
    for row in rows:
        offset = len(labels)
        labels.extend(item["hit"] for item in row["labels"])
        selected.extend(
            offset + index
            for index, item in enumerate(row["labels"])
            if item["security_id"] in row["selected_ids"]
        )
    return classification_metrics(labels, selected)


def _uncertainty(rows: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    # Keep complete, nonoverlapping annual anchor cohorts, chosen without reference to outcomes.
    independent = []
    previous_end = None
    for row in sorted(rows, key=lambda item: item["anchor"]):
        if row["metrics"]["unlabeled"] or (previous_end and row["anchor"] < previous_end):
            continue
        independent.append(row)
        previous_end = row["horizon_end"]
    result: dict[str, Any] = {
        "method": "NONOVERLAPPING_ANCHOR_CLUSTER_BOOTSTRAP_500",
        "nonoverlapping_complete_anchors": len(independent),
        "minimum_anchors": 5,
        "precision_interval_95": None,
        "recall_interval_95": None,
        "lift_interval_95": None,
        "status": "INSUFFICIENT_NONOVERLAPPING_COMPLETE_ANCHORS",
    }
    if len(independent) < 5:
        return result
    rng = random.Random(seed)
    samples = [_pool_metrics(rng.choices(independent, k=len(independent))) for _ in range(500)]
    result["status"] = "ILLUSTRATIVE_FIXTURE_CLUSTER_INTERVALS_NOT_EMPIRICAL_CONFIDENCE"
    for metric, field in (
        ("precision_at_budget", "precision_interval_95"),
        ("recall", "recall_interval_95"),
        ("lift", "lift_interval_95"),
    ):
        values = [sample[metric] for sample in samples]
        # Do not discard resamples with undefined recall/lift and report a favorable conditional CI.
        if all(value is not None for value in values):
            ordered = sorted(values)
            result[field] = [ordered[12], ordered[487]]
    return result


def evaluate_classification(
    dataset: Dataset, asof: datetime, policy: DiscoveryPolicy, *, seed: int = 7, budget: int = 1
) -> dict[str, Any]:
    asof = utc_asof(asof)
    policy = DiscoveryPolicy.model_validate(policy.model_dump())
    if (
        type(seed) is not int
        or not 0 <= seed < 2**32
        or type(budget) is not int
        or not 1 <= budget <= 50
    ):
        raise ValueError("Bounded integer classification seed/budget required")
    if len(dataset.instruments) > 500 or len(dataset.bars) > 1_000_000:
        raise ValueError("Fixture classification input exceeds declared bound")
    if dataset.mode != "FIXTURE" or len({i.security_id for i in dataset.instruments}) != len(
        dataset.instruments
    ):
        raise ValueError("Unique fixture instrument identities required")
    require_finite(dataset.model_dump(), "classification source")
    known_bars = [
        bar for bar in dataset.bars if bar.available_at <= asof and bar.session <= asof.date()
    ]
    sessions = sorted({bar.session for bar in known_bars})
    anchors = [
        next(day for day in sessions if day.year == year)
        for year in sorted({d.year for d in sessions})
    ]
    if len(anchors) > 64 or len(anchors) * len(dataset.instruments) > 2000:
        raise ValueError("Classification annual-anchor budget exceeded")
    if len({(bar.security_id, bar.session) for bar in known_bars}) != len(known_bars):
        raise ValueError("Duplicate classification source bars")
    known_actions = [
        action
        for action in dataset.actions
        if datetime(
            action.effective_date.year,
            action.effective_date.month,
            action.effective_date.day,
            23,
            tzinfo=UTC,
        )
        <= asof
    ]
    attempts = []
    snapshots = []
    for anchor in anchors:
        clock = datetime(anchor.year, anchor.month, anchor.day, 23, tzinfo=UTC)
        if clock > asof:
            continue
        population = sorted(
            (item for item in dataset.instruments if eligible(item, clock)),
            key=lambda item: item.security_id,
        )
        enough_history = sum(day <= anchor for day in sessions) >= 121
        features = ranking_snapshot(dataset, clock, policy) if enough_history else []
        by_id = {row["security_id"]: row for row in features}
        rankable = []
        exclusions = []
        for instrument in population:
            feature = by_id.get(instrument.security_id)
            reason = (
                "MISSING_121_SESSION_FEATURES"
                if feature is None
                else "STALE_ANCHOR_PRICE"
                if feature["price_session"] != str(anchor)
                else "BELOW_PRICE_FLOOR"
                if feature["close"] < policy.min_price
                else "BELOW_LIQUIDITY_FLOOR"
                if feature["dollar_volume_20d"] < policy.min_dollar_volume
                else None
            )
            if reason:
                exclusions.append({"security_id": instrument.security_id, "reason": reason})
            else:
                assert feature is not None
                rankable.append(feature)
        ranks = {
            "discovery_score": sorted(
                rankable, key=lambda row: (-row["score"], row["security_id"])
            ),
            "momentum_63d": sorted(
                rankable, key=lambda row: (-row["return_63d"], row["security_id"])
            ),
            "seeded_random": sorted(
                rankable,
                key=lambda row: hashlib.sha256(
                    f"{seed}:{clock.isoformat()}:{row['security_id']}".encode()
                ).hexdigest(),
            ),
        }
        # The frozen ranks are constructed before any label computation and contain no labels.
        selected = {
            family: [row["security_id"] for row in rows[:budget]] if len(rows) >= budget else []
            for family, rows in ranks.items()
        }
        snapshots.append(
            {
                "anchor": clock.isoformat(),
                "population_ids": [i.security_id for i in population],
                "rankable_ids": [f["security_id"] for f in rankable],
                "selected_ids": selected,
                "exclusions": exclusions,
                "features": [
                    {
                        key: f.get(key)
                        for key in (
                            "security_id",
                            "asof_time",
                            "price_session",
                            "close",
                            "dollar_volume_20d",
                            "score",
                            "return_63d",
                            "completeness",
                            "latest_included_publication",
                        )
                    }
                    for f in rankable
                ],
            }
        )
        for years in HORIZONS:
            end = _anniversary(anchor, years)
            mature = datetime(end.year, end.month, end.day, 23, tzinfo=UTC) <= asof
            outcomes = []
            for instrument in population:
                label: dict[str, Any] = {
                    "security_id": instrument.security_id,
                    "max_multiple": None,
                    "coverage_flag": "HORIZON_NOT_MATURED",
                }
                if mature:
                    if any(
                        bar.security_id == instrument.security_id and bar.session == anchor
                        for bar in known_bars
                    ):
                        terminal = next(
                            (
                                action.effective_date
                                for action in known_actions
                                if action.security_id == instrument.security_id
                                and action.kind == "delist"
                                and anchor < action.effective_date <= end
                            ),
                            None,
                        )
                        required_end = terminal - timedelta(days=1) if terminal else end
                        expected = set()
                        day = anchor
                        while day <= required_end:
                            if day.weekday() < 5:
                                expected.add(day)
                            day += timedelta(days=1)
                        observed = {
                            bar.session
                            for bar in known_bars
                            if bar.security_id == instrument.security_id
                        }
                        missing = len(expected - observed)
                        if missing:
                            label.update(
                                coverage_flag="MISSING_WEEKDAY_PRICE_SESSIONS",
                                missing_price_sessions=missing,
                                required_price_sessions=len(expected),
                            )
                        else:
                            label = outcome(
                                instrument.security_id, known_bars, known_actions, anchor, years
                            )
                            label.update(
                                missing_price_sessions=0, required_price_sessions=len(expected)
                            )
                    else:
                        label["coverage_flag"] = "MISSING_ANCHOR_PRICE"
                outcomes.append(label)
            for threshold in THRESHOLDS:
                labels = [
                    {
                        "security_id": row["security_id"],
                        "max_multiple": row["max_multiple"],
                        "coverage_flag": row["coverage_flag"],
                        "missing_price_sessions": row.get("missing_price_sessions"),
                        "hit": row["max_multiple"] >= threshold
                        if row["max_multiple"] is not None
                        else None,
                    }
                    for row in outcomes
                ]
                for family in FAMILIES:
                    ids = selected[family]
                    metrics = classification_metrics(
                        [row["hit"] for row in labels],
                        [index for index, row in enumerate(labels) if row["security_id"] in ids],
                    )
                    status = (
                        "HORIZON_NOT_MATURED"
                        if not mature
                        else "BUDGET_EXCEEDS_RANKABLE_POOL"
                        if not ids
                        else "PARTIAL_LABEL_COVERAGE"
                        if metrics["unlabeled"]
                        else "CALCULATED_FIXTURE_CLASSIFICATION"
                    )
                    attempts.append(
                        {
                            "anchor": str(anchor),
                            "horizon_end": str(end),
                            "horizon_years": years,
                            "threshold": threshold,
                            "family": family,
                            "budget": budget,
                            "status": status,
                            "selected_ids": ids,
                            "labels": labels,
                            "metrics": metrics,
                        }
                    )
    summaries = []
    for years in HORIZONS:
        for threshold in THRESHOLDS:
            for family in FAMILIES:
                all_rows = [
                    row
                    for row in attempts
                    if row["horizon_years"] == years
                    and row["threshold"] == threshold
                    and row["family"] == family
                ]
                evaluated = [
                    row
                    for row in all_rows
                    if row["status"]
                    in ("PARTIAL_LABEL_COVERAGE", "CALCULATED_FIXTURE_CLASSIFICATION")
                ]
                summaries.append(
                    {
                        "horizon_years": years,
                        "threshold": threshold,
                        "family": family,
                        "budget": budget,
                        "attempted_anchors": len(all_rows),
                        "evaluated_anchors": len(evaluated),
                        "metrics": _pool_metrics(evaluated),
                        "excluded_anchors": [
                            {"anchor": row["anchor"], "reason": row["status"]}
                            for row in all_rows
                            if row not in evaluated
                        ],
                        "uncertainty": _uncertainty(evaluated, seed),
                    }
                )
    report = {
        "policy": VERSION,
        "mode": dataset.mode,
        "asof": asof.isoformat(),
        "seed": seed,
        "budget": budget,
        "dataset_sha256": hashlib.sha256(dataset.model_dump_json().encode()).hexdigest(),
        "selector_policy_sha256": hashlib.sha256(_json(policy.model_dump(mode="json"))).hexdigest(),
        "snapshots": snapshots,
        "attempts": attempts,
        "summaries": summaries,
        "calibration": {
            "status": "UNAVAILABLE_RANKS_ARE_NOT_PROBABILITIES",
            "brier_score": None,
            "reliability_bins": None,
        },
        "performance_scope": "MATURE_BUDGET_FEASIBLE_ANCHORS_ALL_LISTED_COMMON_SHARES",
        "limitations": [
            "Closed artificial universe and inspected heuristic; no empirical "
            "probability or holdout claim",
            "Population denominators include every as-of listed common share, including"
            " unrankable names",
            "Selection alone applies dated discovery warmup/price/liquidity "
            "constraints; no budget reduction",
            "All 1/2/3/5Y by 5x/10x by three fixed families retained; no selected best attempt",
            "Maximum daily-close split/dividend/delist wealth is not intraday or terminal return",
            "Fixed horizons must mature for the whole cohort, even if a delist closed "
            "one name earlier",
            "Unknown outcomes remain unknown; missingness bounds are not confidence intervals",
            "Annual-anchor uncertainty requires five complete nonoverlapping cohorts; "
            "undefined resamples get no interval",
            "Rank scores are not probabilities; no fabricated calibration, p-value or FDR claim",
            "Fixture weekday calendar; 23:00 UTC horizon cutoff and at most two-day "
            "weekend price gap",
            "Action availability uses synthetic effective dates, not verified real vendor vintages",
            "Nonoverlap does not establish independence or interval coverage in real markets",
            "Every required weekday price must be observed through the horizon or known delist",
        ],
    }
    require_finite(report, "classification report")
    return report


def classification_markdown(report: dict[str, Any] | None, run_id: str) -> str:
    if report is None:
        return f"# Multibagger classification\n\nRun {run_id}: unavailable in this archive.\n"

    def percent(value: float | None) -> str:
        return "Unavailable" if value is None else f"{value:.2%}"

    lines = [
        "# FIXTURE maximum-daily-close 5x/10x classification",
        "",
        f"Run {run_id}; {report['policy']}; diagnostic clock {report['asof']}.",
        "Fixed ranks are not probabilities. All declared attempts are retained; "
        "no best model selected.",
        "",
        "| Family | Years | Multiple | Evaluated / attempted anchors | "
        "Precision | Recall | Base rate | Lift |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["summaries"]:
        metrics = row["metrics"]
        lift = metrics["lift"]
        lines.append(
            f"| {row['family']} | {row['horizon_years']} | {row['threshold']}x | "
            f"{row['evaluated_anchors']} / {row['attempted_anchors']} | "
            f"{percent(metrics['precision_at_budget'])} | {percent(metrics['recall'])} | "
            f"{percent(metrics['base_rate'])} | {lift if lift is not None else 'Unavailable'} |"
        )
    lines.extend(
        [
            "",
            "Missingness bounds are not confidence intervals. Complete nonoverlapping date cohorts "
            "are required for illustrative bootstrap intervals; "
            "see JSON for every unavailable reason.",
            "Calibration: unavailable because ranks are not probabilities.",
            "",
            "## Limitations",
            *[f"- {reason}" for reason in report["limitations"]],
        ]
    )
    return "\n".join(lines) + "\n"
