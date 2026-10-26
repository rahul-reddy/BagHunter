"""Availability-bound statement ratios; missing metrics and incompatible units remain null."""

import math
from datetime import datetime
from typing import Any

from packages.research.features import facts_at, utc_asof
from packages.shared.models import Fact


def statement_ratios(facts: list[Fact], security_id: str, asof: datetime) -> dict[str, Any]:
    known = facts_at(facts, security_id, utc_asof(asof))
    latest: dict[tuple[str, str], Fact] = {}
    for f in known:
        latest[(f.metric, str(f.period_end))] = f
    revenues = sorted(
        (f for f in latest.values() if f.metric == "annual_revenue" and f.unit == "USD"),
        key=lambda f: f.period_end,
    )
    result: dict[str, Any] = {
        "period_end": None,
        "revenue": None,
        "revenue_growth": None,
        "operating_margin": None,
        "net_margin": None,
        "cashflow_margin": None,
        "revenue_growth_acceleration": None,
        "citations": [],
        "numeric_limits": [],
    }
    if not revenues:
        return result
    current = revenues[-1]
    result["period_end"], result["revenue"] = str(current.period_end), current.value
    used = [current]

    def finite(value: float, field: str) -> float | None:
        if not math.isfinite(value):
            result["numeric_limits"].append(field)
            return None
        return value

    growths = []
    for left, right in zip(revenues[-3:-1], revenues[-2:], strict=False):
        if left.value > 0 and 330 <= (right.period_end - left.period_end).days <= 400:
            growths.append(finite(right.value / left.value - 1, "growth_history"))
    if len(revenues) >= 2:
        before = revenues[-2]
        if before.value > 0 and 330 <= (current.period_end - before.period_end).days <= 400:
            result["revenue_growth"] = finite(current.value / before.value - 1, "revenue_growth")
            used.append(before)
    if len(growths) == 2 and growths[-1] is not None and growths[-2] is not None:
        result["revenue_growth_acceleration"] = finite(
            growths[-1] - growths[-2],
            "revenue_growth_acceleration",
        )
        used.extend(revenues[-3:])
    for metric, field in [
        ("annual_operating_income", "operating_margin"),
        ("annual_net_income", "net_margin"),
        ("annual_operating_cashflow", "cashflow_margin"),
    ]:
        value = latest.get((metric, str(current.period_end)))
        if value is not None and value.unit == current.unit and current.value > 0:
            result[field] = finite(value.value / current.value, field)
            used.append(value)
    result["citations"] = [
        f.model_dump(mode="json")
        for _, f in sorted({(f.metric, str(f.period_end), f.accession): f for f in used}.items())
    ]
    return result
