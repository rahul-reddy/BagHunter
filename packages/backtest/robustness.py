"""Predeclared failure-oriented fixture stresses; retain failures, never choose a winner."""

import hashlib
import json
import math
from collections import defaultdict
from typing import Any

from packages.backtest.constrained import PortfolioPolicy, simulate
from packages.shared.models import Dataset
from packages.shared.numeric import require_finite

POLICY = "failure-oriented-robustness-v1"


def robustness(
    dataset: Dataset, policy: PortfolioPolicy, baseline: dict[str, Any] | None = None
) -> dict[str, Any]:
    digest = hashlib.sha256(dataset.model_dump_json().encode()).hexdigest()
    baseline = simulate(dataset, policy) if baseline is None else baseline
    if (
        baseline.get("dataset_sha256") != digest
        or PortfolioPolicy.model_validate(baseline.get("policy")) != policy
    ):
        raise ValueError("Robustness baseline source/policy binding mismatch")
    baseline = {
        key: value
        for key, value in baseline.items()
        if key not in ("comparators", "comparator_runs")
    }
    names: dict[str, float] = defaultdict(float)
    sectors: dict[str, float] = defaultdict(float)
    for trade in baseline["executions"]:
        pnl = (
            trade["terminal_wealth"]
            - trade["entry_notional"]
            - trade["entry_cost"]
            - trade["exit_cost"]
        )
        names[trade["security_id"]] += pnl
        sectors[trade["sector"]] += pnl
    require_finite([names, sectors], "contribution diagnostics")
    if not math.isclose(
        sum(names.values()), baseline["ending_equity"] - policy.capital, rel_tol=1e-9, abs_tol=1e-6
    ):
        raise ValueError("Contribution ledger does not reconcile to baseline equity")
    top_name = min(names, key=lambda sid: (-names[sid], sid)) if names else None
    top_sector = min(sectors, key=lambda sector: (-sectors[sector], sector)) if sectors else None
    variations: list[tuple[str, dict[str, Any], bool, str | None]] = [
        (
            "exclude_top_contribution_name",
            {"excluded_security_ids": tuple(sorted(set(policy.excluded_security_ids) | {top_name}))}
            if top_name
            else {},
            True,
            None if top_name else "NO_EXECUTED_NAMES",
        ),
        (
            "exclude_top_contribution_sector",
            {"excluded_sectors": tuple(sorted(set(policy.excluded_sectors) | {top_sector}))}
            if top_sector
            else {},
            True,
            None if top_sector else "NO_EXECUTED_SECTORS",
        ),
        (
            "wider_cost_2x_or_100bps",
            {"one_way_cost_bps": max(100, policy.one_way_cost_bps * 2)},
            False,
            None,
        ),
        (
            "wider_cost_4x_or_250bps",
            {"one_way_cost_bps": max(250, policy.one_way_cost_bps * 4)},
            False,
            None,
        ),
        ("half_maximum_position", {"max_position": policy.max_position / 2}, False, None),
        ("liquidity_floor_2x", {"min_dollar_volume": policy.min_dollar_volume * 2}, False, None),
        ("liquidity_floor_10x", {"min_dollar_volume": policy.min_dollar_volume * 10}, False, None),
        (
            "filing_lag_3x_or_72h",
            {"filing_lag_hours": max(72, policy.filing_lag_hours * 3)},
            False,
            None,
        ),
        (
            "filing_lag_7x_or_168h",
            {"filing_lag_hours": max(168, policy.filing_lag_hours * 7)},
            False,
            None,
        ),
        (
            "exclude_declared_micro_bucket",
            {
                "excluded_cap_buckets": tuple(
                    sorted(set(policy.excluded_cap_buckets) | {"fixture-micro"})
                )
            },
            False,
            None,
        ),
        ("zero_known_delist_proceeds", {"delist_proceeds": "zero_sensitivity"}, False, None),
        (
            "independent_adjusted_price_series",
            {},
            False,
            "INDEPENDENT_ADJUSTED_SERIES_CONTRACT_UNAVAILABLE",
        ),
    ]
    attempts = []
    for name, changes, hindsight, unavailable in variations:
        attempt: dict[str, Any] = {
            "id": name,
            "selection_scope": "EX_POST_CONTRIBUTION_DIAGNOSTIC"
            if hindsight
            else "PREDECLARED_STRESS",
            "requested_changes": {
                key: None if isinstance(value, float) and not math.isfinite(value) else value
                for key, value in changes.items()
            },
            "unrepresentable_fields": [
                key
                for key, value in changes.items()
                if isinstance(value, float) and not math.isfinite(value)
            ],
            "status": "UNAVAILABLE" if unavailable else "PENDING",
            "reason": unavailable,
            "report": None,
        }
        if unavailable is None:
            try:
                changed = PortfolioPolicy.model_validate(policy.model_dump() | changes)
                report = simulate(dataset, changed)
                attempt.update(status="CALCULATED_FIXTURE_STRESS", report=report)
                if name == "exclude_declared_micro_bucket" and not any(
                    i.cap_bucket == "fixture-micro" and i.security_type == "common"
                    for i in dataset.instruments
                ):
                    attempt["reason"] = "NO_MATCHING_DECLARED_MICRO_BUCKET_MEMBERS"
                if name == "zero_known_delist_proceeds" and not any(
                    a.kind == "delist" and a.value != 0 for a in dataset.actions
                ):
                    attempt["reason"] = "ZERO_ASSUMPTION_EQUALS_ALL_REPORTED_DELIST_PROCEEDS"
            except (ValueError, OverflowError, ZeroDivisionError):
                attempt.update(status="REJECTED", reason="POLICY_OR_DATA_BOUNDARY_REJECTED")
        attempts.append(attempt)
    result = {
        "policy": POLICY,
        "mode": dataset.mode,
        "dataset_sha256": digest,
        "base_policy": policy.model_dump(),
        "baseline": baseline,
        "contributions": {
            "basis": "REALIZED_TERMINAL_WEALTH_LESS_ENTRY_NOTIONAL_AND_BOTH_COSTS",
            "names": dict(sorted(names.items())),
            "sectors": dict(sorted(sectors.items())),
            "highest_name": top_name,
            "highest_sector": top_sector,
        },
        "attempts": attempts,
        "status": "ALL_PREDECLARED_ATTEMPTS_RETAINED_NO_SELECTED_BEST_POLICY",
        "limitations": [
            "Synthetic fixture only; no empirical regime, decade or capacity claim",
            "Top contributor exclusions use later realized P&L and are hindsight diagnostics",
            "All attempts share execution, cash, caps, whole-share and missing-mark boundaries",
            "Filing lags change available fundamentals; source times stay fixed. "
            "Momentum may be unchanged",
            "Microcap exclusion uses fixture-micro; no real market-cap scale is inferred",
            "Zero proceeds applies only to known delists; unknown terminal values still reject",
            "Adjusted-series comparison requires a verified independent series",
            "Failures stay visible; no refit, winning policy or alpha selection",
        ],
    }
    require_finite(result, "robustness report")
    return result


def robustness_markdown(report: dict[str, Any] | None, run_id: str) -> str:
    if report is None:
        return f"# Robustness diagnostics\n\nRun {run_id}: unavailable in this archive.\n"
    lines = [
        "# Failure-oriented fixture robustness",
        "",
        f"Run {run_id}; {report['policy']}.",
        "All attempts retained. No selected best policy or empirical validation.",
        "",
        "| Attempt | Scope | Status | Modeled return | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["attempts"]:
        value = row["report"]["metrics"]["total_return"] if row["report"] else None
        lines.append(
            f"| {row['id']} | {row['selection_scope']} | {row['status']} | "
            f"{value if value is not None else 'Unavailable'} | {row['reason'] or 'None'} |"
        )
    lines.extend(
        [
            "",
            "## Declared policy",
            "",
            "```json",
            json.dumps(report["base_policy"], sort_keys=True, indent=2),
            "```",
            "",
            "## Limits",
            *[f"- {value}" for value in report["limitations"]],
        ]
    )
    return "\n".join(lines) + "\n"
