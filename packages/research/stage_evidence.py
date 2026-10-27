"""Dated filing inflections and explicit v2 stage gates; no outcome or operator-note input."""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING, Any

from packages.research.features import facts_at, utc_asof
from packages.shared.models import Fact

if TYPE_CHECKING:
    from packages.research.discovery import DiscoveryPolicy


def _growth(current: float, before: float) -> float | None:
    if before <= 0:
        return None
    value = current / before - 1
    return value if math.isfinite(value) else None


def filing_inflections(
    facts: list[Fact], security_id: str, asof: datetime, max_age_days: int = 550
) -> dict[str, Any]:
    asof = utc_asof(asof)
    if type(max_age_days) is not int or max_age_days < 1:
        raise ValueError("Positive filing age bound required")
    latest = {(f.metric, f.period_end): f for f in facts_at(facts, security_id, asof)}
    revenues = sorted(
        (f for f in latest.values() if f.metric == "annual_revenue" and f.unit == "USD"),
        key=lambda f: f.period_end,
    )
    signals: list[dict[str, Any]] = []
    growth = None
    period_age = (asof.date() - revenues[-1].period_end).days if revenues else None
    fresh = period_age is not None and period_age <= max_age_days
    if fresh and len(revenues) >= 2:
        before, current = revenues[-2:]
        if before.value > 0 and 330 <= (current.period_end - before.period_end).days <= 400:
            growth = _growth(current.value, before.value)
            if growth is not None and growth > 0:
                signals.append({"kind": "POSITIVE_REVENUE_GROWTH", "inputs": [before, current]})
            if len(revenues) >= 3:
                older = revenues[-3]
                if (
                    older.value > 0
                    and 330 <= (before.period_end - older.period_end).days <= 400
                    and growth is not None
                    and (previous_growth := _growth(before.value, older.value)) is not None
                    and growth > previous_growth
                ):
                    signals.append(
                        {"kind": "REVENUE_GROWTH_ACCELERATION", "inputs": [older, before, current]}
                    )
            for metric, name in (
                ("annual_operating_income", "OPERATING_MARGIN_IMPROVEMENT"),
                ("annual_operating_cashflow", "CASHFLOW_MARGIN_IMPROVEMENT"),
            ):
                a, b = (
                    latest.get((metric, before.period_end)),
                    latest.get((metric, current.period_end)),
                )
                if (
                    a is not None
                    and b is not None
                    and a.unit == b.unit == "USD"
                    and before.value > 0
                    and current.value > 0
                    and a.accession == before.accession
                    and b.accession == current.accession
                    and math.isfinite(b.value / current.value)
                    and math.isfinite(a.value / before.value)
                    and b.value / current.value > a.value / before.value
                ):
                    signals.append({"kind": name, "inputs": [before, a, current, b]})
    citations = {(f.metric, f.period_end, f.accession): f for s in signals for f in s["inputs"]}
    return {
        "policy": "filing-inflections-v1-annual-proxy",
        "asof": asof.isoformat(),
        "period_age_days": period_age,
        "max_age_days": max_age_days,
        "status": "NO_REVENUE" if not revenues else "AVAILABLE_PERIOD" if fresh else "STALE_PERIOD",
        "revenue_growth": growth,
        "signals": [
            {
                "kind": s["kind"],
                "input_ids": [[f.metric, str(f.period_end), f.accession] for f in s["inputs"]],
            }
            for s in signals
        ],
        "distinct_accessions": sorted({f.accession for f in citations.values()}),
        "citations": [f.model_dump(mode="json") for f in citations.values()],
        "limitations": [
            "Annual inflection proxies; no inferred quarterly acceleration",
            "Operator catalysts and narrative assertions do not enter these gates",
        ],
    }


def classify_v2(
    feature: dict[str, Any],
    policy: DiscoveryPolicy,
    prior: str,
    streak: int,
) -> tuple[str, str]:
    """Apply frozen thresholds to prepared, availability-bound evidence."""
    if not feature["eligible"] or feature["close"] < policy.min_price:
        return "INVALIDATED", "Outside configured eligibility/price floor"
    trigger = feature.get("trigger_reference")
    evidence = feature.get("filing_inflections", {})
    growth = evidence.get("revenue_growth")
    if trigger is not None and feature["close"] < trigger:
        return "INVALIDATED", "Close fell below the original ignition base reference"
    if trigger is not None and growth is not None and growth <= policy.invalidate_revenue_growth:
        return "INVALIDATED", "Available filing revenue growth breached the invalidation threshold"
    if feature["dollar_volume_20d"] < policy.min_dollar_volume:
        return "WATCH", "Below configured liquidity floor"
    if feature["close"] / feature["ema_21"] - 1 > policy.max_ema_stretch or (
        trigger is not None and feature["close"] / trigger - 1 > policy.max_base_stretch
    ):
        return "EXTENDED/AGING", "Price exceeds configured EMA or original-base stretch"
    rank = feature.get("relative_evidence", {}).get("rank_percentile_63d")
    duration = feature.get("technical", {}).get("base_duration_windows")
    reference = feature.get("breakout_reference")
    ignition = (
        reference is not None
        and feature["close"] > reference
        and feature["relative_volume"] >= policy.ignition_relative_volume
        and feature["base_width_60d"] <= policy.max_base_width
        and duration is not None
        and duration >= policy.min_base_duration_windows
        and rank is not None
        and rank >= policy.min_relative_rank
    )
    if trigger is None:
        return (
            (
                "IGNITION",
                "Configured prior-window breakout, volume, base duration and relative rank",
            )
            if ignition
            else (
                "WATCH",
                "No ignition satisfying every configured duration/rank/price/volume gate",
            )
        )
    strength = (
        feature["ema_8"] > feature["ema_21"]
        and feature["return_21d"] > 0
        and feature.get("relative_strength_63d") is not None
        and feature["relative_strength_63d"] > 0
    )
    signals = evidence.get("signals", [])
    if strength and signals:
        breadth = feature.get("sector_breadth")
        if (
            prior in ("IGNITION", "EMERGING", "CONFIRMED")
            and streak >= policy.confirmation_sessions
            and breadth is not None
            and breadth >= policy.min_peer_participation
            and len(signals) >= policy.min_inflection_signals
            and len(evidence.get("distinct_accessions", [])) >= policy.min_inflection_filings
        ):
            return (
                "CONFIRMED",
                "Maintained breakout, strength, peers and multiple cited filing inflections",
            )
        return "EMERGING", "Maintained original breakout with strength and dated filing improvement"
    return (
        "WATCH",
        "Original breakout held; dated filing improvement or relative trend is unavailable",
    )
