"""Dated technical evidence and sector proxies, independent of labels and score policy."""

import math
from datetime import UTC, datetime
from statistics import mean, pstdev
from typing import Any

from packages.shared.models import Bar
from packages.shared.numeric import require_finite

POLICY = "technical-evidence-v1"
BASE_WINDOW = 20
BASE_CAP = 252


def technical_evidence(
    bars: list[Bar], security_id: str, asof: datetime, base_width_limit: float = 0.4
) -> dict[str, Any]:
    if asof.utcoffset() is None or not math.isfinite(base_width_limit) or base_width_limit <= 0:
        raise ValueError("Aware technical clock and positive finite base width required")
    asof = asof.astimezone(UTC)
    known = sorted(
        (
            b
            for b in bars
            if b.security_id == security_id and b.session <= asof.date() and b.available_at <= asof
        ),
        key=lambda b: b.session,
    )
    if len({b.session for b in known}) != len(known):
        raise ValueError("Duplicate technical sessions")
    result: dict[str, Any] = {
        "policy": POLICY,
        "asof_time": asof.isoformat(),
        "observations": len(known),
        "price_session": str(known[-1].session) if known else None,
        "latest_available_at": max(b.available_at for b in known).isoformat() if known else None,
        "source_ids": sorted({b.source_id for b in known}),
        "adjustment_basis": "RAW",
        "missing": [],
        "base_width_limit": base_width_limit,
        "base_window": BASE_WINDOW,
        "base_cap": BASE_CAP,
        "base_duration_windows": None,
        "base_left_censored": None,
        "gap_open": None,
        "mean_absolute_gap_20d": None,
        "atr_20": None,
        "volatility_20d": None,
        "volatility_60d": None,
        "volatility_contraction": None,
        "stale_calendar_days": (asof.date() - known[-1].session).days if known else None,
    }
    closes = [b.close for b in known]
    require_finite([[b.open, b.high, b.low, b.close] for b in known], "technical prices")
    if any(min(b.open, b.high, b.low, b.close) <= 0 for b in known):
        raise ValueError("Positive technical prices required")
    try:
        returns = [right / left - 1 for left, right in zip(closes[:-1], closes[1:], strict=True)]
        require_finite(returns, "technical daily returns")
        for window in (20, 50, 200):
            result[f"sma_{window}"] = mean(closes[-window:]) if len(closes) >= window else None
        for window in (8, 21):
            value = closes[0] if closes else None
            for close in closes[1:]:
                assert value is not None
                value += 2 / (window + 1) * (close - value)
            result[f"ema_{window}"] = value
        for window in (20, 60, 120):
            prior = known[-window - 1 : -1] if len(known) > window else []
            high = max(b.high for b in prior) if prior else None
            result[f"high_{window}_prior"] = high
            result[f"distance_high_{window}"] = closes[-1] / high - 1 if high is not None else None
            result[f"breakout_{window}"] = closes[-1] > high if high is not None else None
        for window in (20, 60):
            result[f"volatility_{window}d"] = (
                pstdev(returns[-window:]) * math.sqrt(252) if len(returns) >= window else None
            )
        short, long = result["volatility_20d"], result["volatility_60d"]
        if short is not None and long is not None and long > 0:
            result["volatility_contraction"] = short / long
        elif long == 0:
            result["missing"].append(
                {"field": "volatility_contraction", "reason": "ZERO_60D_REFERENCE_VOLATILITY"}
            )
        if len(known) >= 2:
            result["gap_open"] = known[-1].open / known[-2].close - 1
        if len(known) >= 21:
            gaps = [
                known[i].open / known[i - 1].close - 1 for i in range(len(known) - 20, len(known))
            ]
            result["mean_absolute_gap_20d"] = mean(abs(value) for value in gaps)
            result["atr_20"] = mean(
                max(
                    b.high - b.low,
                    abs(b.high - known[i - 1].close),
                    abs(b.low - known[i - 1].close),
                )
                for i, b in enumerate(known)
                if i >= len(known) - 20
            )
            available = min(BASE_CAP, len(known) - BASE_WINDOW)
            count = 0
            for end in range(len(known) - 1, len(known) - 1 - available, -1):
                previous = known[end - BASE_WINDOW : end]
                width = max(b.high for b in previous) / min(b.low for b in previous) - 1
                require_finite(width, "technical base width")
                if width > base_width_limit:
                    break
                count += 1
            result["base_duration_windows"] = count
            result["base_left_censored"] = count == available
        for name, value in result.items():
            if value is None and not any(row["field"] == name for row in result["missing"]):
                result["missing"].append(
                    {"field": name, "reason": "INSUFFICIENT_AVAILABLE_HISTORY"}
                )
        require_finite(result, "technical evidence")
        return result
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Technical evidence exceeds finite numeric bounds") from exc


def cross_section_evidence(signals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if len({s["security_id"] for s in signals}) != len(signals):
        raise ValueError("Duplicate cross-section identity")
    require_finite([[s["return_63d"], s["return_21d"]] for s in signals], "cross-section returns")

    def percentile(value: float, values: list[float]) -> float | None:
        if len(values) < 2:
            return None
        return (sum(v < value for v in values) + (sum(v == value for v in values) - 1) / 2) / (
            len(values) - 1
        )

    result = {}
    market = [s["return_63d"] for s in signals]
    references = [
        {
            "security_id": s["security_id"],
            "asof_time": s.get("asof_time"),
            "price_session": s.get("price_session"),
            "latest_available_at": s.get("technical", {}).get("latest_available_at"),
            "source_ids": s.get("technical", {}).get("source_ids", []),
        }
        for s in sorted(signals, key=lambda s: s["security_id"])
    ]
    for signal in signals:
        sector = signal.get("sector")
        peers = [
            s
            for s in signals
            if isinstance(sector, str) and sector.strip() and s.get("sector") == sector
        ]
        others = [s for s in peers if s["security_id"] != signal["security_id"]]
        sector_values = [s["return_63d"] for s in peers]
        row = {
            "policy": "cross-section-evidence-v1",
            "scope": "KNOWN_COMMON_EQUITIES_WITH_HISTORY_BEFORE_PRICE_LIQUIDITY_FILTERS",
            "universe_count": len(signals),
            "sector_count": len(peers),
            "references": references,
            "rank_percentile_63d": percentile(signal["return_63d"], market),
            "sector_rank_percentile_63d": percentile(signal["return_63d"], sector_values),
            "sector_relative_63d": signal["return_63d"] - mean(s["return_63d"] for s in others)
            if others
            else None,
            "sector_participation_21d": mean(s["return_21d"] > 0 for s in peers)
            if len(peers) >= 2
            else None,
            "sector_dispersion_63d": pstdev(sector_values) if len(peers) >= 2 else None,
            "universe_dispersion_63d": pstdev(market) if len(market) >= 2 else None,
            "limitations": [
                "Sector is an explicit proxy, not industry history",
                "Average-rank ties; one-member ranks/dispersion are undefined",
                "No outcome labels, score-weight changes or empirical calibration",
            ],
        }
        require_finite(row, "cross-section evidence")
        result[signal["security_id"]] = row
    return result


def technical_report(run: dict[str, Any]) -> dict[str, Any]:
    """Use archived fields only: never recompute a historical run on download."""
    return {
        "run_id": run["run_id"],
        "asof": run.get("asof"),
        "mode": run["mode"],
        "signals": [
            {
                "security_id": s["security_id"],
                "technical": s.get("technical"),
                "relative_evidence": s.get("relative_evidence"),
            }
            for s in run["signals"]
        ],
    }
