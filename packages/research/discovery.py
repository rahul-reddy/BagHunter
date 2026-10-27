"""Configurable point-in-time discovery and dated stage transitions, without outcome labels."""

import hashlib
from collections import Counter
from datetime import UTC, datetime
from statistics import mean
from typing import Any, Literal

from pydantic import Field, model_validator

from packages.data.finviz import _json
from packages.research.features import eligible, snapshot, symbol_at, utc_asof
from packages.research.fundamentals import statement_ratios
from packages.research.technical import cross_section_evidence, technical_evidence
from packages.shared.models import Dataset, Record
from packages.shared.numeric import require_finite

STAGES = ("WATCH", "IGNITION", "EMERGING", "CONFIRMED", "EXTENDED/AGING", "INVALIDATED")


class DiscoveryPolicy(Record):
    version: Literal["discovery-v1-unvalidated"] = "discovery-v1-unvalidated"
    min_dollar_volume: float = Field(default=1_000_000, ge=0)
    min_price: float = Field(default=1, gt=0)
    ignition_relative_volume: float = Field(default=1.5, gt=0)
    max_base_width: float = Field(default=0.4, gt=0)
    max_ema_stretch: float = Field(default=0.25, gt=0)
    confirmation_sessions: int = Field(default=3, ge=1, le=20)
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "price_volume": 0.2,
            "fundamental_inflection": 0.25,
            "industry_breadth": 0.15,
            "business_quality": 0.15,
            "valuation_catalyst": 0.15,
            "liquidity_risk": 0.1,
        }
    )

    @model_validator(mode="after")
    def valid_weights(self) -> "DiscoveryPolicy":
        required = {
            "price_volume",
            "fundamental_inflection",
            "industry_breadth",
            "business_quality",
            "valuation_catalyst",
            "liquidity_risk",
        }
        if set(self.weights) != required or any(not 0 <= v <= 1 for v in self.weights.values()):
            raise ValueError("Exactly the six bounded score weights are required")
        if abs(sum(self.weights.values()) - 1) > 1e-9:
            raise ValueError("Score weights must sum to one; no silent normalization")
        return self


def classify(
    feature: dict[str, Any], policy: DiscoveryPolicy, prior: str = "WATCH", streak: int = 0
) -> tuple[str, str]:
    if not feature["eligible"] or feature["close"] < policy.min_price:
        return "INVALIDATED", "Outside configured eligibility/price floor"
    if feature["dollar_volume_20d"] < policy.min_dollar_volume:
        return "WATCH", "Below configured liquidity floor"
    if feature["close"] / feature["ema_21"] - 1 > policy.max_ema_stretch:
        return "EXTENDED/AGING", "Price exceeds configured stretch above EMA21"
    if feature["close"] < feature["ema_21"] and feature["return_21d"] < 0:
        return (
            ("INVALIDATED", "Trend failed below EMA21")
            if prior != "WATCH"
            else ("WATCH", "Negative trend; no active setup to invalidate")
        )
    if (
        feature["close"] > feature["base_high_60d"]
        and feature["relative_volume"] >= policy.ignition_relative_volume
        and feature["base_width_60d"] <= policy.max_base_width
    ):
        return "IGNITION", "Prior 60-session high cleared with qualifying volume and base width"
    growth = feature["revenue_growth"]
    relative = feature.get("relative_strength_63d")
    improving = (
        feature["ema_8"] > feature["ema_21"]
        and feature["return_21d"] > 0
        and growth is not None
        and growth > 0
        and relative is not None
        and relative > 0
    )
    if improving:
        breadth = feature.get("sector_breadth")
        if (
            prior in ("IGNITION", "EMERGING", "CONFIRMED")
            and streak >= policy.confirmation_sessions
            and breadth is not None
            and breadth >= 0.5
        ):
            return (
                "CONFIRMED",
                "Sustained trend, positive revenue growth, relative strength and breadth",
            )
        return "EMERGING", "Positive trend, dated revenue growth and benchmark-relative strength"
    return "WATCH", "No qualifying setup under the frozen policy"


def discover(dataset: Dataset, asof: datetime, policy: DiscoveryPolicy) -> dict[str, Any]:
    try:
        result = _discover(dataset, asof, policy)
        require_finite(result, "discovery output")
        return result
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Discovery features exceed finite numeric bounds") from exc


def _discover(dataset: Dataset, asof: datetime, policy: DiscoveryPolicy) -> dict[str, Any]:
    asof = utc_asof(asof)
    sessions = sorted(
        {b.session for b in dataset.bars if b.available_at <= asof and b.session <= asof.date()}
    )
    if len(sessions) < 121:
        raise ValueError("Discovery requires 121 known sessions")
    histories: dict[str, list[dict[str, Any]]] = {}
    last: list[dict[str, Any]] = []
    benchmark = next((i for i in dataset.instruments if i.security_type == "benchmark"), None)
    # Fixed lookback has an explicit WATCH initialization; no hidden state or outcome input.
    for day in sessions[-21:]:
        clock = (
            asof if day == sessions[-1] else datetime(day.year, day.month, day.day, 23, tzinfo=UTC)
        )
        batch = []
        benchmark_return = None
        if benchmark is not None:
            try:
                benchmark_return = snapshot(benchmark, dataset.bars, [], clock)["return_63d"]
            except ValueError as exc:
                if "insufficient price history" not in str(exc):
                    raise
        for instrument in dataset.instruments:
            if not eligible(instrument, clock):
                continue
            try:
                f = snapshot(instrument, dataset.bars, dataset.facts, clock)
            except ValueError as exc:
                if "insufficient price history" in str(exc):
                    continue
                raise
            f["ticker"] = symbol_at(dataset.symbols, instrument.security_id, clock)
            f["feature_version"] = policy.version
            f["financials"] = statement_ratios(dataset.facts, instrument.security_id, clock)
            f["revenue_growth"] = f["financials"]["revenue_growth"]
            growth = f["revenue_growth"]
            f["components"]["fundamental_inflection"] = (
                None if growth is None else min(1, max(0, growth)) * 100
            )
            margins = [f["financials"]["operating_margin"], f["financials"]["cashflow_margin"]]
            f["components"]["business_quality"] = (
                None if any(m is None for m in margins) else min(1, max(0, mean(margins))) * 100
            )
            f["sector"] = instrument.sector
            f["cap_bucket"] = instrument.cap_bucket
            f["relative_strength_63d"] = (
                None if benchmark_return is None else f["return_63d"] - benchmark_return
            )
            known = sorted(
                (
                    b
                    for b in dataset.bars
                    if b.security_id == instrument.security_id
                    and b.available_at <= clock
                    and b.session <= clock.date()
                ),
                key=lambda b: b.session,
            )
            f["technical"] = technical_evidence(
                known, instrument.security_id, clock, policy.max_base_width
            )
            f["chart"] = [
                {
                    "date": str(b.session),
                    "close": b.close,
                    "volume": b.volume,
                    "high": b.high,
                    "low": b.low,
                }
                for b in known[-126:]
            ]
            f["volatility_20d"] = f["technical"]["volatility_20d"]
            f["consolidation"] = f["base_width_60d"] <= policy.max_base_width
            require_finite(f, "discovery features before ranking")
            batch.append(f)
        relative = cross_section_evidence(batch)
        for f in batch:
            f["relative_evidence"] = relative[f["security_id"]]
            peers = [p for p in batch if p["sector"] == f["sector"]]
            breadth = mean(p["return_21d"] > 0 for p in peers) if len(peers) > 1 else None
            f["sector_breadth"] = breadth
            f["sector_peer_count"] = len(peers)
            f["components"]["industry_breadth"] = None if breadth is None else breadth * 100
            f["weights"] = policy.weights
            f["score"] = round(
                sum(policy.weights[k] * v for k, v in f["components"].items() if v is not None), 4
            )
            f["completeness"] = round(
                sum(policy.weights[k] for k, v in f["components"].items() if v is not None), 4
            )
            f["missing_weight_penalty"] = round(100 * (1 - f["completeness"]), 4)
            history = histories.setdefault(f["security_id"], [])
            prior = history[-1]["stage"] if history else "WATCH"
            streak = 0
            for row in reversed(history):
                if row["stage"] not in ("IGNITION", "EMERGING", "CONFIRMED"):
                    break
                streak += 1
            stage, reason = classify(f, policy, prior, streak)
            history.append(
                {
                    "asof": clock.isoformat(),
                    "session": f["price_session"],
                    "stage": stage,
                    "previous_stage": prior,
                    "reason": reason,
                    "close": f["close"],
                    "score": f["score"],
                    "base_high_60d": f["base_high_60d"],
                }
            )
            f["stage"], f["stage_reason"] = stage, reason
            f["stage_history"] = list(history)
            f["risk_flags"] = ["UNVALIDATED_HEURISTIC", "FIXTURE_ONLY"]
            if f["completeness"] < 0.75:
                f["risk_flags"].append("INCOMPLETE_FACTORS")
            if f["dollar_volume_20d"] < policy.min_dollar_volume:
                f["risk_flags"].append("LOW_LIQUIDITY")
            f["limitations"] = [s for s in f["limitations"] if not s.startswith("Stages WATCH")]
            f["limitations"].append(
                "Stage history initializes WATCH at the start of a 21-session window"
            )
        last = batch
    return {
        "policy": policy.model_dump(mode="json"),
        "policy_sha256": hashlib.sha256(_json(policy.model_dump(mode="json"))).hexdigest(),
        "signals": sorted(last, key=lambda f: (-f["score"], f["security_id"])),
        "stage_counts": dict(Counter(f["stage"] for f in last)),
        "breadth": mean(f["return_21d"] > 0 for f in last) if last else None,
        "benchmark_return_63d": benchmark_return,
        "regime": "UNAVAILABLE"
        if benchmark_return is None
        else ("POSITIVE_63D" if benchmark_return > 0 else "NEGATIVE_63D"),
        "scope": "FIXTURE; descriptive breadth and regime, not empirical inference",
    }
