"""As-of ranking sensitivity only: no outcome labels, fitting or performance inference."""

import math
from typing import Any

from packages.research.discovery import DiscoveryPolicy


def ranking_sensitivity(signals: list[dict[str, Any]], policy: DiscoveryPolicy) -> dict[str, Any]:
    names = tuple(policy.weights)
    if len({s["security_id"] for s in signals}) != len(signals):
        raise ValueError("Duplicate sensitivity security")
    for signal in signals:
        if set(signal["components"]) != set(names):
            raise ValueError("Sensitivity requires the exact dated factor family")
        values = [signal["close"], signal["dollar_volume_20d"]]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Invalid sensitivity price/liquidity")
        if any(
            value is not None and (not math.isfinite(value) or not 0 <= value <= 100)
            for value in signal["components"].values()
        ):
            raise ValueError("Invalid sensitivity component")
    variants = [
        ("frozen_policy", policy.weights, policy.min_dollar_volume),
        ("equal_factor_weights", {k: 1 / len(names) for k in names}, policy.min_dollar_volume),
        (
            "price_volume_only",
            {k: float(k == "price_volume") for k in names},
            policy.min_dollar_volume,
        ),
        (
            "fundamental_inflection_only",
            {k: float(k == "fundamental_inflection") for k in names},
            policy.min_dollar_volume,
        ),
        ("liquidity_floor_2x", policy.weights, policy.min_dollar_volume * 2),
        ("liquidity_floor_10x", policy.weights, policy.min_dollar_volume * 10),
    ]
    output: list[dict[str, Any]] = []
    baseline: dict[str, int] = {}
    for name, weights, floor in variants:
        if not math.isfinite(floor):
            raise ValueError("Sensitivity liquidity threshold exceeds finite bounds")
        ranked = sorted(
            (
                {
                    "security_id": s["security_id"],
                    "score": round(
                        sum(weights[k] * v for k, v in s["components"].items() if v is not None), 4
                    ),
                    "factor_coverage": round(
                        sum(weights[k] for k, v in s["components"].items() if v is not None), 4
                    ),
                }
                for s in signals
                if s["eligible"]
                and s["close"] >= policy.min_price
                and s["dollar_volume_20d"] >= floor
            ),
            key=lambda s: (-s["score"], s["security_id"]),
        )
        if not output:
            baseline = {s["security_id"]: i + 1 for i, s in enumerate(ranked)}
        for i, row in enumerate(ranked):
            row["rank"] = i + 1
            prior = baseline.get(row["security_id"])
            row["rank_change"] = prior - i - 1 if prior is not None else None
        output.append(
            {
                "name": name,
                "weights": weights,
                "min_dollar_volume": floor,
                "ranked": ranked,
                "excluded": len(signals) - len(ranked),
            }
        )
    return {
        "status": "ASOF_RANKING_DIAGNOSTIC_NOT_PERFORMANCE_VALIDATION",
        "variants": output,
        "limitations": [
            "Frozen dated factors only; no outcome labels or refitting",
            "Missing components contribute no score or covered weight; no renormalization",
            "Equal-factor weights explicitly allocate one sixth to each family",
            "Ordinal ties resolve by permanent ID; rank changes are not statistical evidence",
            "Stricter liquidity filters change the comparison universe",
            "No selected best policy, return sensitivity, calibration or investment inference",
        ],
    }
