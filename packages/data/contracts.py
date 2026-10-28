"""Canonical research-table exports; unknown provenance stays null, never backdated."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from packages.research.features import eligible, utc_asof
from packages.shared.models import Dataset
from packages.shared.numeric import require_finite

VERSION = "canonical-research-tables-v1"


def _schema(
    required: str, optional: str = "", numbers: str = "", booleans: str = "", integers: str = ""
) -> pa.Schema:
    fields = [pa.field(name, pa.string(), nullable=False) for name in required.split()]
    fields.extend(pa.field(name, pa.string()) for name in optional.split())
    fields.extend(pa.field(name, pa.float64()) for name in numbers.split())
    fields = [field for field in fields if field.name not in booleans.split() + integers.split()]
    fields.extend(pa.field(name, pa.bool_(), nullable=False) for name in booleans.split())
    fields.extend(pa.field(name, pa.int64(), nullable=False) for name in integers.split())
    return pa.schema(
        fields, metadata={b"contract": VERSION.encode(), b"clock_encoding": b"ISO8601"}
    )


SCHEMAS = {
    "instrument": _schema(
        "permanent_security_id first_seen security_type provenance_status",
        "cik exchange last_seen identifiers_version",
    ),
    "symbol_history": _schema("security_id ticker valid_from provenance_status", "valid_to source"),
    "universe_membership": _schema(
        "security_id asof_date eligible source_snapshot_id eligibility_basis",
        "rejection_reason",
        "marketcap_asof dollar_volume",
        booleans="eligible",
    ),
    "daily_bar": _schema(
        "security_id session_date adjustment_policy source_id availability_at provenance_status",
        "vendor_recorded_at",
        "open high low close volume",
        integers="volume",
    ),
    "corporate_action": _schema(
        "security_id effective_date event_type source_id", "", "factor proceeds"
    ),
    "fundamental_fact": _schema(
        "security_id period_end filing_accepted_at published_at metric unit accession "
        "amended_flag source_url source_id provenance_status",
        "ingestion_at",
        "value",
        booleans="amended_flag",
    ),
    "event_evidence": _schema(
        "security_id event_at first_public_at evidence_type source_url raw_digest "
        "raw_digest_scope summary provenance_status",
        "",
        "classification_confidence",
    ),
    "backtest_execution": _schema(
        "run_id security_id session_date order_intent timestamp_status simulation_basis",
        "timestamp rejected_reason",
        "assumed_fill costs terminal_wealth",
    ),
    "thesis": _schema(
        "security_id asof_time scenario_assumptions citations adversarial_review version "
        "assertion_status run_id dossier_sha256"
    ),
    "source_manifest": _schema(
        "source_id provider url license_note asof_coverage checksum status retrieval_status",
        "retrieval_at",
    ),
}


def _json(value: Any) -> str:
    require_finite(value, "canonical table")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def canonical_tables(dataset: Dataset, run: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Export the saved fixture calculation, without promoting operator assertions or history."""
    from datetime import datetime

    dataset = Dataset.model_validate(dataset.model_dump())
    checksum = hashlib.sha256(dataset.model_dump_json().encode()).hexdigest()
    if (
        run["mode"] != "FIXTURE"
        or dataset.mode != "FIXTURE"
        or len(run["sources"]) != 1
        or run["sources"][0]["sha256"] != checksum
    ):
        raise ValueError("Canonical export requires its exact fixture source")
    require_finite(run, "canonical saved run")
    if not re.fullmatch(r"[a-f0-9]{16}", run["run_id"]):
        raise ValueError("Invalid canonical run ID")
    ids = {i.security_id for i in dataset.instruments}
    if any(
        row["security_id"] not in ids
        for row in run["signals"] + run["portfolio"]["executions"] + run["portfolio"]["exclusions"]
    ):
        raise ValueError("Canonical run refers to an unknown security")
    clock = utc_asof(datetime.fromisoformat(run["asof"]))
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in SCHEMAS}
    signals = {row["security_id"]: row for row in run["signals"]}
    for instrument in dataset.instruments:
        rows["instrument"].append(
            dict(
                permanent_security_id=instrument.security_id,
                cik=instrument.cik,
                exchange=instrument.exchange,
                first_seen=str(instrument.first_seen),
                last_seen=str(instrument.last_seen) if instrument.last_seen else None,
                security_type=instrument.security_type,
                identifiers_version=instrument.identifiers_version,
                provenance_status="SYNTHETIC_REFERENCE_UNKNOWN_FIELDS_NULL",
            )
        )
        included = eligible(instrument, clock)
        rows["universe_membership"].append(
            dict(
                security_id=instrument.security_id,
                asof_date=clock.date().isoformat(),
                eligible=included,
                rejection_reason=None if included else "NOT_ASOF_LISTED_COMMON_SHARE",
                marketcap_asof=None,
                dollar_volume=signals.get(instrument.security_id, {}).get("dollar_volume_20d"),
                source_snapshot_id=checksum,
                eligibility_basis="FIXTURE_LISTING_TYPE_ONLY_NOT_STRATEGY_ELIGIBILITY",
            )
        )
    for symbol in dataset.symbols:
        rows["symbol_history"].append(
            dict(
                security_id=symbol.security_id,
                ticker=symbol.ticker,
                valid_from=str(symbol.valid_from),
                valid_to=str(symbol.valid_to) if symbol.valid_to else None,
                source=symbol.source,
                provenance_status="SYNTHETIC_MAPPING_SOURCE_NULL_IF_UNRECORDED",
            )
        )
    for bar in dataset.bars:
        rows["daily_bar"].append(
            dict(
                security_id=bar.security_id,
                session_date=str(bar.session),
                adjustment_policy=bar.adjustment_policy,
                source_id=bar.source_id,
                availability_at=bar.available_at.isoformat(),
                vendor_recorded_at=bar.vendor_recorded_at.isoformat()
                if bar.vendor_recorded_at
                else None,
                provenance_status="SYNTHETIC_AVAILABLE_AT_IS_NOT_VENDOR_RECORDED_AT",
                **{name: getattr(bar, name) for name in ("open", "high", "low", "close", "volume")},
            )
        )
    for action in dataset.actions:
        rows["corporate_action"].append(
            dict(
                security_id=action.security_id,
                effective_date=str(action.effective_date),
                event_type=action.kind,
                factor=action.value if action.kind == "split" else None,
                proceeds=action.value if action.kind != "split" else None,
                source_id=action.source_id,
            )
        )
    filings: dict[tuple[str, str], list[Any]] = {}
    for fact in dataset.facts:
        rows["fundamental_fact"].append(
            dict(
                security_id=fact.security_id,
                period_end=str(fact.period_end),
                filing_accepted_at=fact.accepted_at.isoformat(),
                published_at=fact.published_at.isoformat(),
                metric=fact.metric,
                unit=fact.unit,
                accession=fact.accession,
                amended_flag=fact.amended,
                source_url=fact.source_url,
                source_id=fact.source_id,
                ingestion_at=fact.ingestion_at.isoformat() if fact.ingestion_at else None,
                value=fact.value,
                provenance_status="SYNTHETIC_INGESTION_NULL_IF_UNRECORDED",
            )
        )
        filings.setdefault((fact.security_id, fact.accession), []).append(fact)
    for (security_id, accession), facts in sorted(filings.items()):
        rows["event_evidence"].append(
            dict(
                security_id=security_id,
                event_at=max(f.accepted_at for f in facts).isoformat(),
                first_public_at=max(f.published_at for f in facts).isoformat(),
                evidence_type="SYNTHETIC_FILED_FACTS_NOT_CATALYST_CLASSIFICATION",
                source_url=facts[0].source_url,
                raw_digest=checksum,
                raw_digest_scope="COMPLETE_SYNTHETIC_DATASET_NOT_ORIGINAL_FILING",
                summary=_json(
                    {"accession": accession, "metrics": sorted({f.metric for f in facts})}
                ),
                classification_confidence=None,
                provenance_status="SYNTHETIC_NO_CAUSAL_OR_INDUSTRY_EVENT_INFERENCE",
            )
        )
    for execution in run["portfolio"]["executions"]:
        for side in ("entry", "exit"):
            rows["backtest_execution"].append(
                dict(
                    run_id=run["run_id"],
                    security_id=execution["security_id"],
                    session_date=execution[side],
                    order_intent=_json({"side": side, "shares": execution["shares"]}),
                    timestamp=None,
                    timestamp_status="SESSION_ONLY_INTRADAY_TIME_NOT_RECORDED",
                    assumed_fill=execution["entry_price"] if side == "entry" else None,
                    costs=execution[f"{side}_cost"],
                    rejected_reason=None,
                    terminal_wealth=execution["terminal_wealth"] if side == "exit" else None,
                    simulation_basis="FIXTURE_TERMINAL_WEALTH_INCLUDES_ACTIONS_NOT_EXIT_FILL",
                )
            )
    for rejection in run["portfolio"]["exclusions"]:
        rows["backtest_execution"].append(
            dict(
                run_id=run["run_id"],
                security_id=rejection["security_id"],
                session_date=rejection["decision"],
                timestamp=f"{rejection['decision']}T23:00:00+00:00",
                timestamp_status="DATED_SELECTION_CLOCK_NOT_ORDER_TRANSMISSION",
                order_intent=_json({"side": "excluded"}),
                assumed_fill=None,
                costs=None,
                terminal_wealth=None,
                rejected_reason=rejection["reason"],
                simulation_basis="FIXTURE_REJECTED_SELECTION_NOT_ORDER",
            )
        )
    for source in run["sources"]:
        rows["source_manifest"].append(
            dict(
                source_id=source["source_id"],
                provider=source["provider"],
                url=source["url"],
                license_note=source["license_note"],
                asof_coverage=source["coverage"],
                checksum=source["sha256"],
                status="SYNTHETIC_FIXTURE",
                retrieval_at=None,
                retrieval_status="GENERATED_NOT_RETRIEVED",
            )
        )
    # No synthetic thesis is invented to populate the table. Offline imports are assertions.
    return rows


def write_contracts(folder: Path, rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if set(rows) != set(SCHEMAS):
        raise ValueError("Every canonical table, including empty tables, is required")
    # Validate every table before creating output files.
    tables = {}
    for name, schema in SCHEMAS.items():
        for row in rows[name]:
            if set(row) != set(schema.names):
                raise ValueError(f"Canonical field mismatch: {name}")
            if any(row[field.name] is None for field in schema if not field.nullable):
                raise ValueError(f"Missing required canonical value: {name}")
            require_finite(row, "canonical table")
        tables[name] = pa.Table.from_pylist(rows[name], schema=schema)
    folder.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for name, data in tables.items():
        path = folder / f"{name}.parquet"
        pq.write_table(data, path)
        inventory[name] = {
            "rows": data.num_rows,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "fields": data.column_names,
            "null_counts": {name: data[name].null_count for name in data.column_names},
        }
    return {"contract": VERSION, "tables": inventory, "scope": "FIXTURE_NOT_EMPIRICAL"}
