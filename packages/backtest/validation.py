"""Transparent diagnostics and chronological purged partitions; no fitted/untouched-test claim."""

import math
import random
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any

from packages.shared.numeric import require_finite


def partition_windows(rows: list[dict[str, Any]], embargo_days: int = 7) -> dict[str, Any]:
    if not 0 <= embargo_days <= 365:
        raise ValueError("Embargo must be zero to 365 calendar days")
    ordered = sorted(rows, key=lambda r: r["decision"])
    if len({r["decision"] for r in ordered}) != len(ordered):
        raise ValueError("Duplicate observation dates")
    for row in ordered:
        if not row["decision"] < row["entry"] <= row["exit"]:
            raise ValueError("Invalid decision/entry/outcome chronology")
    if len(ordered) < 5:
        return {
            "status": "INSUFFICIENT_WINDOWS",
            "train": [],
            "validation": [],
            "holdout": [],
            "purged": [],
            "embargo_days": embargo_days,
        }
    a, b = max(1, int(len(ordered) * 0.6)), max(2, int(len(ordered) * 0.8))
    validation_start = date.fromisoformat(ordered[a]["decision"])
    holdout_start = date.fromisoformat(ordered[b]["decision"])
    result: dict[str, Any] = {
        "status": "DESIGN_DIAGNOSTIC_NOT_UNTOUCHED_HOLDOUT",
        "train": [],
        "validation": [],
        "holdout": [],
        "purged": [],
        "embargo_days": embargo_days,
    }
    for i, row in enumerate(ordered):
        group = "train" if i < a else "validation" if i < b else "holdout"
        boundary = (
            validation_start
            if group == "train"
            else holdout_start
            if group == "validation"
            else None
        )
        if (
            boundary is not None
            and date.fromisoformat(row["exit"]) + timedelta(days=embargo_days) >= boundary
        ):
            result["purged"].append(row["decision"])
        else:
            result[group].append(row["decision"])
    return result


def performance(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    try:
        result = _performance(rows, field)
        require_finite(result, "window performance")
        return result
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Window performance exceeds finite numeric bounds") from exc


def _performance(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    if not rows:
        return {
            "windows": 0,
            "total_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "payoff_ratio": None,
            "cagr": None,
        }
    returns = [r[field] for r in rows]
    if any(v is None or not math.isfinite(v) or v < -1 for v in returns):
        raise ValueError("Missing or invalid comparable returns")
    equity = peak = 1.0
    drawdown = 0.0
    for value in returns:
        equity *= 1 + value
        require_finite(equity, "compounded wealth")
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1)
    days = (date.fromisoformat(rows[-1]["exit"]) - date.fromisoformat(rows[0]["entry"])).days
    wins, losses = [v for v in returns if v > 0], [v for v in returns if v < 0]
    return {
        "windows": len(rows),
        "total_return": equity - 1,
        "max_drawdown": drawdown,
        "win_rate": len(wins) / len(rows),
        "payoff_ratio": mean(wins) / -mean(losses) if wins and losses else None,
        "cagr": equity ** (365.25 / days) - 1 if days > 0 else None,
        "window_volatility": pstdev(returns),
        "worst_window": min(returns),
        "turnover_assumption": "Full liquidation and re-entry each independent window",
        "annualized_sharpe": None,
        "sharpe_reason": "Sparse nonuniform windows; no daily equity/risk-free series",
    }


def diagnostics(backtest: dict[str, Any]) -> dict[str, Any]:
    rows = backtest["rows"]
    partitions = partition_windows(rows)
    comparators = {
        name: performance(rows, field)
        for name, field in (
            ("selector", "net_return"),
            ("equal_weight", "equal_weight_net"),
            ("benchmark", "benchmark_net"),
        )
    }
    # Resample complete date windows, not individual securities; descriptive fixture math.
    rng = random.Random(backtest["seed"])
    spread = [r["net_return"] - r["equal_weight_net"] for r in rows]
    samples = sorted(mean(rng.choices(spread, k=len(spread))) for _ in range(500)) if spread else []
    sensitivity = []
    for cost in (20, 40, 80, 120):
        adjusted = [
            r
            | {
                "net_return": max(
                    -1.0, r["net_return"] + (backtest["cost_round_trip_bps"] - cost) / 10000
                )
            }
            for r in rows
        ]
        sensitivity.append({"round_trip_bps": cost, **performance(adjusted, "net_return")})
    subgroups = []
    for security_id in sorted({r["security_id"] for r in rows}):
        subgroups.append(
            {
                "security_id": security_id,
                **performance([r for r in rows if r["security_id"] == security_id], "net_return"),
            }
        )
    return {
        "mode": "FIXTURE",
        "status": "DESCRIPTIVE_DEMONSTRATION_NOT_EMPIRICAL_VALIDATION",
        "partitions": partitions,
        "metrics": comparators,
        "cost_sensitivity": sensitivity,
        "subgroups": subgroups,
        "paired_window_bootstrap": {
            "seed": backtest["seed"],
            "resamples": 500,
            "mean_excess_versus_equal_weight": mean(spread) if spread else None,
            "interval_95": [samples[12], samples[487]] if samples else None,
            "status": "ILLUSTRATIVE_FIXTURE_INTERVAL_NOT_EVIDENCE",
        },
        "holdout_status": "NOT_UNTOUCHED: fixed fixture and rules already inspected; "
        "no holdout performance claim",
        "constraints": {
            "long_only": True,
            "leverage": 1,
            "capacity_status": "NOT_MODELED_IN_LEGACY_TOY",
            "position_sector_caps": "NOT_MODELED_IN_LEGACY_TOY",
        },
    }
