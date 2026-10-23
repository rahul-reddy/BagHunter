"""Bounded local overview CSV import. No network, PIT promotion or identity inference."""

import csv
import hashlib
import io
import json
import re
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import AwareDatetime, ConfigDict, Field

from packages.shared.models import Record

VERSION = "finviz-snapshot-v1"
MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
COLUMNS = [
    "No.",
    "Ticker",
    "Company",
    "Sector",
    "Industry",
    "Country",
    "Market Cap",
    "P/E",
    "Price",
    "Change",
    "Volume",
]
MISSING = {"", "-", "N/A"}
Mode = Literal["FIXTURE", "EXTERNAL_UNVERIFIED"]


class ExportManifest(Record):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    provider: Literal["Finviz Elite"]
    source_url: Literal["https://elite.finviz.com/export.ashx", "https://elite.finviz.com/export"]
    parameters: dict[str, str]
    filters: list[str]
    requested_at: AwareDatetime
    retrieved_at: AwareDatetime
    provider_observation_time: None
    status: Literal["CURRENT_SNAPSHOT_UNVERIFIED_NOT_HISTORICAL_PIT"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rows: int = Field(strict=True, gt=0, le=MAX_ROWS)
    columns: list[str]
    bytes: int = Field(strict=True, gt=0, le=MAX_BYTES)
    historical_coverage: Literal["unverified"]
    adjustment_semantics: Literal["unverified"]


class Observation(Record):
    """Decimal fields retain provider scale. They are not dollar-normalized fundamentals."""

    ticker: str
    company: str
    sector: str | None
    industry: str | None
    country: str | None
    market_cap_reported: Decimal | None
    pe_reported: Decimal | None
    price_reported: Decimal | None
    change_fraction: Decimal | None
    volume_shares: int | None
    security_id: None = None
    security_type: Literal["unknown"] = "unknown"


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise ValueError("Input exceeds size limit")
    return body


def _number(value: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal | None:
    if value in MISSING:
        return None
    if not re.fullmatch(r"[+-]?\d{1,25}(?:\.\d{1,8})?", value):
        raise ValueError("Unsupported numeric representation")
    number = Decimal(value)
    if abs(number) > Decimal("1e24") or (positive and number <= 0):
        raise ValueError("Numeric value outside bounds")
    if nonnegative and number < 0:
        raise ValueError("Negative unsigned value")
    return number


def _text(value: str, *, required: bool = False) -> str | None:
    if required and value in MISSING:
        raise ValueError("Required text is missing")
    if value in MISSING and not required:
        return None
    if not value or len(value) > 512 or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid text")
    return value


def _parse(body: bytes) -> list[Observation]:
    reader = csv.reader(io.StringIO(body.decode("utf-8-sig"), newline=""), strict=True)
    if next(reader, None) != COLUMNS:
        raise ValueError("Only exact overview columns are supported")
    observations = []
    seen: set[str] = set()
    for index, row in enumerate(reader, 1):
        if index > MAX_ROWS or len(row) != len(COLUMNS):
            raise ValueError("Invalid CSV shape or row limit")
        values = dict(zip(COLUMNS, (cell.strip() for cell in row), strict=True))
        ticker = values["Ticker"]
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.^/\-]{0,31}", ticker) or ticker in seen:
            raise ValueError("Invalid or duplicate ticker")
        if values["No."] != str(index):
            raise ValueError("Unexpected row ordinal")
        seen.add(ticker)
        change = values["Change"]
        if change not in MISSING and not change.endswith("%"):
            raise ValueError("Change must have explicit percent unit")
        fraction = None if change in MISSING else _number(change[:-1])
        if fraction is not None:
            fraction /= 100
            if fraction < -1:
                raise ValueError("Invalid price change")
        volume = _number(values["Volume"], nonnegative=True)
        if volume is not None and (volume != int(volume) or volume > 2**63 - 1):
            raise ValueError("Volume must be a bounded integer")
        observations.append(
            Observation(
                ticker=ticker,
                company=_text(values["Company"], required=True) or "",
                sector=_text(values["Sector"]),
                industry=_text(values["Industry"]),
                country=_text(values["Country"]),
                market_cap_reported=_number(values["Market Cap"], nonnegative=True),
                pe_reported=_number(values["P/E"], nonnegative=True),
                price_reported=_number(values["Price"], positive=True),
                change_fraction=fraction,
                volume_shares=None if volume is None else int(volume),
            )
        )
    if not observations:
        raise ValueError("Empty export")
    return observations


def load_export(
    csv_path: Path, manifest_path: Path
) -> tuple[ExportManifest, list[Observation], bytes, bytes]:
    manifest_bytes = _read(manifest_path, 64 * 1024)
    manifest = ExportManifest.model_validate_json(manifest_bytes)
    now = datetime.now(UTC)
    if not manifest.requested_at <= manifest.retrieved_at <= now:
        raise ValueError("Source clock outside retrieval interval")
    if manifest.parameters != {"v": "111"} or manifest.filters or manifest.columns != COLUMNS:
        raise ValueError("Only unfiltered overview exports are supported")
    body = _read(csv_path, MAX_BYTES)
    if len(body) != manifest.bytes or hashlib.sha256(body).hexdigest() != manifest.sha256:
        raise ValueError("Source checksum or byte count mismatch")
    observations = _parse(body)
    if len(observations) != manifest.rows:
        raise ValueError("Source row count mismatch")
    return manifest, observations, body, manifest_bytes


def _json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _table(rows: list[Observation]) -> Any:
    decimal = pa.decimal128(38, 10)
    schema = pa.schema(
        [
            ("ticker", pa.string()),
            ("company", pa.string()),
            ("sector", pa.string()),
            ("industry", pa.string()),
            ("country", pa.string()),
            ("market_cap_reported", decimal),
            ("pe_reported", decimal),
            ("price_reported", decimal),
            ("change_fraction", decimal),
            ("volume_shares", pa.int64()),
            ("security_id", pa.string()),
            ("security_type", pa.string()),
        ]
    )
    return pa.Table.from_pylist([row.model_dump() for row in rows], schema=schema)


def _parquet(rows: list[Observation], path: Path) -> None:
    pq.write_table(_table(rows), path)


def ingest_snapshot(
    csv_path: Path, manifest_path: Path, *, mode: Mode, usage_authorized: bool
) -> dict[str, Any]:
    if usage_authorized is not True or mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise ValueError("Explicit authorization and source mode required")
    manifest, rows, body, manifest_bytes = load_export(csv_path, manifest_path)
    # A fixed ignored subtree avoids writing licensed rows into arbitrary tracked directories.
    root = Path.cwd().resolve() / "data" / "finviz" / "snapshots" / mode.lower()
    if root.resolve() != root:
        raise ValueError("Output directory must not traverse symlinks")
    root.mkdir(parents=True, exist_ok=True)
    snapshot_id = hashlib.sha256(
        VERSION.encode() + mode.encode() + body + manifest_bytes
    ).hexdigest()
    destination = root / snapshot_id
    if destination.is_symlink():
        raise ValueError("Snapshot must not be a symlink")
    data = _json([row.model_dump(mode="json") for row in rows])
    missing = {
        name: sum(getattr(row, name) is None for row in rows)
        for name in Observation.model_fields
        if name not in {"ticker", "company", "security_type"}
    }
    report: dict[str, Any] = {
        "version": VERSION,
        "snapshot_id": snapshot_id,
        "mode": mode,
        "provider": "Finviz Elite",
        "status": "QUARANTINED_CURRENT_SNAPSHOT",
        "source_sha256": manifest.sha256,
        "rows": len(rows),
        "missing": missing,
        "zero_pe_reported": sum(row.pe_reported == 0 for row in rows),
        "retrieved_at": manifest.retrieved_at.isoformat(),
        "provider_observation_time": None,
        "unit_policy": {
            "market_cap_reported": "provider scale unverified; no USD conversion",
            "price_reported": "provider price; currency/adjustment unverified",
            "pe_reported": "reported ratio",
            "volume_shares": "current/last session shares",
            "change_fraction": "explicit CSV percent divided by 100",
        },
        "flags": [
            "NO_PIT_HISTORY",
            "UNRESOLVED_PERMANENT_IDENTITIES",
            "SECURITY_TYPES_UNKNOWN",
            "MARKET_CAP_SCALE_UNVERIFIED",
            "PROVIDER_OBSERVATION_TIME_UNKNOWN",
            "ENTITLEMENT_NOT_INDEPENDENTLY_VERIFIED",
        ]
        + (["FIXTURE_ONLY"] if mode == "FIXTURE" else []),
    }
    files = {"raw.csv": body, "source-manifest.json": manifest_bytes, "observations.json": data}
    if destination.exists():
        expected_names = {*files, "observations.parquet", "coverage.json"}
        if {p.name for p in destination.iterdir()} != expected_names:
            raise ValueError("Archive file set mismatch")
        if any(p.is_symlink() or not p.is_file() for p in destination.iterdir()):
            raise ValueError("Invalid archive member")
        for name, value in files.items():
            if _read(destination / name, len(value)) != value:
                raise ValueError("Archive content mismatch")
        if (destination / "observations.parquet").stat().st_size > 256 * 1024 * 1024:
            raise ValueError("Archive Parquet exceeds size limit")
        table = pq.read_table(destination / "observations.parquet")
        if not table.equals(_table(rows), check_metadata=False):
            raise ValueError("Archive Parquet mismatch")
        previous: dict[str, Any] = json.loads(_read(destination / "coverage.json", 64 * 1024))
        ingested_at = datetime.fromisoformat(previous.pop("ingested_at"))
        if previous != report or not manifest.retrieved_at <= ingested_at <= datetime.now(UTC):
            raise ValueError("Archive report mismatch")
        return previous | {"ingested_at": ingested_at.isoformat()}
    report["ingested_at"] = datetime.now(UTC).isoformat()
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=root) as temporary:
        stage = Path(temporary) / "snapshot"
        stage.mkdir()
        for name, value in files.items():
            (stage / name).write_bytes(value)
        _parquet(rows, stage / "observations.parquet")
        (stage / "coverage.json").write_bytes(_json(report))
        # The archive is published in one rename; no partial run or CURRENT pointer is exposed.
        for attempt in range(6):
            try:
                stage.rename(destination)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    return report
