"""Long-only constrained fixture simulation with explicit cash, costs and corporate actions."""

import hashlib
import math
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from packages.backtest.allocation import MODES, Allocation, allocation_targets, dated_volatility
from packages.backtest.risk import daily_risk
from packages.backtest.validation import performance
from packages.research.features import eligible, snapshot
from packages.research.outcomes import wealth_path
from packages.shared.models import Dataset, Record
from packages.shared.numeric import require_finite


class PortfolioPolicy(Record):
    selector: Literal["momentum_63d", "momentum_12_1", "revenue_growth", "seeded_random"] = (
        "momentum_63d"
    )
    allocation: Allocation = "cap_ranked"
    volatility_window: Literal[20, 60] = 60
    seed: int = 7
    capital: float = Field(default=100_000, gt=0, le=1e12)
    max_position: float = Field(default=0.25, gt=0, le=1)
    max_sector: float = Field(default=0.5, gt=0, le=1)
    participation: float = Field(default=0.01, gt=0, le=0.1)
    min_dollar_volume: float = Field(default=1_000_000, ge=0)
    min_price: float = Field(default=1, gt=0)
    one_way_cost_bps: float = Field(default=20, ge=0, le=1000)


def simulate(dataset: Dataset, policy: PortfolioPolicy) -> dict[str, Any]:
    try:
        result = _simulate(dataset, policy)
        require_finite(result, "constrained portfolio")
        return result
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Constrained portfolio exceeds finite numeric bounds") from exc


def _simulate(dataset: Dataset, policy: PortfolioPolicy) -> dict[str, Any]:
    sessions = sorted({b.session for b in dataset.bars})
    lookup = {(b.security_id, b.session): b for b in dataset.bars}
    capital = policy.capital
    rows = []
    executions = []
    exclusions = []
    allocation_ledger = []
    curve: list[dict[str, Any]] = []
    cost_rate = policy.one_way_cost_bps / 10000
    instruments = {i.security_id: i for i in dataset.instruments}
    for index in range(260, min(1000, len(sessions) - 23), 42):
        if capital <= 0:
            break
        decision, entry, exit_day = sessions[index], sessions[index + 1], sessions[index + 22]
        clock = datetime(decision.year, decision.month, decision.day, 23, tzinfo=UTC)
        candidates = []
        for instrument in dataset.instruments:
            if not eligible(instrument, clock):
                continue
            try:
                f = snapshot(instrument, dataset.bars, dataset.facts, clock)
            except ValueError as exc:
                if "insufficient price history" not in str(exc):
                    raise
                exclusions.append(
                    {
                        "decision": str(decision),
                        "security_id": instrument.security_id,
                        "reason": "INSUFFICIENT_DATED_SELECTION_HISTORY",
                    }
                )
                continue
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
            f["sector"] = instrument.sector
            if policy.allocation == "inverse_volatility":
                f["allocation_volatility"] = dated_volatility(
                    dataset.bars, instrument.security_id, clock, policy.volatility_window
                )
            candidates.append(f)
        candidates.sort(key=lambda f: (-f["selection_score"], f["security_id"]))
        plan = allocation_targets(
            candidates, policy.allocation, policy.max_position, policy.max_sector
        )
        allocation_ledger.append(
            {"decision": str(decision), "asof_time": clock.isoformat(), **plan}
        )
        exclusions.extend({"decision": str(decision), **row} for row in plan["exclusions"])
        targets = {row["security_id"]: row for row in plan["targets"]}
        starting = capital
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
            if sid not in targets or targets[sid]["planned_weight"] == 0:
                continue
            first = lookup.get((sid, entry))
            sector = instruments[sid].sector
            budget = min(
                starting * targets[sid]["planned_weight"],
                starting * policy.max_sector - sector_allocated.get(sector, 0),
                f["dollar_volume_20d"] * policy.participation,
                cash,
            )
            if first is None:
                exclusions.append(
                    {"decision": str(decision), "security_id": sid, "reason": "MISSING_ENTRY"}
                )
                continue
            unit_cost = first.open * (1 + cost_rate)
            require_finite([budget, unit_cost], "execution budget and unit cost")
            shares = math.floor(budget / unit_cost)
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
                    "requested_weight": targets[sid]["requested_weight"],
                    "planned_weight": targets[sid]["planned_weight"],
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
        allocation_ledger[-1].update(
            entry_cash_fraction=cash / starting,
            realized_sector_weights={
                key: value / starting for key, value in sorted(sector_allocated.items())
            },
        )
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
                "entry_cash_fraction": cash / starting,
                "sector_entry_weights": {
                    key: value / starting for key, value in sorted(sector_allocated.items())
                },
            }
        )
    return {
        "mode": "FIXTURE",
        "status": "CONSTRAINED_SIMULATION_NOT_EMPIRICAL_VALIDATION",
        "policy": policy.model_dump(),
        "rows": rows,
        "executions": executions,
        "exclusions": exclusions,
        "allocation_ledger": allocation_ledger,
        "metrics": performance(rows, "net_return"),
        "daily_curve": curve,
        "daily_risk": daily_risk(curve),
        "ending_equity": capital,
        "limitations": [
            "Whole-share rounding; no leverage or borrowing",
            "Allocation envelopes include entry costs; unfilled/capped targets stay in cash "
            "without redistribution",
            "Inverse volatility uses dated population simple-return volatility; "
            "zero/missing risk is excluded",
            "Sector-neutral allocation means equal-sector targets among available sectors; "
            "realized weights can drift under caps/rounding",
            "Flat cash between independent windows; no cash yield",
            "Participation uses prior known 20-session dollar volume, not future execution volume",
            "Constant one-way costs combine commissions/spread/slippage; no calibrated impact",
            "Weekday fixture calendar; no real executable-return claim",
        ],
    }


def comparator_runs(dataset: Dataset, policy: PortfolioPolicy) -> list[dict[str, Any]]:
    """Predeclared one-axis variations; preserve every ledger, not only favorable summaries."""
    variations = []
    if policy.allocation != "cash":
        for selector in ("momentum_63d", "momentum_12_1", "revenue_growth", "seeded_random"):
            if selector != policy.selector:
                variations.append({"selector": selector})
    variations.extend({"allocation": mode} for mode in MODES if mode != policy.allocation)
    result = []
    for variation in variations:
        changed = PortfolioPolicy.model_validate(policy.model_dump() | variation)
        report = simulate(dataset, changed)
        result.append({"id": f"{changed.selector}__{changed.allocation}", **report})
    return result
