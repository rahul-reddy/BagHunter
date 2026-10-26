"""Date-local outcome permutations and predated irrelevant ranks; descriptive, never fitted."""

import hashlib
import json
import math
import random
import re
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from typing import Any

from packages.shared.numeric import require_finite


def _clock(value: str) -> datetime:
    clock = datetime.fromisoformat(value)
    if clock.utcoffset() is None:
        raise ValueError("Negative controls require aware availability clocks")
    return clock.astimezone(UTC)


def _day(value: str) -> date:
    parsed = date.fromisoformat(value)
    if str(parsed) != value:
        raise ValueError("Canonical YYYY-MM-DD dates required")
    return parsed


def negative_controls(
    windows: list[dict[str, Any]],
    asof: datetime,
    seed: int,
    *,
    permutations: int = 500,
    budget: int = 1,
    hit_threshold: float = 0,
    selector_model: str = "frozen-63d-momentum-v0",
    selector_config_sha256: str | None = None,
) -> dict[str, Any]:
    if asof.utcoffset() is None or type(seed) is not int:
        raise ValueError("Aware negative-control clock and integer seed required")
    if (
        type(permutations) is not int
        or not 20 <= permutations <= 1000
        or type(budget) is not int
        or not 1 <= budget <= 100
        or type(hit_threshold) not in (int, float)
        or not math.isfinite(hit_threshold)
        or len(windows) > 2000
        or not isinstance(selector_model, str)
        or not 1 <= len(selector_model) <= 100
        or (
            selector_config_sha256 is not None
            and not re.fullmatch(r"[a-f0-9]{64}", selector_config_sha256)
        )
    ):
        raise ValueError("Negative-control settings exceed bounds")
    asof = asof.astimezone(UTC)
    eligible = []
    excluded: dict[str, list[str]] = {"unmatured": [], "insufficient_peers": []}
    decisions: set[str] = set()
    observations = 0
    for window in sorted(windows, key=lambda w: w["decision"]):
        decision = _day(window["decision"])
        entry, exit_day = _day(window["entry"]), _day(window["exit"])
        if window["decision"] in decisions or not decision < entry <= exit_day:
            raise ValueError("Duplicate or invalid negative-control window chronology")
        decisions.add(window["decision"])
        available = _clock(window["label_available_at"])
        if available.date() < exit_day:
            raise ValueError("Outcome availability cannot precede its exit")
        if available > asof:
            excluded["unmatured"].append(window["decision"])
            continue  # Future outcomes are neither inspected nor fingerprinted.
        if not isinstance(window["candidates"], list) or any(
            not isinstance(c, dict)
            or not isinstance(c.get("security_id"), str)
            or not c["security_id"]
            for c in window["candidates"]
        ):
            raise ValueError("Missing negative-control permanent identity")
        candidates = sorted(window["candidates"], key=lambda c: c["security_id"])
        if type(window["eligible_count"]) is not int or window["eligible_count"] != len(candidates):
            raise ValueError("Incomplete decision-date candidate pool")
        observations += len(candidates)
        if observations > 20_000 or len({c["security_id"] for c in candidates}) != len(candidates):
            raise ValueError("Negative-control candidate count or identity violation")
        for candidate in candidates:
            if not isinstance(candidate["security_id"], str) or not candidate["security_id"]:
                raise ValueError("Missing negative-control permanent identity")
            if _day(candidate["identity_first_seen"]) > decision:
                raise ValueError("Negative-control identity was not known at decision")
            signal_at = _clock(candidate["signal_at"])
            publication = _clock(candidate["latest_publication"])
            if signal_at.date() != decision or publication > signal_at:
                raise ValueError("Negative-control predictor availability violation")
            if (
                type(candidate["signal_score"]) not in (int, float)
                or type(candidate["net_return"]) not in (int, float)
                or not math.isfinite(candidate["signal_score"])
                or not math.isfinite(candidate["net_return"])
                or candidate["net_return"] < -1
            ):
                raise ValueError("Invalid frozen score or matured outcome")
        if len(candidates) < max(2, budget):
            excluded["insufficient_peers"].append(window["decision"])
            continue
        eligible.append(
            {k: window[k] for k in ("decision", "entry", "exit", "label_available_at")}
            | {"candidates": candidates}
        )
    ledger = {
        "policy": "date-local-negative-controls-v1",
        "asof": asof.isoformat(),
        "seed": seed,
        "permutations": permutations,
        "budget": budget,
        "hit_threshold": hit_threshold,
        "selector_model": selector_model,
        "selector_config_sha256": selector_config_sha256,
        "windows": eligible,
        "excluded": excluded,
    }
    fingerprint = hashlib.sha256(
        json.dumps(ledger, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    details = []
    observed, irrelevant, excess, precisions, bases = [], [], [], [], []
    noise_matched_observed: list[float] = []
    noise_unavailable: list[str] = []
    positions = []
    variable_returns = variable_labels = 0
    for window in eligible:
        candidates = window["candidates"]
        ranks = sorted(
            range(len(candidates)),
            key=lambda i: (-candidates[i]["signal_score"], candidates[i]["security_id"]),
        )
        noise_at = (date.fromisoformat(window["decision"]) - timedelta(days=1)).isoformat()
        noise_ranks = sorted(
            range(len(candidates)),
            key=lambda i: hashlib.sha256(
                f"{seed}:{noise_at}:{candidates[i]['security_id']}".encode()
            ).hexdigest(),
        )
        if any(c["identity_first_seen"] > noise_at for c in candidates):
            noise_ranks = []
            noise_unavailable.append(window["decision"])
        values = [c["net_return"] for c in candidates]
        selected = ranks[:budget]
        selected_mean = mean(values[i] for i in selected)
        peer_mean = mean(values)
        observed.append(selected_mean)
        if noise_ranks:
            irrelevant.append(mean(values[i] for i in noise_ranks[:budget]))
            noise_matched_observed.append(selected_mean)
        excess.append(selected_mean - peer_mean)
        precisions.append(mean(values[i] > hit_threshold for i in selected))
        bases.append(mean(value > hit_threshold for value in values))
        variable_returns += len(set(values)) > 1
        variable_labels += len({v > hit_threshold for v in values}) > 1
        positions.append((values, selected, peer_mean))
        details.append(
            {
                "decision": window["decision"],
                "entry": window["entry"],
                "exit": window["exit"],
                "label_available_at": window["label_available_at"],
                "peers": len(candidates),
                "selected_ids": [candidates[i]["security_id"] for i in selected],
                "irrelevant_feature_at": noise_at,
                "irrelevant_selected_ids": [
                    candidates[i]["security_id"] for i in noise_ranks[:budget]
                ],
                "selected_mean_net_return": selected_mean,
                "peer_mean_net_return": peer_mean,
                "precision_at_budget": precisions[-1],
                "cross_section_base_rate": bases[-1],
            }
        )
    rng = random.Random(seed)
    null_returns, null_precision = [], []
    if eligible:
        for _ in range(permutations):
            date_excess, date_precision = [], []
            for values, selected, peer_mean in positions:
                shuffled = values.copy()
                rng.shuffle(shuffled)  # Never exchange labels across dates or split boundaries.
                date_excess.append(mean(shuffled[i] for i in selected) - peer_mean)
                date_precision.append(mean(shuffled[i] > hit_threshold for i in selected))
            null_returns.append(mean(date_excess))
            null_precision.append(mean(date_precision))

    def interval(values: list[float]) -> list[float] | None:
        ordered = sorted(values)
        return (
            [
                ordered[math.floor((len(ordered) - 1) * 0.025)],
                ordered[math.ceil((len(ordered) - 1) * 0.975)],
            ]
            if ordered
            else None
        )

    result = {
        "policy": ledger["policy"],
        "selector_model": selector_model,
        "selector_config_sha256": selector_config_sha256,
        "input_sha256": fingerprint,
        "mode": "FIXTURE",
        "status": "NO_TESTABLE_WINDOWS"
        if not eligible
        else "DEGENERATE_RETURN_NULL"
        if not variable_returns
        else "DESCRIPTIVE_NEGATIVE_CONTROLS_NOT_EMPIRICAL_VALIDATION",
        "asof": asof.isoformat(),
        "seed": seed,
        "permutations": permutations,
        "budget": budget,
        "hit_threshold_net_return": hit_threshold,
        "windows": len(eligible),
        "candidate_observations": sum(len(w["candidates"]) for w in eligible),
        "return_variable_windows": variable_returns,
        "label_variable_windows": variable_labels,
        "excluded_windows": excluded,
        "window_details": details,
        "observed": {
            "mean_selected_net_return": mean(observed) if observed else None,
            "mean_excess_versus_date_peers": mean(excess) if excess else None,
            "precision_at_budget": mean(precisions) if precisions else None,
            "date_balanced_base_rate": mean(bases) if bases else None,
        },
        "predated_irrelevant_feature": {
            "construction": "SHA-256 of seed, prior date and ID; no market inputs or labels",
            "mean_selected_net_return": mean(irrelevant) if irrelevant else None,
            "matched_frozen_mean_net_return": mean(noise_matched_observed)
            if noise_matched_observed
            else None,
            "windows": len(irrelevant),
            "identity_unavailable_dates": noise_unavailable,
        },
        "date_local_permutations": {
            "mean_excess_95_range": interval(null_returns),
            "precision_95_range": interval(null_precision),
            "null_mean_excess": mean(null_returns) if null_returns else None,
            "descriptive_upper_tail_fraction": (1 + sum(v >= mean(excess) for v in null_returns))
            / (permutations + 1)
            if null_returns
            else None,
        },
        "limitations": [
            "Frozen ranks and supplied complete same-date pools; labels never enter predictors",
            "Only matured outcomes at the diagnostic clock; no tuning or cross-date label exchange",
            "Equal weight per date; mean returns are not a portfolio wealth or CAGR simulation",
            "Null ranges and tail fractions are descriptive, not p-values or calibrated confidence",
            "Exchangeability, independence and real-market representativeness are not established",
            "Fixed fixture and rules already inspected; no untouched holdout or alpha claim",
            "Seeded irrelevant ranks are a synthetic diagnostic, not an observed economic feature",
        ],
    }
    require_finite(result, "negative-control diagnostics")
    return result
