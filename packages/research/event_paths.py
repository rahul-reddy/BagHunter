"""Calendar-anchored descriptive paths; outcome grouping never enters snapshot construction."""

import hashlib
import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from pydantic import Field

from packages.data.finviz import _json
from packages.research.features import VERSION, eligible, snapshot, symbol_at, utc_asof
from packages.research.fundamentals import statement_ratios
from packages.research.outcomes import matched_pairs, outcome
from packages.research.technical import technical_evidence
from packages.shared.models import Bar, Dataset, Fact, Instrument, Record, Symbol
from packages.shared.numeric import require_finite

OFFSETS = (-120, -60, -20, 0, 20)
MAX_POINTS = 2048


class EventPathPolicy(Record):
    version: Literal["calendar-event-paths-v1"] = "calendar-event-paths-v1"
    anchor_rule: Literal["FIRST_FIXTURE_WEEKDAY_EACH_QUARTER"] = (
        "FIRST_FIXTURE_WEEKDAY_EACH_QUARTER"
    )
    horizon_years: Literal[1, 2, 3, 5] = 1
    max_hit_threshold: float = Field(default=5.0, ge=1, le=100)
    seed: int = 7


def path_snapshot(
    instrument: Instrument,
    bars: list[Bar],
    facts: list[Fact],
    symbols: list[Symbol],
    clock: datetime,
) -> dict[str, Any]:
    """No labels, actions, peer groups or other point snapshots are accepted."""
    clock = utc_asof(clock)
    base = snapshot(instrument, bars, facts, clock)
    values = {
        key: base[key]
        for key in (
            "close",
            "return_1d",
            "return_5d",
            "return_21d",
            "return_63d",
            "ema_8",
            "ema_21",
            "dollar_volume_20d",
            "relative_volume",
            "price_session",
            "source_ids",
            "latest_included_publication",
            "evidence",
        )
    }
    values.update(
        ticker=symbol_at(symbols, instrument.security_id, clock),
        asof_time=clock.isoformat(),
        feature_version=VERSION,
        technical=technical_evidence(bars, instrument.security_id, clock),
        financials=statement_ratios(facts, instrument.security_id, clock),
    )
    require_finite(values, "event path snapshot")
    return values


def event_study(dataset: Dataset, policy: EventPathPolicy) -> dict[str, Any]:
    days = [b.session for b in dataset.bars]
    if not days or (max(days) - min(days)).days > 6000:
        raise ValueError("Event paths require a bounded nonempty fixture calendar")
    if any(day.weekday() >= 5 for day in days):
        raise ValueError("Fixture weekday calendar rejects weekend observations")
    if len(dataset.instruments) > 32 or len({i.security_id for i in dataset.instruments}) != len(
        dataset.instruments
    ):
        raise ValueError("Event paths require at most 32 unique instruments")
    start, end = min(days), max(days)
    calendar = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    ]
    first: dict[tuple[int, int], int] = {}
    for index, calendar_day in enumerate(calendar):
        first.setdefault((calendar_day.year, (calendar_day.month - 1) // 3), index)
    if len(first) > 64:
        raise ValueError("Event paths exceed the 64-anchor limit")
    anchors: list[dict[str, Any]] = []
    points_used = 0
    # Build every member's dated snapshots before consulting any outcome or case/control label.
    for index in first.values():
        anchor = calendar[index]
        anchor_clock = datetime.combine(anchor, time(23), UTC)
        members = []
        for instrument in sorted(dataset.instruments, key=lambda i: i.security_id):
            if not eligible(instrument, anchor_clock):
                continue
            points_used += len(OFFSETS)
            if points_used > MAX_POINTS:
                raise ValueError("Event paths exceed the point budget; no silent truncation")
            points = []
            for offset in OFFSETS:
                position = index + offset
                day = calendar[position] if 0 <= position < len(calendar) else None
                clock = datetime.combine(day, time(23), UTC) if day else None
                point: dict[str, Any] = {
                    "offset": offset,
                    "point_session": str(day) if day else None,
                    "asof_time": clock.isoformat() if clock else None,
                    "timing": "POST_ANCHOR_DESCRIPTIVE_ONLY" if offset > 0 else "KNOWN_BY_ANCHOR",
                    "status": "OUTSIDE_FIXTURE_CALENDAR",
                    "snapshot": None,
                }
                if clock is not None:
                    if not eligible(instrument, clock):
                        point["status"] = "INELIGIBLE_AT_POINT"
                    elif not any(
                        b.security_id == instrument.security_id
                        and b.session == day
                        and b.available_at <= clock
                        for b in dataset.bars
                    ):
                        point["status"] = "NO_QUOTE_AVAILABLE_AT_POINT"
                    else:
                        try:
                            point["snapshot"] = path_snapshot(
                                instrument, dataset.bars, dataset.facts, dataset.symbols, clock
                            )
                            point["status"] = "AVAILABLE"
                        except ValueError as exc:
                            if "insufficient price history" not in str(exc):
                                raise
                            point["status"] = "INSUFFICIENT_PRICE_HISTORY"
                points.append(point)
            members.append(
                {
                    "security_id": instrument.security_id,
                    "name": instrument.name,
                    "sector": instrument.sector,
                    "points": points,
                }
            )
        anchors.append(
            {
                "anchor": str(anchor),
                "asof_time": anchor_clock.isoformat(),
                "eligible": len(members),
                "members": members,
            }
        )

    # Hindsight is attached only after all independent feature vectors have been assembled.
    for row in anchors:
        labels = []
        for member in row["members"]:
            sid = member["security_id"]
            anchor = date.fromisoformat(row["anchor"])
            if any(b.security_id == sid and b.session == anchor for b in dataset.bars):
                label = outcome(sid, dataset.bars, dataset.actions, anchor, policy.horizon_years)
            else:
                label = {
                    "security_id": sid,
                    "anchor": str(anchor),
                    "horizon_years": policy.horizon_years,
                    "max_multiple": None,
                    "terminal_total_return": None,
                    "max_drawdown": None,
                    "delisted": None,
                    "coverage_flag": "MISSING_ANCHOR_QUOTE",
                }
            member["outcome"] = label
            member["outcome_group"] = (
                "MISSING"
                if label["max_multiple"] is None
                else "CASE"
                if label["max_multiple"] >= policy.max_hit_threshold
                else "NONCASE"
            )
            labels.append(label)
        pairs = matched_pairs(
            dataset.instruments,
            labels,
            datetime.fromisoformat(row["asof_time"]),
            policy.seed,
            horizon_years=policy.horizon_years,
            max_hit_threshold=policy.max_hit_threshold,
        )
        row["pairs"] = pairs
        row["cases"] = sum(m["outcome_group"] == "CASE" for m in row["members"])
        row["missing_outcomes"] = sum(m["outcome_group"] == "MISSING" for m in row["members"])
        row["unmatched_cases"] = sorted(
            set(m["security_id"] for m in row["members"] if m["outcome_group"] == "CASE")
            - {p["case_security_id"] for p in pairs}
        )
    result = {
        "mode": "FIXTURE",
        "scope": "DESCRIPTIVE_HINDSIGHT_PATHS_NOT_PREDICTORS_OR_EMPIRICAL_INFERENCE",
        "policy": policy.model_dump(mode="json"),
        "policy_sha256": hashlib.sha256(_json(policy.model_dump(mode="json"))).hexdigest(),
        "offsets": list(OFFSETS),
        "calendar": {
            "basis": "SYNTHETIC_WEEKDAYS_NOT_EXCHANGE_SESSIONS",
            "start": str(start),
            "end": str(end),
            "sessions": len(calendar),
            "sha256": hashlib.sha256(_json([str(d) for d in calendar])).hexdigest(),
        },
        "anchors": anchors,
        "points": points_used,
        "limitations": [
            "Calendar/offset policy is declared in code; no external preregistration or holdout",
            "Eligible members and missing/unmatched groups are retained; retrospective grouping",
            "Sector is an industry proxy; matching weights are not population probabilities",
            "Later snapshots and outcomes are descriptive and excluded from gold predictors",
            "Raw closes may contain corporate actions; outcome labels use total-wealth accounting",
            "Qualitative, capital raise, customer/TAM and valuation evidence remain unsupplied",
        ],
    }
    require_finite(result, "event study")
    return result


def event_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"anchor": row["anchor"], "security_id": member["security_id"], **point}
        for row in report["anchors"]
        for member in row["members"]
        for point in member["points"]
    ]


def event_report(report: dict[str, Any] | None, run_id: str) -> str:
    lines = ["# FIXTURE descriptive event study", "", f"Run {run_id}.", ""]
    if report is None:
        return "\n".join(lines + ["Event paths unavailable in this archive.", ""])
    lines += [
        f"Policy {report['policy_sha256']}; {report['policy']['horizon_years']}Y "
        f"maximum-hit threshold {report['policy']['max_hit_threshold']}x.",
        "Quarterly fixture-weekday anchors precede outcome grouping. Every t+20 point "
        "is post-anchor descriptive hindsight, never a predictor at t.",
        "Raw closes are not total-return multiples. Outcome labels use wealth accounting.",
        "",
    ]
    for row in report["anchors"]:
        lines += [
            f"## Anchor {row['anchor']}",
            f"{row['eligible']} eligible; {row['cases']} cases; "
            f"{row['missing_outcomes']} missing outcomes; "
            f"{len(row['unmatched_cases'])} unmatched cases.",
            "",
        ]
        for pair in row["pairs"]:
            lines += [
                f"Case {pair['case_security_id']}; control {pair['control_security_id']}; "
                f"control probability {pair['control_sampling_probability']}; "
                f"sampling weight {pair['control_weight']}. Retrospective strata: "
                f"{', '.join(pair['strata'])}.",
                "",
            ]
            for sid in (pair["case_security_id"], pair["control_security_id"]):
                member = next(m for m in row["members"] if m["security_id"] == sid)
                lines += [
                    f"### {sid}",
                    "",
                    "| Offset | Session | Coverage | Raw close USD | Trailing 63 return |",
                    "| --- | --- | --- | --- | --- |",
                ]
                for point in member["points"]:
                    vector = point["snapshot"]
                    close = vector["close"] if vector else "Missing"
                    trailing = vector["return_63d"] if vector else "Missing"
                    lines.append(
                        f"| {point['offset']} | {point['point_session'] or 'Missing'} | "
                        f"{point['status']} / {point['timing']} | {close} | {trailing} |"
                    )
                outcome_text = json.dumps(member["outcome"], sort_keys=True, allow_nan=False)
                lines += [
                    "",
                    f"Separate hindsight outcome: {outcome_text}",
                    "",
                ]
                for point in member["points"]:
                    if point["snapshot"]:
                        for fact in point["snapshot"]["financials"]["citations"]:
                            lines.append(
                                f"- Offset {point['offset']}: {fact['metric']} "
                                f"{fact['value']} {fact['unit']}; period {fact['period_end']}; "
                                f"first public {fact['published_at']}; "
                                f"accession {fact['accession']}; source {fact['source_id']}."
                            )
    lines += ["", "## Limitations", *[f"- {v}" for v in report["limitations"]], ""]
    return "\n".join(lines)
