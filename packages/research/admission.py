"""Dated capitalization and annual-earnings inputs; missing is never zero or revenue growth."""

import json
import math
from datetime import datetime
from typing import Any

from packages.research.features import facts_at, utc_asof
from packages.shared.models import CapitalizationObservation, Fact


def capitalization_at(
    records: list[CapitalizationObservation],
    security_id: str,
    asof: datetime,
    max_age_days: int = 5,
) -> dict[str, Any]:
    clock = utc_asof(asof)
    if type(max_age_days) is not int or not 0 <= max_age_days <= 365:
        raise ValueError("Bounded capitalization age required")
    result: dict[str, Any] = {
        "status": "NO_KNOWN_DATED_USD_CAPITALIZATION",
        "value_usd": None,
        "evidence": [],
    }
    known = []
    for record in records:
        row = CapitalizationObservation.model_validate(record.model_dump())
        if (
            row.security_id == security_id
            and row.observed_at <= clock
            and row.published_at <= clock
            and clock < row.valid_until
        ):
            known.append(row)
    if not known:
        return result
    observed = max(row.observed_at for row in known)
    known = [row for row in known if row.observed_at == observed]
    latest: dict[str, list[CapitalizationObservation]] = {}
    for row in known:
        previous = latest.get(row.source_id, [])
        if not previous or row.published_at > previous[0].published_at:
            latest[row.source_id] = [row]
        elif row.published_at == previous[0].published_at:
            previous.append(row)
    selected = [row for revisions in latest.values() for row in revisions]
    evidence = sorted(
        [row.model_dump(mode="json") for row in selected],
        key=lambda row: json.dumps(row, sort_keys=True),
    )
    if (clock.date() - utc_asof(observed).date()).days > max_age_days:
        return {**result, "status": "STALE_DATED_CAPITALIZATION", "evidence": evidence}
    values = {row.value_usd for row in selected}
    if len(values) != 1:
        return {**result, "status": "AMBIGUOUS_DATED_CAPITALIZATION", "evidence": evidence}
    return {
        "status": "KNOWN_DATED_USD_CAPITALIZATION",
        "value_usd": next(iter(values)),
        "evidence": evidence,
    }


def annual_earnings_growth(
    facts: list[Fact],
    security_id: str,
    asof: datetime,
    lag_hours: int = 24,
    max_age_days: int = 550,
) -> dict[str, Any]:
    if type(lag_hours) is not int or not 24 <= lag_hours <= 720:
        raise ValueError("Annual earnings require the declared filing lag")
    clock = utc_asof(asof)
    if type(max_age_days) is not int or not 0 <= max_age_days <= 730:
        raise ValueError("Bounded annual earnings age required")
    known = [
        fact
        for fact in facts_at(facts, security_id, asof, lag_hours)
        if fact.metric == "annual_net_income"
    ]
    missing: dict[str, Any] = {
        "status": "MISSING_DATED_ANNUAL_NET_INCOME_PAIR",
        "value": None,
        "evidence": [],
    }
    periods = sorted({fact.period_end for fact in known})
    if len(periods) < 2:
        return missing
    selected = []
    for period in periods[-2:]:
        values = [fact for fact in known if fact.period_end == period]
        version = max(
            (utc_asof(f.published_at), utc_asof(f.accepted_at), f.accession) for f in values
        )
        latest = [
            f
            for f in values
            if (utc_asof(f.published_at), utc_asof(f.accepted_at), f.accession) == version
        ]
        usd = [f for f in latest if f.unit == "USD"]
        if not usd:
            return {
                **missing,
                "status": "UNSUPPORTED_LATEST_ANNUAL_EARNINGS_UNIT",
                "evidence": [f.model_dump(mode="json", exclude_unset=True) for f in latest],
            }
        if len({f.value for f in usd}) != 1:
            return {
                **missing,
                "status": "AMBIGUOUS_KNOWN_ANNUAL_EARNINGS",
                "evidence": [f.model_dump(mode="json", exclude_unset=True) for f in usd],
            }
        selected.append(
            sorted(usd, key=lambda f: json.dumps(f.model_dump(mode="json"), sort_keys=True))[0]
        )
    prior, current = selected
    evidence = [row.model_dump(mode="json", exclude_unset=True) for row in selected]
    if (clock.date() - current.period_end).days > max_age_days:
        return {**missing, "status": "STALE_ANNUAL_EARNINGS_INPUTS", "evidence": evidence}
    if not 330 <= (current.period_end - prior.period_end).days <= 400:
        return {**missing, "status": "NONADJACENT_ANNUAL_EARNINGS_PERIODS", "evidence": evidence}
    if prior.value <= 0:
        return {**missing, "status": "NONPOSITIVE_PRIOR_ANNUAL_EARNINGS", "evidence": evidence}
    value = current.value / prior.value - 1
    if not math.isfinite(value):
        return {**missing, "status": "UNREPRESENTABLE_ANNUAL_EARNINGS_GROWTH", "evidence": evidence}
    return {"status": "DATED_ANNUAL_NET_INCOME_GROWTH", "value": value, "evidence": evidence}
