"""Hindsight outputs live here, isolated from predictor assembly."""

import random
from datetime import date, datetime
from typing import Any

from packages.research.features import eligible
from packages.shared.models import Action, Bar, Instrument


def wealth_path(
    bars: list[Bar], actions: list[Action], start: date, end: date
) -> list[tuple[date, float]]:
    """Wealth per initial share, cash dividends held without reinvestment.

    Splits apply before cash dividends on the same date. Delist value is per held share.
    Input is one instrument only, raw prices; post-delist observations are rejected.
    """
    bars = sorted(bars, key=lambda b: b.session)
    actions = sorted(actions, key=lambda a: (a.effective_date, a.kind != "split"))
    ids = {b.security_id for b in bars} | {a.security_id for a in actions}
    if len(ids) > 1:
        raise ValueError("wealth_path requires one security")
    closes = {b.session: b.close for b in bars if start <= b.session <= end}
    if not closes or min(closes) != start:
        raise ValueError("anchor price missing")
    if len(closes) != len([b for b in bars if start <= b.session <= end]):
        raise ValueError("duplicate price session")
    events: dict[date, list[Action]] = {}
    for a in actions:
        if start < a.effective_date <= end:
            events.setdefault(a.effective_date, []).append(a)
    shares, cash, dead = 1.0, 0.0, False
    path = []
    for day in sorted(set(closes) | set(events)):
        if dead and day in closes:
            raise ValueError("price after delisting")
        for action in events.get(day, []):
            if action.kind == "split":
                shares *= action.value
            elif action.kind == "dividend":
                cash += shares * action.value
            else:
                cash += shares * action.value
                shares, dead = 0, True
        if day in closes or dead:
            path.append((day, cash + shares * closes.get(day, 0)))
    return path


def outcome(
    security_id: str, bars: list[Bar], actions: list[Action], anchor: date, years: int
) -> dict[str, Any]:
    try:
        end = anchor.replace(year=anchor.year + years)
    except ValueError:
        end = anchor.replace(year=anchor.year + years, day=28)
    selected = [b for b in bars if b.security_id == security_id]
    events = [a for a in actions if a.security_id == security_id]
    path = wealth_path(selected, events, anchor, end)
    delisted = any(a.kind == "delist" and anchor < a.effective_date <= end for a in events)
    # At most a weekend gap is accepted for this WEEKDAY fixture calendar.
    complete = delisted or (end - path[-1][0]).days <= 2
    initial = path[0][1]
    multiples = [v / initial for _, v in path]
    peak, drawdown = multiples[0], 0.0
    for v in multiples:
        peak = max(peak, v)
        drawdown = min(drawdown, v / peak - 1)
    return {
        "security_id": security_id,
        "anchor": str(anchor),
        "horizon_years": years,
        "outcome_method": "raw+splits+cash-dividends-no-reinvestment-v1",
        "max_multiple": max(multiples) if complete else None,
        "terminal_total_return": multiples[-1] - 1 if complete else None,
        "max_drawdown": drawdown if complete else None,
        "delisted": delisted,
        "coverage_flag": "COMPLETE_FIXTURE" if complete else "INCOMPLETE_HORIZON",
    }


def matched_pairs(
    instruments: list[Instrument], labels: list[dict[str, Any]], asof: datetime, seed: int
) -> list[dict[str, Any]]:
    pool = {i.security_id: i for i in instruments if eligible(i, asof)}
    labels = [
        row
        for row in labels
        if row["anchor"] == str(asof.date())
        and row["horizon_years"] == 1
        and row["max_multiple"] is not None
    ]
    cases = [row for row in labels if row["max_multiple"] >= 5]
    rng = random.Random(seed)
    pairs = []
    for case in cases:
        ci = pool.get(case["security_id"])
        if ci is None:
            continue
        strata = (ci.sector, ci.cap_bucket, ci.liquidity_bucket, ci.price_bucket)
        controls = sorted(
            [
                row["security_id"]
                for row in labels
                if row["max_multiple"] < 5
                and row["security_id"] in pool
                and (
                    pool[row["security_id"]].sector,
                    pool[row["security_id"]].cap_bucket,
                    pool[row["security_id"]].liquidity_bucket,
                    pool[row["security_id"]].price_bucket,
                )
                == strata
            ]
        )
        if controls:
            pairs.append(
                {
                    "anchor": str(asof.date()),
                    "case_security_id": ci.security_id,
                    "control_security_id": rng.choice(controls),
                    "strata": strata,
                    "matching_seed": seed,
                    "control_sampling_probability": 1 / len(controls),
                    "control_weight": len(controls),
                    "scope": "Retrospective fixture case/control; NOT population hit rates",
                }
            )
    return pairs
