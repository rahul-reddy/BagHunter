"""Descriptive SEC entity financials at one frozen clock; no security mapping or scoring."""

import math
from datetime import datetime, timedelta
from typing import Any

from packages.shared.models import Fact


def financial_profile(normalized: dict[str, Any]) -> dict[str, Any]:
    clock = datetime.fromisoformat(normalized["asof"])
    lag = normalized["processing_lag_hours"]
    if clock.utcoffset() is None or type(lag) is not int or not 0 <= lag <= 720:
        raise ValueError("Invalid SEC profile availability policy")
    latest: dict[tuple[str, str], Fact] = {}
    for raw in normalized["facts"]:
        fact = Fact.model_validate(raw)
        if fact.security_id != normalized["security_id"]:
            raise ValueError("SEC profile entity mismatch")
        if max(fact.published_at, fact.accepted_at) + timedelta(hours=lag) > clock:
            continue
        key = (fact.metric, str(fact.period_end))
        previous = latest.get(key)
        if previous is None or (fact.published_at, fact.accepted_at, fact.accession) > (
            previous.published_at,
            previous.accepted_at,
            previous.accession,
        ):
            latest[key] = fact
    revenues = sorted(
        (f for f in latest.values() if f.metric == "annual_revenue"), key=lambda f: f.period_end
    )
    result: dict[str, Any] = {
        "policy": "sec-entity-profile-v1",
        "asof": normalized["asof"],
        "security_id": normalized["security_id"],
        "periods": len(revenues),
        "status": "DESCRIPTIVE_ENTITY_FINANCIALS_NOT_SECURITY_RANKING",
        "latest": None,
        "series": [],
        "limitations": [
            "Latest available revision at the bundle clock, not knowledge at the period end",
            "Annual USD entity-wide amounts; no per-share valuation, security eligibility or rank",
            "Growth requires adjacent 330–400-day annual ends and positive prior revenue",
            "Margins require same-period USD numerator and positive revenue; missing stays null",
            "Original extraction vintages and class identity are not certified",
        ],
    }
    if len(revenues) > 200:
        result["status"] = "PROFILE_PERIOD_LIMIT_EXCEEDED"
        return result

    def ratio(left: float, right: float) -> float | None:
        value = left / right if right > 0 else None
        return value if value is not None and math.isfinite(value) else None

    for i, revenue in enumerate(revenues):
        row: dict[str, Any] = {
            "period_end": str(revenue.period_end),
            "revenue": revenue.value if revenue.unit == "USD" else None,
            "revenue_growth": None,
            "growth_acceleration": None,
            "operating_income": None,
            "net_income": None,
            "operating_cashflow": None,
            "operating_margin": None,
            "net_margin": None,
            "cashflow_margin": None,
            "citations": [revenue.model_dump(mode="json")],
        }
        if i:
            prior = revenues[i - 1]
            if (
                revenue.unit == prior.unit == "USD"
                and 330 <= (revenue.period_end - prior.period_end).days <= 400
            ):
                growth = ratio(revenue.value, prior.value)
                row["revenue_growth"] = growth - 1 if growth is not None else None
                row["citations"].append(prior.model_dump(mode="json"))
        for metric, amount, margin in (
            ("annual_operating_income", "operating_income", "operating_margin"),
            ("annual_net_income", "net_income", "net_margin"),
            ("annual_operating_cashflow", "operating_cashflow", "cashflow_margin"),
        ):
            numerator = latest.get((metric, str(revenue.period_end)))
            if numerator is not None and numerator.unit == revenue.unit == "USD":
                row[amount] = numerator.value
                row[margin] = ratio(numerator.value, revenue.value)
                row["citations"].append(numerator.model_dump(mode="json"))
        if (
            i
            and row["revenue_growth"] is not None
            and result["series"][-1]["revenue_growth"] is not None
        ):
            acceleration = row["revenue_growth"] - result["series"][-1]["revenue_growth"]
            row["growth_acceleration"] = acceleration if math.isfinite(acceleration) else None
        result["series"].append(row)
    result["latest"] = result["series"][-1] if result["series"] else None
    return result
