"""Dated long-only allocation targets, before observing execution prices or outcomes."""

import math
from collections import Counter, defaultdict
from datetime import datetime
from statistics import pstdev
from typing import Any, Literal

from packages.research.features import utc_asof
from packages.shared.models import Bar
from packages.shared.numeric import require_finite

Allocation = Literal["cap_ranked", "equal_weight", "inverse_volatility", "sector_neutral", "cash"]
VERSION = "allocation-v1"
MODES: tuple[Allocation, ...] = (
    "cap_ranked",
    "equal_weight",
    "inverse_volatility",
    "sector_neutral",
    "cash",
)


def dated_volatility(
    bars: list[Bar], security_id: str, clock: datetime, window: int
) -> dict[str, Any]:
    clock = utc_asof(clock)
    if window not in (20, 60):
        raise ValueError("Allocation volatility requires a 20/60 observation window")
    known = sorted(
        (
            b
            for b in bars
            if b.security_id == security_id
            and b.session <= clock.date()
            and b.available_at <= clock
        ),
        key=lambda b: b.session,
    )
    if len({b.session for b in known}) != len(known):
        raise ValueError("Duplicate volatility sessions")
    result: dict[str, Any] = {
        "window": window,
        "observations": min(len(known), window + 1),
        "known_observations": len(known),
        "value": None,
        "reason": "INSUFFICIENT_DATED_VOLATILITY_HISTORY",
        "source_ids": [],
        "latest_available_at": None,
    }
    if len(known) < window + 1:
        return result
    sample = known[-window - 1 :]
    try:
        returns = [b.close / a.close - 1 for a, b in zip(sample[:-1], sample[1:], strict=True)]
        require_finite(returns, "allocation volatility returns")
        value = pstdev(returns) * math.sqrt(252)
        require_finite(value, "allocation volatility")
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Allocation volatility exceeds finite bounds") from exc
    result.update(
        value=value,
        reason="ZERO_REFERENCE_VOLATILITY" if value == 0 else None,
        source_ids=sorted({b.source_id for b in sample}),
        latest_available_at=max(b.available_at for b in sample).isoformat(),
    )
    return result


def allocation_targets(
    candidates: list[dict[str, Any]], mode: Allocation, max_position: float, max_sector: float
) -> dict[str, Any]:
    """Inputs are the dated, filtered candidate pool; targets never use entry/exit data."""
    if len({f["security_id"] for f in candidates}) != len(candidates):
        raise ValueError("Duplicate allocation identity")
    if mode not in MODES:
        raise ValueError("Unsupported allocation policy")
    if not 0 < max_position <= 1 or not 0 < max_sector <= 1:
        raise ValueError("Bounded finite allocation caps required")
    accepted, excluded = [], []
    for f in candidates:
        reason = None
        if mode == "inverse_volatility":
            volatility = f.get("allocation_volatility", {})
            value = volatility.get("value")
            if value is None:
                reason = volatility.get("reason") or "MISSING_DATED_VOLATILITY"
            elif value == 0:
                reason = "ZERO_REFERENCE_VOLATILITY"
            elif not math.isfinite(value) or value < 0:
                raise ValueError("Positive finite volatility required")
        if mode == "sector_neutral" and not str(f.get("sector") or "").strip():
            reason = "MISSING_DATED_SECTOR"
        if reason:
            excluded.append(
                {
                    "security_id": f["security_id"],
                    "reason": reason,
                    "volatility": f.get("allocation_volatility"),
                }
            )
        else:
            accepted.append(f)
    counts = Counter(f["sector"] for f in accepted)
    weights: dict[str, float] = {}
    if mode == "inverse_volatility" and accepted:
        minimum = min(f["allocation_volatility"]["value"] for f in accepted)
        raw = {f["security_id"]: minimum / f["allocation_volatility"]["value"] for f in accepted}
        if any(v <= 0 for v in raw.values()):
            raise ValueError("Risk weights underflow supported bounds")
        total = sum(raw.values())
        weights = {sid: value / total for sid, value in raw.items()}
        if any(value <= 0 for value in weights.values()):
            raise ValueError("Normalized risk weights underflow supported bounds")
    else:
        for f in accepted:
            weights[f["security_id"]] = (
                max_position
                if mode == "cap_ranked"
                else 0.0
                if mode == "cash"
                else 1 / len(counts) / counts[f["sector"]]
                if mode == "sector_neutral"
                else 1 / len(accepted)
            )
    requested_sectors: dict[str, float] = defaultdict(float)
    capped_sectors: dict[str, float] = defaultdict(float)
    for f in accepted:
        sid, sector = f["security_id"], f["sector"]
        requested_sectors[sector] += weights[sid]
        capped_sectors[sector] += min(weights[sid], max_position)
    targets = []
    for f in accepted:
        sid, sector = f["security_id"], f["sector"]
        factor = min(1.0, max_sector / capped_sectors[sector]) if capped_sectors[sector] else 1.0
        weight = min(weights[sid], max_position)
        if mode != "cap_ranked":
            weight *= factor
        if weight == 0 and weights[sid] > 0:
            raise ValueError("Capped allocation weights underflow supported bounds")
        targets.append(
            {
                "security_id": sid,
                "sector": sector,
                "requested_weight": weights[sid],
                "planned_weight": weight,
                "volatility": f.get("allocation_volatility"),
                "asof_time": f["asof_time"],
                "latest_included_publication": f["latest_included_publication"],
                "source_ids": f["source_ids"],
                "selection_score": f["selection_score"],
            }
        )
    result = {
        "version": VERSION,
        "mode": mode,
        "pool_count": len(candidates),
        "accepted_count": len(accepted),
        "targets": targets,
        "exclusions": excluded,
        "requested_sector_weights": dict(sorted(requested_sectors.items())),
        "planned_weight_total": sum(t["planned_weight"] for t in targets),
        "scope": "FIXTURE_RAW_PRICES; equal-sector target is an available-sector proxy; "
        "benchmark sector history unavailable",
    }
    require_finite(result, "allocation targets")
    return result
