"""Predictors accept only prices, facts and dated identity; no outcome-label argument."""

from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

from packages.shared.models import Bar, Fact, Instrument, Symbol

VERSION = "heuristic-v1-unvalidated"


def utc_asof(asof: datetime) -> datetime:
    if asof.utcoffset() is None:
        raise ValueError("asof must include timezone")
    return asof.astimezone(UTC)


def symbol_at(symbols: list[Symbol], security_id: str, asof: datetime) -> str:
    asof = utc_asof(asof)
    found = [
        s.ticker
        for s in symbols
        if s.security_id == security_id
        and s.valid_from <= asof.date()
        and (s.valid_to is None or asof.date() < s.valid_to)
    ]
    if len(found) != 1:
        raise ValueError("missing or ambiguous historical identity")
    return found[0]


def eligible(instrument: Instrument, asof: datetime) -> bool:
    asof = utc_asof(asof)
    return (
        instrument.security_type == "common"
        and instrument.first_seen <= asof.date()
        and (instrument.last_seen is None or asof.date() <= instrument.last_seen)
    )


def facts_at(
    facts: list[Fact], security_id: str, asof: datetime, lag_hours: int = 24
) -> list[Fact]:
    if lag_hours < 0:
        raise ValueError("processing lag must be nonnegative")
    return sorted(
        [
            f
            for f in facts
            if f.security_id == security_id
            and max(f.accepted_at, f.published_at) + timedelta(hours=lag_hours) <= asof
        ],
        key=lambda f: (f.period_end, f.published_at, f.accepted_at, f.accession),
    )


def assert_pit(publications: list[datetime], asof: datetime) -> None:
    if asof.utcoffset() is None or any(p > asof for p in publications):
        raise ValueError("PIT cutoff violation")


def snapshot(
    instrument: Instrument, bars: list[Bar], facts: list[Fact], asof: datetime
) -> dict[str, Any]:
    asof = utc_asof(asof)
    history = sorted(
        [
            b
            for b in bars
            if b.security_id == instrument.security_id
            and b.session <= asof.date()
            and b.available_at <= asof
        ],
        key=lambda b: b.session,
    )
    if len({b.session for b in history}) != len(history):
        raise ValueError("duplicate bar sessions")
    if len(history) < 121:
        raise ValueError("insufficient price history (121 sessions required)")
    known = facts_at(facts, instrument.security_id, asof)
    assert_pit([b.available_at for b in history] + [f.published_at for f in known], asof)
    closes = [b.close for b in history]
    returns = {f"return_{n}d": closes[-1] / closes[-1 - n] - 1 for n in (1, 5, 21, 63)}
    base_high = max(b.high for b in history[-61:-1])
    base_low = min(b.low for b in history[-61:-1])
    volume_baseline = mean(b.volume for b in history[-21:-1])
    if volume_baseline <= 0:
        raise ValueError("insufficient volume baseline")
    relative_volume = history[-1].volume / volume_baseline
    dollar_volume = mean(b.close * b.volume for b in history[-20:])
    ema: dict[str, float] = {}
    for n in (8, 21):
        value = closes[0]
        for close in closes[1:]:
            value += 2 / (n + 1) * (close - value)
        ema[f"ema_{n}"] = value
    # Last knowable revision per period. Amendments remain in immutable raw history.
    revisions: dict[str, Fact] = {}
    for f in known:
        if f.metric == "annual_revenue":
            revisions[str(f.period_end)] = f
    revenues = list(revisions.values())
    growth = None
    if len(revenues) >= 2 and revenues[-2].value > 0:
        growth = revenues[-1].value / revenues[-2].value - 1
    components: dict[str, float | None] = {
        "price_volume": min(100, max(0, returns["return_63d"] * 200 + 30)),
        "fundamental_inflection": None if growth is None else min(100, max(0, growth * 100)),
        "industry_breadth": None,
        "business_quality": None,
        "valuation_catalyst": None,
        "liquidity_risk": min(100, dollar_volume / 100000),
    }
    weights = {
        "price_volume": 0.2,
        "fundamental_inflection": 0.25,
        "industry_breadth": 0.15,
        "business_quality": 0.15,
        "valuation_catalyst": 0.15,
        "liquidity_risk": 0.1,
    }
    completeness = sum(weights[k] for k, v in components.items() if v is not None)
    score = sum(weights[k] * v for k, v in components.items() if v is not None)
    breakout = closes[-1] > base_high and relative_volume >= 1.5
    stage = "IGNITION" if breakout and dollar_volume >= 1000000 else "WATCH"
    if closes[-1] > base_low * 1.8:
        stage = "EXTENDED/AGING"
    latest = max([b.available_at for b in history] + [f.published_at for f in known])
    return {
        "security_id": instrument.security_id,
        "name": instrument.name,
        "asof_time": asof.isoformat(),
        "latest_included_publication": latest.isoformat(),
        "feature_version": VERSION,
        "source_ids": sorted({b.source_id for b in history} | {f.source_id for f in known}),
        "close": closes[-1],
        **returns,
        **ema,
        "dollar_volume_20d": dollar_volume,
        "relative_volume": relative_volume,
        "base_high_60d": base_high,
        "base_width_60d": base_high / base_low - 1,
        "revenue_growth": growth,
        "components": components,
        "weights": weights,
        "score": round(score, 4),
        "completeness": round(completeness, 4),
        "missing_weight_penalty": round(100 * (1 - completeness), 4),
        "stage": stage,
        "eligible": eligible(instrument, asof),
        "price_session": str(history[-1].session),
        "evidence": [f.model_dump(mode="json") for f in known],
        "chart": [{"date": str(b.session), "close": b.close} for b in history[-126:]],
        "limitations": [
            "FIXTURE; no investment inference",
            "Unvalidated placeholder weights",
            "Missing factors retain null values; weight is not redistributed",
            "Stages WATCH / IGNITION / EXTENDED only in this MVP",
            "Raw prices; fixture has no splits or dividends",
        ],
    }
