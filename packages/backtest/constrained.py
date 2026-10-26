"""Long-only constrained fixture simulation with explicit cash, costs and corporate actions."""

import hashlib
import math
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from packages.backtest.risk import daily_risk
from packages.backtest.validation import performance
from packages.research.features import eligible, snapshot
from packages.research.outcomes import wealth_path
from packages.shared.models import Dataset, Record


class PortfolioPolicy(Record):
    selector: Literal["momentum_63d", "momentum_12_1", "revenue_growth", "seeded_random"] = (
        "momentum_63d"
    )
    seed: int = 7
    capital: float = Field(default=100_000, gt=0, le=1e12)
    max_position: float = Field(default=0.25, gt=0, le=1)
    max_sector: float = Field(default=0.5, gt=0, le=1)
    participation: float = Field(default=0.01, gt=0, le=0.1)
    min_dollar_volume: float = Field(default=1_000_000, ge=0)
    min_price: float = Field(default=1, gt=0)
    one_way_cost_bps: float = Field(default=20, ge=0, le=1000)


def simulate(dataset: Dataset, policy: PortfolioPolicy) -> dict[str, Any]:
    sessions = sorted({b.session for b in dataset.bars})
    lookup = {(b.security_id, b.session): b for b in dataset.bars}
    capital = policy.capital
    rows = []
    executions = []
    exclusions = []
    curve: list[dict[str, Any]] = []
    cost_rate = policy.one_way_cost_bps / 10000
    instruments = {i.security_id: i for i in dataset.instruments}
    for index in range(260, min(1000, len(sessions) - 23), 42):
        decision, entry, exit_day = sessions[index], sessions[index + 1], sessions[index + 22]
        clock = datetime(decision.year, decision.month, decision.day, 23, tzinfo=UTC)
        candidates = []
        for instrument in dataset.instruments:
            if not eligible(instrument, clock):
                continue
            f = snapshot(instrument, dataset.bars, dataset.facts, clock)
            if policy.selector == "momentum_12_1":
                known = sorted(
                    (
                        b
                        for b in dataset.bars
                        if b.security_id == instrument.security_id
                        and b.session <= decision
                        and b.available_at <= clock
                    ),
                    key=lambda b: b.session,
                )
                if len(known) < 253:
                    exclusions.append(
                        {
                            "decision": str(decision),
                            "security_id": instrument.security_id,
                            "reason": "MISSING_12_1_HISTORY",
                        }
                    )
                    continue
                f["selection_score"] = known[-22].close / known[-253].close - 1
            elif policy.selector == "revenue_growth":
                if f["revenue_growth"] is None:
                    exclusions.append(
                        {
                            "decision": str(decision),
                            "security_id": instrument.security_id,
                            "reason": "MISSING_DATED_REVENUE_GROWTH",
                        }
                    )
                    continue
                f["selection_score"] = f["revenue_growth"]
            elif policy.selector == "seeded_random":
                digest = hashlib.sha256(
                    f"{policy.seed}:{decision}:{instrument.security_id}".encode()
                ).hexdigest()
                f["selection_score"] = int(digest[:16], 16) / 2**64
            else:
                f["selection_score"] = f["return_63d"]
            if f["close"] < policy.min_price or f["dollar_volume_20d"] < policy.min_dollar_volume:
                exclusions.append(
                    {
                        "decision": str(decision),
                        "security_id": instrument.security_id,
                        "reason": "PRICE_OR_LIQUIDITY_FLOOR",
                    }
                )
                continue
            candidates.append(f)
        candidates.sort(key=lambda f: (-f["selection_score"], f["security_id"]))
        starting = capital
        if starting <= 0:
            break
        cash = capital
        last_mark = curve[-1]["date"] if curve else ""
        for day in sessions[: index + 1]:
            if str(day) > last_mark and (curve or day == decision):
                curve.append({"date": str(day), "equity": starting, "basis": "CASH_GAP"})
        holdings: list[dict[str, Any]] = []
        terminal_cash = 0.0
        sector_allocated: dict[str, float] = {}
        deployed = 0.0
        fees = 0.0
        sold = 0.0
        for f in candidates:
            sid = f["security_id"]
            first = lookup.get((sid, entry))
            sector = instruments[sid].sector
            budget = min(
                starting * policy.max_position,
                starting * policy.max_sector - sector_allocated.get(sector, 0),
                f["dollar_volume_20d"] * policy.participation,
                cash,
            )
            if first is None:
                exclusions.append(
                    {"decision": str(decision), "security_id": sid, "reason": "MISSING_ENTRY"}
                )
                continue
            shares = math.floor(budget / (first.open * (1 + cost_rate)))
            if shares < 1:
                exclusions.append(
                    {
                        "decision": str(decision),
                        "security_id": sid,
                        "reason": "CONSTRAINT_OR_MINIMUM_LOT",
                    }
                )
                continue
            bars = [b for b in dataset.bars if b.security_id == sid]
            events = [a for a in dataset.actions if a.security_id == sid]
            # Entry is next open. Ex-date actions on entry do not accrue to a new holder.
            path = wealth_path(bars, events, entry, exit_day)
            delisted = any(
                a.kind == "delist" and entry < a.effective_date <= exit_day for a in events
            )
            last = lookup.get((sid, exit_day))
            if last is None and not delisted:
                raise ValueError("Unresolved portfolio exit; no zero-return fallback")
            # Final wealth includes cash distributions. Only sale/delist proceeds incur exit cost.
            ratio = 1.0
            dividends = 0.0
            for action in sorted(
                (a for a in events if entry < a.effective_date <= exit_day),
                key=lambda a: (a.effective_date, {"split": 0, "dividend": 1, "delist": 2}[a.kind]),
            ):
                if action.kind == "split":
                    ratio *= action.value
                elif action.kind == "dividend":
                    dividends += ratio * action.value
                else:
                    ratio = 0.0
            terminal = path[-1][1]
            proceeds = max(0.0, terminal - dividends)
            buy_notional = shares * first.open
            entry_cost = buy_notional * cost_rate
            exit_cost = shares * proceeds * cost_rate
            fee_date = min(
                (
                    a.effective_date
                    for a in events
                    if a.kind == "delist" and entry < a.effective_date <= exit_day
                ),
                default=exit_day,
            )
            holdings.append(
                {
                    "shares": shares,
                    "marks": dict(path),
                    "delisted": delisted,
                    "terminal": terminal,
                    "fee_date": fee_date,
                    "exit_cost": exit_cost,
                }
            )
            cash -= buy_notional + entry_cost
            terminal_cash += shares * terminal - exit_cost
            deployed += buy_notional
            sold += shares * proceeds
            fees += entry_cost + exit_cost
            sector_allocated[sector] = sector_allocated.get(sector, 0) + buy_notional + entry_cost
            executions.append(
                {
                    "decision": str(decision),
                    "entry": str(entry),
                    "exit": str(exit_day),
                    "security_id": sid,
                    "sector": sector,
                    "shares": shares,
                    "entry_price": first.open,
                    "entry_notional": buy_notional,
                    "starting_capital": starting,
                    "capacity_limit": f["dollar_volume_20d"] * policy.participation,
                    "entry_cost": entry_cost,
                    "exit_cost": exit_cost,
                    "terminal_wealth": shares * terminal,
                    "delisted": delisted,
                }
            )
        for day in sessions[index + 1 : index + 23]:
            equity = cash
            for holding in holdings:
                mark = holding["marks"].get(day)
                if mark is None:
                    if holding["delisted"] and day >= holding["fee_date"]:
                        mark = holding["terminal"]
                    else:
                        raise ValueError("Missing daily portfolio mark; cannot infer flat equity")
                equity += holding["shares"] * mark
                if day >= holding["fee_date"]:
                    equity -= holding["exit_cost"]
            curve.append({"date": str(day), "equity": equity, "basis": "DAILY_CLOSE_AND_CASH"})
        capital = cash + terminal_cash
        if not math.isclose(curve[-1]["equity"], capital, rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("Daily portfolio marks do not reconcile to terminal cash")
        rows.append(
            {
                "decision": str(decision),
                "entry": str(entry),
                "exit": str(exit_day),
                "net_return": capital / starting - 1,
                "ending_equity": capital,
                "deployment_fraction": deployed / starting,
                "costs": fees,
                "turnover": (deployed + sold) / starting,
            }
        )
    return {
        "mode": "FIXTURE",
        "status": "CONSTRAINED_SIMULATION_NOT_EMPIRICAL_VALIDATION",
        "policy": policy.model_dump(),
        "rows": rows,
        "executions": executions,
        "exclusions": exclusions,
        "metrics": performance(rows, "net_return"),
        "daily_curve": curve,
        "daily_risk": daily_risk(curve),
        "ending_equity": capital,
        "limitations": [
            "Whole-share rounding; no leverage or borrowing",
            "Flat cash between independent windows; no cash yield",
            "Participation uses prior known 20-session dollar volume, not future execution volume",
            "Constant one-way costs combine commissions/spread/slippage; no calibrated impact",
            "Weekday fixture calendar; no real executable-return claim",
        ],
    }
