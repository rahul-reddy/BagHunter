"""Daily marked-equity diagnostics with explicit sampling and risk-free assumptions."""

import math
from datetime import date
from statistics import mean, pstdev, stdev
from typing import Any


def daily_risk(curve: list[dict[str, Any]]) -> dict[str, Any]:
    if not curve:
        return {"status": "NO_DAILY_EQUITY", "observations": 0}
    dates = [date.fromisoformat(row["date"]) for row in curve]
    values = [row["equity"] for row in curve]
    if dates != sorted(set(dates)) or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Invalid daily equity dates or marks")
    if values[0] <= 0:
        raise ValueError("Positive initial equity required")
    peak = values[0]
    drawdown = 0.0
    underwater = longest = 0
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
        underwater = underwater + 1 if value < peak else 0
        longest = max(longest, underwater)
    days = (dates[-1] - dates[0]).days
    returns = [
        right / left - 1 for left, right in zip(values[:-1], values[1:], strict=True) if left > 0
    ]
    exhausted = any(value == 0 for value in values[:-1])
    sd = stdev(returns) if len(returns) >= 2 and not exhausted else None
    downside = (
        math.sqrt(mean(min(v, 0) ** 2 for v in returns)) if returns and not exhausted else None
    )
    average = mean(returns) if returns and not exhausted else None
    population_sd = pstdev(returns) if len(returns) >= 2 and not exhausted else 0
    return {
        "status": "FIXTURE_DAILY_CLOSE_MARKS_NOT_EMPIRICAL_VALIDATION",
        "observations": len(values),
        "period_start": str(dates[0]),
        "period_end": str(dates[-1]),
        "total_return": values[-1] / values[0] - 1,
        "cagr": (values[-1] / values[0]) ** (365.25 / days) - 1 if days else None,
        "max_drawdown": drawdown,
        "maximum_underwater_sessions": longest,
        "annualized_volatility": sd * math.sqrt(252) if sd is not None else None,
        "sharpe_zero_risk_free": average / sd * math.sqrt(252)
        if average is not None and sd
        else None,
        "sortino_zero_target": average / downside * math.sqrt(252)
        if average is not None and downside
        else None,
        "worst_daily_return": min(returns) if returns else None,
        "daily_tail_5pct": sorted(returns)[int((len(returns) - 1) * 0.05)] if returns else None,
        "skewness": mean((v - mean(returns)) ** 3 for v in returns) / population_sd**3
        if population_sd
        else None,
        "ratio_status": "UNDEFINED_AFTER_EQUITY_EXHAUSTION"
        if exhausted
        else "ZERO_VARIANCE_RATIOS_MAY_BE_UNDEFINED",
        "assumptions": [
            "Daily close marks include known cash, distributions and costs",
            "252 sessions/year for volatility and ratios; zero risk-free/target return",
            "Calendar-day CAGR; fixture weekdays are not an exchange calendar",
            "Close-to-close drawdown excludes intraday extrema",
        ],
    }
