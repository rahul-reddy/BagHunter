"""Dated classification and raw-benchmark context, independent of hindsight outcomes."""

from datetime import UTC, datetime, timedelta
from typing import Any

from packages.research.features import utc_asof
from packages.shared.models import Bar, Dataset, IndustryClassification
from packages.shared.numeric import require_finite


def industry_at(
    records: list[IndustryClassification], security_id: str, asof: datetime
) -> dict[str, Any]:
    clock = utc_asof(asof)
    result: dict[str, Any] = {
        "asof": clock.isoformat(),
        "status": "NO_KNOWABLE_CLASSIFICATION",
        "industry": None,
        "industry_version": None,
        "source_ids": [],
        "latest_publication": None,
    }
    groups: dict[tuple[Any, ...], list[IndustryClassification]] = {}
    for source in records:
        row = IndustryClassification.model_validate(source.model_dump())
        if (
            row.security_id != security_id
            or row.published_at > clock
            or row.valid_from > clock.date()
            or (row.valid_to is not None and clock.date() >= row.valid_to)
        ):
            continue
        key = (row.source_id, row.industry_version, row.valid_from, row.valid_to)
        groups.setdefault(key, []).append(row)
    selected: list[IndustryClassification] = []
    for revisions in groups.values():
        latest = max(row.published_at for row in revisions)
        selected.extend(row for row in revisions if row.published_at == latest)
    if not selected:
        return result
    identities = {(row.industry_version, row.industry) for row in selected}
    if len(identities) != 1:
        result["status"] = "AMBIGUOUS_KNOWN_CLASSIFICATION"
        return result
    version, industry = next(iter(identities))
    return {
        **result,
        "status": "DATED_CLASSIFICATION_AVAILABLE",
        "industry": industry,
        "industry_version": version,
        "source_ids": sorted({row.source_id for row in selected}),
        "latest_publication": max(row.published_at for row in selected).astimezone(UTC).isoformat(),
    }


def benchmark_regime(dataset: Dataset, asof: datetime) -> dict[str, Any]:
    clock = utc_asof(asof)
    result: dict[str, Any] = {
        "asof": clock.isoformat(),
        "regime": "UNAVAILABLE",
        "status": "NO_UNIQUE_DATED_BENCHMARK",
        "scope": "DATED_RAW_63_SESSION_PROXY_NOT_MACRO_REGIME",
        "benchmark_security_id": None,
        "return_63d": None,
        "latest_publication": None,
        "source_ids": [],
    }
    if dataset.mode != "FIXTURE":
        raise ValueError("Benchmark regime requires a declared fixture calendar")
    instruments = [
        item
        for item in dataset.instruments
        if item.security_type == "benchmark"
        and item.first_seen <= clock.date()
        and (item.last_seen is None or clock.date() <= item.last_seen)
    ]
    if len(instruments) != 1:
        return result
    sid = instruments[0].security_id
    result["benchmark_security_id"] = sid
    known = sorted(
        [
            bar
            for bar in dataset.bars
            if bar.security_id == sid and bar.session <= clock.date() and bar.available_at <= clock
        ],
        key=lambda bar: bar.session,
    )
    if len({bar.session for bar in known}) != len(known):
        raise ValueError("Duplicate known benchmark price session")
    if not known or known[-1].session != clock.date():
        return {**result, "status": "MISSING_ANCHOR_BENCHMARK_PRICE"}
    if len(known) < 64:
        return {**result, "status": "INSUFFICIENT_BENCHMARK_HISTORY"}
    window = [Bar.model_validate(bar.model_dump()) for bar in known[-64:]]
    if (clock.date() - window[0].session).days > 100:
        return {**result, "status": "MISSING_FIXTURE_WEEKDAY_BENCHMARK_PRICE"}
    expected = set()
    day = window[0].session
    while day <= clock.date():
        if day.weekday() < 5:
            expected.add(day)
        day += timedelta(days=1)
    if expected != {bar.session for bar in window}:
        return {**result, "status": "MISSING_FIXTURE_WEEKDAY_BENCHMARK_PRICE"}
    change = window[-1].close / window[0].close - 1
    require_finite(change, "dated benchmark return")
    return {
        **result,
        "status": "CALCULATED_RAW_FIXTURE_BENCHMARK",
        "regime": "UP_63D" if change > 0 else "DOWN_63D" if change < 0 else "FLAT_63D",
        "return_63d": change,
        "latest_publication": max(bar.available_at for bar in window).astimezone(UTC).isoformat(),
        "source_ids": sorted({bar.source_id for bar in window}),
    }
