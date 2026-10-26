"""Explicit assumption arithmetic, never inferred investment price targets."""

from typing import Any

from pydantic import Field

from packages.shared.models import Record


class Scenario(Record):
    revenue: float = Field(gt=0, le=1e15)
    shares: float = Field(ge=1, le=1e15)
    net_debt: float = Field(default=0, ge=-1e15, le=1e15)
    growth: float = Field(ge=-0.99, le=2)
    margin: float = Field(ge=-1, le=1)
    multiple: float = Field(ge=0, le=200)
    dilution: float = Field(default=0, ge=0, le=1)
    years: int = Field(default=3, strict=True, ge=1, le=10)
    reference_price: float = Field(ge=1e-9, le=1e9)


def scenario(inputs: Scenario) -> dict[str, Any]:
    revenue = inputs.revenue * (1 + inputs.growth) ** inputs.years
    shares = inputs.shares * (1 + inputs.dilution) ** inputs.years
    # This is an enterprise operating-earnings multiple, so subtract net debt once.
    operating_earnings = revenue * inputs.margin
    enterprise = operating_earnings * inputs.multiple
    equity = max(0.0, enterprise - inputs.net_debt)
    per_share = equity / shares
    return {
        "assumptions": inputs.model_dump(),
        "revenue": revenue,
        "operating_earnings": operating_earnings,
        "diluted_shares": shares,
        "enterprise_value": enterprise,
        "equity_value": equity,
        "per_share_value": per_share,
        "annualized_change": (per_share / inputs.reference_price) ** (1 / inputs.years) - 1,
        "status": "USER_ASSUMPTIONS_NOT_A_FORECAST",
        "formula": "max(0, revenue*(1+growth)^years*operating_margin*"
        "EV_operating_earnings_multiple-net_debt) / (shares*(1+dilution)^years)",
        "limitations": [
            "No probabilities assigned",
            "Net debt is held constant by assumption",
            "No dividend, tax, discount-rate or financing model",
            "Negative earnings cannot support a positive earnings-multiple valuation",
        ],
    }
