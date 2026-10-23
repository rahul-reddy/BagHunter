"""Validate and quarantine normalized historical exports. Never implies provider entitlement."""

import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ConfigDict, Field, field_validator, model_validator

from packages.research.features import facts_at, utc_asof
from packages.shared.models import Action, Bar, Fact, Record

TABLES = ("instruments", "symbols", "universe", "bars", "actions", "facts", "sessions")
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_EXPECTED_CELLS = 5_000_000
VERSION = "historical-import-v2"


class ImportRecord(Record):
    model_config = ConfigDict(hide_input_in_errors=True)


class Manifest(ImportRecord):
    schema_version: Literal[1]
    mode: Literal["FIXTURE", "EXTERNAL_UNVERIFIED"]
    source_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    source_url: str
    retrieved_at: datetime
    license_note: str = Field(min_length=1)
    usage_authorized: Literal[True]
    universe_basis: Literal["archived_pit", "current_only", "unknown"]
    delisted_coverage: Literal["included", "excluded", "unknown"]
    actions_coverage: Literal["complete", "unknown"]
    files: dict[str, str]

    @field_validator("usage_authorized", mode="before")
    @classmethod
    def explicit_authorization(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("explicit usage authorization required")
        return True

    @model_validator(mode="after")
    def contract(self) -> "Manifest":
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at requires a timezone")
        url = urlsplit(self.source_url)
        allowed = ("https", "fixture") if self.mode == "FIXTURE" else ("https",)
        if (
            url.scheme not in allowed
            or not url.netloc
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "source_url must be a public source reference without credentials/query"
            )
        if set(self.files) != set(TABLES):
            raise ValueError("manifest must hash every required table, including empty tables")
        if any(
            len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in self.files.values()
        ):
            raise ValueError("invalid SHA-256 digest")
        return self


class HistoricalInstrument(ImportRecord):
    security_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    first_seen: date
    last_seen: date | None = None
    security_type: Literal["common", "benchmark"]
    exchange: str = Field(min_length=1)
    delisted: bool

    @model_validator(mode="after")
    def interval(self) -> "HistoricalInstrument":
        if self.last_seen is not None and self.last_seen < self.first_seen:
            raise ValueError("invalid listing interval")
        if self.delisted and self.last_seen is None:
            raise ValueError("delisted instrument needs last_seen")
        return self


class HistoricalSymbol(ImportRecord):
    security_id: str
    ticker: str = Field(min_length=1)
    valid_from: date
    valid_to: date | None = None
    published_at: datetime

    @field_validator("published_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc_asof(value)

    @model_validator(mode="after")
    def interval(self) -> "HistoricalSymbol":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("invalid symbol interval")
        return self


class Membership(ImportRecord):
    security_id: str
    asof_time: datetime
    published_at: datetime
    valid_until: datetime
    eligible: bool
    rejection_reason: str | None
    marketcap_asof: float | None = Field(ge=0)
    dollar_volume: float | None = Field(ge=0)
    sector_asof: str | None
    source_id: str

    @field_validator("asof_time", "published_at", "valid_until")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc_asof(value)

    @model_validator(mode="after")
    def reason(self) -> "Membership":
        if self.valid_until <= self.asof_time:
            raise ValueError("membership validity must end after its as-of time")
        if not self.eligible and not self.rejection_reason:
            raise ValueError("excluded membership needs a reason")
        return self


def read_bytes(path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("import file exceeds size limit")
    return content


class LocalHistoryProvider:
    """One normalized export, no HTTP calls. A passed contract is not an empirical PIT audit."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()
        manifest_path = (self.directory / "manifest.json").resolve()
        if manifest_path.parent != self.directory:
            raise ValueError("manifest must stay within bundle directory")
        self.raw = {"manifest": read_bytes(manifest_path, 65536)}
        self.manifest = Manifest.model_validate_json(self.raw["manifest"])
        parsed: dict[str, Any] = {}
        for name in TABLES:
            path = (self.directory / f"{name}.json").resolve()
            if path.parent != self.directory:
                raise ValueError("import table must stay within bundle directory")
            body = read_bytes(path)
            if hashlib.sha256(body).hexdigest() != self.manifest.files[name]:
                raise ValueError(f"checksum mismatch: {name}")
            value = json.loads(body)
            if not isinstance(value, list):
                raise ValueError(f"table must be a JSON array: {name}")
            parsed[name] = value
            self.raw[name] = body
        self.instruments = [HistoricalInstrument.model_validate(r) for r in parsed["instruments"]]
        self.symbols = [HistoricalSymbol.model_validate(r) for r in parsed["symbols"]]
        self.membership = [Membership.model_validate(r) for r in parsed["universe"]]
        # Shared immutable fact/action/bar schemas are reused; no fixture Instrument defaults.
        self.bars = [Bar.model_validate(r) for r in parsed["bars"]]
        self.actions = [Action.model_validate(r) for r in parsed["actions"]]
        self.facts = [Fact.model_validate(r) for r in parsed["facts"]]
        self.sessions = [date.fromisoformat(s) for s in parsed["sessions"]]
        self._validate_relations()

    def _validate_relations(self) -> None:
        ids = {i.security_id for i in self.instruments}
        if not ids or len(ids) != len(self.instruments):
            raise ValueError("instrument IDs must be nonempty and unique")
        if len(self.instruments) * len(self.sessions) > MAX_EXPECTED_CELLS:
            raise ValueError("bundle exceeds audit budget; partition instruments or calendar")
        for rows in (self.symbols, self.membership, self.bars, self.actions, self.facts):
            if any(r.security_id not in ids for r in rows):
                raise ValueError("table refers to an unknown permanent security ID")
        for rows in (self.membership, self.bars, self.actions, self.facts):
            if any(r.source_id != self.manifest.source_id for r in rows):
                raise ValueError("row source_id does not match manifest")
        keys = [(b.security_id, b.session) for b in self.bars]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate bars; revisions cannot overwrite observations silently")
        if any(b.available_at.astimezone(UTC).date() < b.session for b in self.bars):
            raise ValueError("bar availability precedes its session")
        publications = (
            [b.available_at for b in self.bars]
            + [f.published_at for f in self.facts]
            + [s.published_at for s in self.symbols]
            + [m.published_at for m in self.membership]
            + [m.asof_time for m in self.membership]
        )
        if any(p > self.manifest.retrieved_at for p in publications):
            raise ValueError("source contains observations after its declared retrieval time")
        if any(
            a.effective_date > self.manifest.retrieved_at.astimezone(UTC).date()
            for a in self.actions
        ):
            raise ValueError("realized action occurs after retrieval time")
        master = {i.security_id: i for i in self.instruments}
        for bar in self.bars:
            instrument = master[bar.security_id]
            if bar.session < instrument.first_seen or (
                instrument.last_seen is not None and bar.session > instrument.last_seen
            ):
                raise ValueError("bar is outside listing interval")
        exits = {a.security_id: a.effective_date for a in self.actions if a.kind == "delist"}
        if any(b.security_id in exits and b.session > exits[b.security_id] for b in self.bars):
            raise ValueError("bar occurs after delisting")
        keys2 = [(m.security_id, m.asof_time, m.published_at) for m in self.membership]
        if len(set(keys2)) != len(keys2):
            raise ValueError("duplicate membership revisions")
        if self.sessions != sorted(set(self.sessions)):
            raise ValueError("expected sessions must be sorted and unique")
        session_set = set(self.sessions)
        if self.sessions and any(b.session not in session_set for b in self.bars):
            raise ValueError("bar session is outside declared calendar")

    def list_instruments(self, asof: str) -> list[dict[str, Any]]:
        clock = self._clock(asof)
        latest: dict[str, Membership] = {}
        for row in sorted(self.membership, key=lambda m: (m.asof_time, m.published_at)):
            if row.asof_time <= clock and row.published_at <= clock:
                latest[row.security_id] = row
        result = []
        for instrument in self.instruments:
            member = latest.get(instrument.security_id)
            if member is None or not member.eligible or member.valid_until <= clock:
                continue
            if instrument.first_seen > clock.date() or (
                instrument.last_seen is not None and instrument.last_seen < clock.date()
            ):
                continue
            symbols = [
                s
                for s in self.symbols
                if s.security_id == instrument.security_id
                and s.valid_from <= clock.date()
                and s.published_at <= clock
                and (s.valid_to is None or clock.date() < s.valid_to)
            ]
            if len(symbols) != 1:
                raise ValueError("missing or ambiguous as-of symbol mapping")
            result.append(
                {
                    "name": instrument.name,
                    "exchange": instrument.exchange,
                    "security_type": instrument.security_type,
                    **member.model_dump(mode="json"),
                    "ticker": symbols[0].ticker,
                    "provider": self.manifest.provider,
                    "mode": self.manifest.mode,
                }
            )
        return result

    def get_bars(
        self, security_ids: list[str], start: str, end: str, adjustment: str
    ) -> list[dict[str, Any]]:
        self._known_ids(security_ids)
        if adjustment != "raw":
            raise ValueError("only raw prices supported; corporate-action adjustment is explicit")
        begin, finish = date.fromisoformat(start), date.fromisoformat(end)
        if finish < begin:
            raise ValueError("invalid bar range")
        return [
            b.model_dump(mode="json")
            for b in self.bars
            if b.security_id in security_ids and begin <= b.session <= finish
        ]

    def get_actions(self, security_ids: list[str]) -> list[dict[str, Any]]:
        self._known_ids(security_ids)
        return [a.model_dump(mode="json") for a in self.actions if a.security_id in security_ids]

    def get_fundamentals(self, security_ids: list[str], asof: str) -> list[dict[str, Any]]:
        self._known_ids(security_ids)
        clock = self._clock(asof)
        return [
            f.model_dump(mode="json")
            for sid in security_ids
            for f in facts_at(self.facts, sid, clock)
        ]

    def get_filings(self, cik: str, start: str, end: str) -> list[dict[str, Any]]:
        raise NotImplementedError("filing documents are not included in a market-history bundle")

    def _known_ids(self, security_ids: list[str]) -> None:
        if not set(security_ids).issubset({i.security_id for i in self.instruments}):
            raise ValueError("requested permanent ID is not present in the bundle")

    def _clock(self, asof: str) -> datetime:
        clock = utc_asof(datetime.fromisoformat(asof))
        if clock > self.manifest.retrieved_at:
            raise ValueError("requested asof exceeds source vintage")
        return clock

    def get_coverage_report(self) -> dict[str, Any]:
        flags = [
            "FIXTURE_ONLY"
            if self.manifest.mode == "FIXTURE"
            else "EXTERNAL_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED"
        ]
        if self.manifest.universe_basis != "archived_pit":
            flags.append("UNIVERSE_NOT_ARCHIVED_PIT")
        if self.manifest.delisted_coverage != "included":
            flags.append("DELISTED_COVERAGE_INCOMPLETE")
        if self.manifest.actions_coverage != "complete":
            flags.append("CORPORATE_ACTION_COVERAGE_UNKNOWN")
        if not self.facts:
            flags.append("FUNDAMENTALS_MISSING")
        if not self.membership:
            flags.append("UNIVERSE_MEMBERSHIP_MISSING")
        if not self.sessions:
            flags.append("EXPECTED_CALENDAR_MISSING")
        observed = {(b.security_id, b.session) for b in self.bars}
        missing = sum(
            (i.security_id, day) not in observed
            for i in self.instruments
            for day in self.sessions
            if i.first_seen <= day and (i.last_seen is None or day <= i.last_seen)
        )
        if missing:
            flags.append("PRICE_SESSIONS_MISSING")
        end = (
            max(self.sessions)
            if self.sessions
            else max((b.session for b in self.bars), default=date.min)
        )
        exits = {
            a.security_id for a in self.actions if a.kind == "delist" and a.effective_date <= end
        }
        unresolved = [
            i.security_id
            for i in self.instruments
            if i.delisted
            and i.last_seen is not None
            and i.last_seen <= end
            and i.security_id not in exits
        ]
        if unresolved:
            flags.append("DELIST_PROCEEDS_UNRESOLVED")
        return {
            "status": "QUARANTINED_NOT_RESEARCH_READY",
            "mode": self.manifest.mode,
            "provider": self.manifest.provider,
            "source_id": self.manifest.source_id,
            "license": "USER_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
            "adapter_version": VERSION,
            "coverage_flags": flags,
            "counts": {
                "instruments": len(self.instruments),
                "bars": len(self.bars),
                "universe_rows": len(self.membership),
                "facts": len(self.facts),
                "actions": len(self.actions),
                "missing_price_sessions": missing,
            },
            "unresolved_delist_ids": unresolved,
            "limitations": [
                "No live candidate or backtest activation",
                "Calendar and coverage declarations require independent audit",
                "Empty tables are reported gaps, never evidence of zero exposure",
                "Action history is realized history, not a PIT catalyst feed",
            ],
        }


def ingest(directory: Path, output: Path) -> dict[str, Any]:
    provider = LocalHistoryProvider(directory)
    output = output.resolve()
    if "imported" not in output.parts:
        raise ValueError("quarantined imports must stay under a directory named imported")
    namespace = "fixture" if provider.manifest.mode == "FIXTURE" else "external-unverified"
    root = output / namespace
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(VERSION.encode())
    for name, body in sorted(provider.raw.items()):
        digest.update(name.encode())
        digest.update(body)
    snapshot_id = digest.hexdigest()
    target = root / snapshot_id
    ingested_at = datetime.now(UTC)
    if target.exists():
        archive_report = target / "coverage.json"
        if target.is_symlink() or not archive_report.resolve().is_relative_to(target.resolve()):
            raise ValueError("import archive cannot escape its snapshot directory")
        stored = json.loads(read_bytes(archive_report))
        ingested_at = utc_asof(datetime.fromisoformat(stored["ingested_at"]))
    if ingested_at > datetime.now(UTC) or provider.manifest.retrieved_at > ingested_at:
        raise ValueError("invalid source retrieval or ingestion timeline")
    report = {
        **provider.get_coverage_report(),
        "snapshot_id": snapshot_id,
        "manifest_sha256": hashlib.sha256(provider.raw["manifest"]).hexdigest(),
        "ingested_at": ingested_at.isoformat(),
    }
    staging = Path(tempfile.mkdtemp(prefix="staging-", dir=root))
    try:
        raw = staging / "raw"
        raw.mkdir()
        for name, body in provider.raw.items():
            (raw / f"{name}.json").write_bytes(body)
        silver = staging / "silver"
        silver.mkdir()
        for name, rows in (
            ("instruments", provider.instruments),
            ("symbols", provider.symbols),
            ("universe", provider.membership),
            ("bars", provider.bars),
            ("actions", provider.actions),
            ("facts", provider.facts),
        ):
            if rows:
                pq.write_table(
                    pa.Table.from_pylist([r.model_dump(mode="json") for r in rows]),
                    silver / f"{name}.parquet",
                )
        (staging / "coverage.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
        if target.exists():
            # A repeated import cannot reactivate a tampered archive silently.
            if target.is_symlink():
                raise ValueError("import archive cannot be a symbolic link")
            for expected in staging.rglob("*"):
                if expected.is_file():
                    archived = target / expected.relative_to(staging)
                    if (
                        not archived.resolve().is_relative_to(target.resolve())
                        or not archived.is_file()
                        or read_bytes(archived) != expected.read_bytes()
                    ):
                        raise ValueError(
                            "existing derived import archive is corrupted or incompatible"
                        )
        else:
            for attempt in range(6):
                try:
                    os.rename(staging, target)
                    break
                except PermissionError:
                    if attempt == 5:
                        raise
                    time.sleep(0.1 * 2**attempt)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report
