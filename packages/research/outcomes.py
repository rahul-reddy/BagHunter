"""Hindsight outputs live here, isolated from predictor assembly."""

import math
import random
from datetime import date, datetime
from typing import Any

from packages.research.cohort_context import industry_at
from packages.research.features import eligible, utc_asof
from packages.shared.models import Action, Bar, IndustryClassification, Instrument
from packages.shared.numeric import require_finite


def wealth_path(
    bars: list[Bar], actions: list[Action], start: date, end: date
) -> list[tuple[date, float]]:
    """Wealth per initial share, cash dividends held without reinvestment.

    Same-date order: split, dividend, delisting. Delist value is per held share.
    Input is one instrument only, raw prices; post-delist observations are rejected.
    """
    bars = sorted(bars, key=lambda b: b.session)
    precedence = {"split": 0, "dividend": 1, "delist": 2}
    actions = sorted(actions, key=lambda a: (a.effective_date, precedence[a.kind]))
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
    instruments: list[Instrument],
    labels: list[dict[str, Any]],
    asof: datetime,
    seed: int,
    *,
    horizon_years: int = 1,
    max_hit_threshold: float = 5,
    industry_history: list[IndustryClassification] | None = None,
) -> list[dict[str, Any]]:
    asof = utc_asof(asof)
    if (
        type(horizon_years) is not int
        or horizon_years not in (1, 2, 3, 5)
        or type(seed) is not int
        or not 0 <= seed < 2**32
        or type(max_hit_threshold) not in (int, float)
        or not math.isfinite(max_hit_threshold)
        or not 1 <= max_hit_threshold <= 100
    ):
        raise ValueError("Bounded matching horizon/threshold required")
    require_finite(labels, "matching outcomes")
    pool = {i.security_id: i for i in instruments if eligible(i, asof)}
    labels = [
        row
        for row in labels
        if row["anchor"] == str(asof.date())
        and row["horizon_years"] == horizon_years
        and row["max_multiple"] is not None
    ]
    if len({row["security_id"] for row in labels}) != len(labels):
        raise ValueError("Duplicate matching outcome identity")
    if any(type(row["max_multiple"]) not in (int, float) for row in labels):
        raise ValueError("Matching multiple must be numeric")
    cases = sorted(
        [row for row in labels if row["max_multiple"] >= max_hit_threshold],
        key=lambda row: row["security_id"],
    )
    rng = random.Random(seed)
    pairs = []
    industry_rows: dict[str, list[IndustryClassification]] = {}
    for classification in industry_history or []:
        industry_rows.setdefault(classification.security_id, []).append(classification)
    contexts = {sid: industry_at(industry_rows.get(sid, []), sid, asof) for sid in pool}
    for case in cases:
        ci = pool.get(case["security_id"])
        if ci is None:
            continue
        case_context = contexts[ci.security_id]
        if case_context["status"] == "AMBIGUOUS_KNOWN_CLASSIFICATION":
            continue
        dated_industry = case_context["status"] == "DATED_CLASSIFICATION_AVAILABLE"
        basis = "DATED_INDUSTRY_METADATA" if dated_industry else "EXPLICIT_SECTOR_PROXY"
        grouping = (
            (case_context["industry_version"], case_context["industry"])
            if dated_industry
            else ci.sector
        )
        strata = (grouping, ci.cap_bucket, ci.liquidity_bucket, ci.price_bucket)
        controls = []
        for row in labels:
            sid = row["security_id"]
            if row["max_multiple"] >= max_hit_threshold or sid not in pool:
                continue
            instrument = pool[sid]
            context = contexts[sid]
            if context["status"] == "AMBIGUOUS_KNOWN_CLASSIFICATION":
                continue
            other_group: tuple[Any, Any] | str
            if dated_industry:
                if context["status"] != "DATED_CLASSIFICATION_AVAILABLE":
                    continue
                other_group = (context["industry_version"], context["industry"])
            else:
                other_group = instrument.sector
            if (
                other_group,
                instrument.cap_bucket,
                instrument.liquidity_bucket,
                instrument.price_bucket,
            ) == strata:
                controls.append(sid)
        controls.sort()
        if controls:
            selected_control = rng.choice(controls)
            pairs.append(
                {
                    "anchor": str(asof.date()),
                    "case_security_id": ci.security_id,
                    "control_security_id": selected_control,
                    "matching_basis": basis,
                    "case_industry_context": case_context,
                    "control_industry_context": contexts[selected_control],
                    "strata": (
                        case_context["industry_version"],
                        case_context["industry"],
                        *strata[1:],
                    )
                    if dated_industry
                    else strata,
                    "matching_seed": seed,
                    "horizon_years": horizon_years,
                    "max_hit_threshold": max_hit_threshold,
                    "control_sampling_probability": 1 / len(controls),
                    "control_weight": len(controls),
                    "scope": "Retrospective fixture case/control; NOT population hit rates",
                }
            )
    return pairs
