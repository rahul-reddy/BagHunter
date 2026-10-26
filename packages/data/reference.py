"""Current OpenFIGI candidates, isolated from historical identities and licensed source rows."""

import hashlib
import json
import re
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import AwareDatetime, ConfigDict, Field

from packages.data.finviz import Mode, Observation, _json, _read, read_snapshot
from packages.shared.models import Record

VERSION = "openfigi-reference-v1"
URL = "https://api.openfigi.com/v3/mapping"
MAX_RESPONSE = 4 * 1024 * 1024


class Candidate(Record):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    figi: str = Field(pattern=r"^[A-Z0-9]{12}$")
    ticker: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=512)
    exchCode: str = Field(min_length=1, max_length=32)
    marketSector: str = Field(min_length=1, max_length=100)
    securityType: str = Field(min_length=1, max_length=100)
    securityType2: str | None = Field(default=None, max_length=100)
    compositeFIGI: str | None = Field(default=None, pattern=r"^[A-Z0-9]{12}$")
    shareClassFIGI: str | None = Field(default=None, pattern=r"^[A-Z0-9]{12}$")
    securityDescription: str | None = Field(default=None, max_length=512)


class Receipt(Record):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    version: str
    provider: str
    source_url: str
    mode: Mode
    base_snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    offset: int = Field(strict=True, ge=0, le=100_000)
    limit: int = Field(strict=True, ge=1, le=10)
    requested_at: AwareDatetime
    retrieved_at: AwareDatetime
    request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def _validate_jobs(jobs: list[dict[str, Any]]) -> None:
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 10:
        raise ValueError("Reference batch must contain one to ten jobs")
    for job in jobs:
        if not isinstance(job, dict) or set(job) != {
            "idType",
            "idValue",
            "exchCode",
            "marketSecDes",
            "includeUnlistedEquities",
        }:
            raise ValueError("Unsupported reference request fields")
        if (
            job["idType"] != "TICKER"
            or job["exchCode"] != "US"
            or job["marketSecDes"] != "Equity"
            or job["includeUnlistedEquities"] is not False
            or not isinstance(job["idValue"], str)
            or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^/\-]{0,31}", job["idValue"])
        ):
            raise ValueError("Unsupported reference request context")
    if len({job["idValue"] for job in jobs}) != len(jobs):
        raise ValueError("Duplicate reference jobs")


def _jobs(rows: list[Observation], offset: int, limit: int) -> list[dict[str, Any]]:
    if type(offset) is not int or type(limit) is not int or not 0 <= offset < len(rows):
        raise ValueError("Invalid reference offset")
    if not 1 <= limit <= 10:
        raise ValueError("At most ten reference jobs per batch")
    selected = sorted(rows, key=lambda row: row.ticker)[offset : offset + limit]
    return [
        {
            "idType": "TICKER",
            "idValue": row.ticker,
            "exchCode": "US",
            "marketSecDes": "Equity",
            "includeUnlistedEquities": False,
        }
        for row in selected
    ]


def _records(jobs: list[dict[str, Any]], raw: bytes) -> list[dict[str, Any]]:
    _validate_jobs(jobs)
    value = json.loads(raw)
    if not isinstance(value, list) or len(value) != len(jobs):
        raise ValueError("Reference response must preserve job cardinality")
    records = []
    for job, result in zip(jobs, value, strict=True):
        if not isinstance(result, dict) or len(result) != 1:
            raise ValueError("Reference job has ambiguous result keys")
        candidates = []
        if "data" in result:
            if not isinstance(result["data"], list) or len(result["data"]) > 100:
                raise ValueError("Reference candidates exceed batch audit limits")
            candidates = [Candidate.model_validate(row).model_dump() for row in result["data"]]
            if len({row["figi"] for row in candidates}) != len(candidates):
                raise ValueError("Duplicate reference candidates")
            for candidate in candidates:
                if any(isinstance(v, str) and not v.isprintable() for v in candidate.values()):
                    raise ValueError("Nonprintable reference metadata")
            context_ok = all(
                row["ticker"] == job["idValue"]
                and row["exchCode"] == "US"
                and row["marketSector"] == "Equity"
                for row in candidates
            )
            status = (
                "NO_CANDIDATES"
                if not candidates
                else "CONTEXT_MISMATCH"
                if not context_ok
                else ("SINGLE_CANDIDATE" if len(candidates) == 1 else "AMBIGUOUS")
            )
        elif set(result) <= {"error", "warning"}:
            message = next(iter(result.values()))
            if not isinstance(message, str) or len(message) > 2048:
                raise ValueError("Invalid reference error metadata")
            status = "NO_MATCH_REPORTED" if message == "No identifier found." else "PROVIDER_ISSUE"
        else:
            raise ValueError("Unknown reference result")
        records.append(
            {
                "ticker": job["idValue"],
                "status": status,
                "candidates": candidates,
                "identity_promoted": False,
                "name_match_verified": False,
            }
        )
    return records


class OpenFigiClient:
    """Unauthenticated, per-client 3.1-second request spacing; no keys or .env reads."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.transport = transport
        self.last_request: float | None = None

    def mapping(self, jobs: list[dict[str, Any]]) -> tuple[bytes, datetime, datetime]:
        _validate_jobs(jobs)
        started = datetime.now(UTC)
        with httpx.Client(
            timeout=30, follow_redirects=False, trust_env=False, transport=self.transport
        ) as client:
            for attempt in range(3):
                if self.last_request is not None:
                    time.sleep(max(0, 3.1 - (time.monotonic() - self.last_request)))
                self.last_request = time.monotonic()
                with client.stream(
                    "POST", URL, content=_json(jobs), headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code == 429 and attempt < 2:
                        delay = int(response.headers.get("retry-after", "60"))
                        if not 0 <= delay <= 60:
                            raise ValueError("Reference retry delay exceeds local wait budget")
                        time.sleep(delay)
                        continue
                    if response.status_code in (500, 502, 503, 504) and attempt < 2:
                        time.sleep(3.1 * (attempt + 1))
                        continue
                    if response.status_code != 200:
                        raise ValueError("Reference provider did not return HTTP 200")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE:
                            raise ValueError("Reference response exceeds size cap")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    _records(jobs, body)
                    return body, started, datetime.now(UTC)
        raise ValueError("Reference retry budget exhausted")


def _derive(receipt: Receipt, request: bytes, response: bytes) -> tuple[str, dict[str, Any]]:
    if receipt.version != VERSION or receipt.provider != "OpenFIGI" or receipt.source_url != URL:
        raise ValueError("Unsupported reference provenance")
    base, rows = read_snapshot(receipt.base_snapshot_id, receipt.mode)
    if (
        not datetime.fromisoformat(base["retrieved_at"])
        <= receipt.requested_at
        <= receipt.retrieved_at
        <= datetime.now(UTC)
    ):
        raise ValueError("Reference source clock invalid")
    jobs = _jobs(rows, receipt.offset, receipt.limit)
    if request != _json(jobs) or hashlib.sha256(request).hexdigest() != receipt.request_sha256:
        raise ValueError("Reference requests do not match selected source sample")
    if hashlib.sha256(response).hexdigest() != receipt.response_sha256:
        raise ValueError("Reference response checksum mismatch")
    records = _records(jobs, response)
    reference_id = hashlib.sha256(
        _json(receipt.model_dump(mode="json")) + request + response
    ).hexdigest()
    return reference_id, {
        "reference_id": reference_id,
        "base_snapshot_id": receipt.base_snapshot_id,
        "provider": "OpenFIGI",
        "mode": receipt.mode,
        "source_url": URL,
        "retrieved_at": receipt.retrieved_at.isoformat(),
        "response_sha256": receipt.response_sha256,
        "queried": len(jobs),
        "population": len(rows),
        "offset": receipt.offset,
        "selection": "ALPHABETICAL_SAMPLE",
        "records": records,
        "counts": dict(Counter(row["status"] for row in records)),
        "flags": [
            "CURRENT_REFERENCE_ONLY_NOT_PIT",
            "NOT_IDENTITY_PROMOTION",
            "NAME_MATCH_NOT_VERIFIED",
            "US_EQUITY_CONTEXT_ASSUMED",
            "NO_CURRENCY_OR_CAP_SCALE_EVIDENCE",
        ]
        + (["FIXTURE_ONLY"] if receipt.mode == "FIXTURE" else []),
    }


def _root(mode: Mode) -> Path:
    if mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise ValueError("Invalid reference mode")
    root = Path.cwd().resolve() / "data" / "reference" / "openfigi" / mode.lower()
    if root.resolve() != root:
        raise ValueError("Reference root must not traverse symlinks")
    return root


def archive_reference(receipt: Receipt, request: bytes, response: bytes) -> dict[str, Any]:
    if len(request) > 64 * 1024 or len(response) > MAX_RESPONSE:
        raise ValueError("Reference input size cap exceeded")
    reference_id, evidence = _derive(receipt, request, response)
    root = _root(receipt.mode)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / reference_id
    if destination.exists() or destination.is_symlink():
        return read_reference(reference_id, receipt.base_snapshot_id, receipt.mode)
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=root) as directory:
        stage = Path(directory) / "batch"
        stage.mkdir()
        for name, body in {
            "manifest.json": _json(receipt.model_dump(mode="json")),
            "request.json": request,
            "response.json": response,
            "evidence.json": _json(evidence),
        }.items():
            (stage / name).write_bytes(body)
        for attempt in range(6):
            try:
                stage.rename(destination)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    return evidence


def fetch_reference(base_snapshot_id: str, offset: int = 0, limit: int = 10) -> dict[str, Any]:
    _, rows = read_snapshot(base_snapshot_id, "EXTERNAL_UNVERIFIED")
    jobs = _jobs(rows, offset, limit)
    request = _json(jobs)
    response, started, retrieved = OpenFigiClient().mapping(jobs)
    receipt = Receipt(
        version=VERSION,
        provider="OpenFIGI",
        source_url=URL,
        mode="EXTERNAL_UNVERIFIED",
        base_snapshot_id=base_snapshot_id,
        offset=offset,
        limit=limit,
        requested_at=started,
        retrieved_at=retrieved,
        request_sha256=hashlib.sha256(request).hexdigest(),
        response_sha256=hashlib.sha256(response).hexdigest(),
    )
    return archive_reference(receipt, request, response)


def read_reference(reference_id: str, base_snapshot_id: str, mode: Mode) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", reference_id):
        raise ValueError("Invalid reference selection")
    destination = _root(mode) / reference_id
    if destination.resolve() != destination:
        raise ValueError("Reference archive must not traverse symlinks")
    names = {"manifest.json", "request.json", "response.json", "evidence.json"}
    if {p.name for p in destination.iterdir()} != names or any(
        p.is_symlink() or not p.is_file() for p in destination.iterdir()
    ):
        raise ValueError("Invalid reference archive members")
    receipt = Receipt.model_validate_json(_read(destination / "manifest.json", 64 * 1024))
    if receipt.base_snapshot_id != base_snapshot_id or receipt.mode != mode:
        raise ValueError("Reference does not belong to selected observations")
    actual_id, evidence = _derive(
        receipt,
        _read(destination / "request.json", 64 * 1024),
        _read(destination / "response.json", MAX_RESPONSE),
    )
    if actual_id != reference_id or _read(destination / "evidence.json", 8 * 1024 * 1024) != _json(
        evidence
    ):
        raise ValueError("Reference archive integrity mismatch")
    return evidence
