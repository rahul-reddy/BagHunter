"""Offline audit of attributed issuer evidence; assertions never approve identity."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from packages.data.finviz import Mode, _json, _read
from packages.data.reconciliation import compare_names, inspect_reference

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Text = Annotated[str, Field(min_length=1, max_length=512)]
POLICY = "issuer-evidence-audit-v1"
MAX_DOCUMENT = 20 * 1024 * 1024


class StrictRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)


class Document(StrictRecord):
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    sha256: Digest
    bytes: int = Field(strict=True, gt=0, le=MAX_DOCUMENT)
    source_url: str = Field(max_length=2048)
    discovered_from: str = Field(max_length=2048)
    retrieved_at: AwareDatetime
    published_at: AwareDatetime | None
    locator: Text
    # Explicit operator transcription, not machine-extracted or trusted facts.
    issuer_name: Text
    ticker: Text
    exchange: Text
    class_title: Text


class Dossier(StrictRecord):
    version: Literal["issuer-evidence-dossier-v1"]
    mode: Mode
    base_snapshot_id: Digest
    reference_id: Digest
    ticker: Text
    candidate_figi: str = Field(pattern=r"^[A-Z0-9]{12}$")
    documents: list[Document] = Field(min_length=1, max_length=3)
    unresolved: list[Text] = Field(min_length=1, max_length=20)


def _url(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or any(char.isspace() or ord(char) < 32 for char in value)
    ):
        raise ValueError("Public HTTPS provenance without credentials or query required")


def _no_symlinks(path: Path) -> None:
    if any(part.is_symlink() or part.is_junction() for part in (path, *path.parents)):
        raise ValueError("Linked dossier paths rejected")


def audit_issuer(
    bundle: Path, base_snapshot_id: str, reference_id: str, mode: Mode
) -> dict[str, Any]:
    """Verify local bytes and source binding, without network, writes or identity decisions.

    HTTPS attribution and matching transcriptions do not authenticate a document's origin
    or prove that the attributed statements describe the selected provider identifiers.
    """
    bundle = bundle.absolute()
    _no_symlinks(bundle)
    manifest = bundle / "dossier.json"
    _no_symlinks(manifest)
    raw = _read(manifest, 64 * 1024)
    dossier = Dossier.model_validate_json(raw)
    if (dossier.base_snapshot_id, dossier.reference_id, dossier.mode) != (
        base_snapshot_id,
        reference_id,
        mode,
    ):
        raise ValueError("Dossier/source selection mismatch")
    evidence = inspect_reference(reference_id, base_snapshot_id, mode)
    record = next((r for r in evidence["records"] if r["ticker"] == dossier.ticker), None)
    if record is None:
        raise ValueError("Dossier ticker outside queried batch")
    candidate = next((c for c in record["candidates"] if c["figi"] == dossier.candidate_figi), None)
    if candidate is None:
        raise ValueError("Dossier candidate absent from selected record")
    comparison = next(
        r for r in evidence["reconciliation"]["records"] if r["ticker"] == dossier.ticker
    )
    seen: set[str] = set()
    documents = []
    now = datetime.now(UTC)
    for doc in dossier.documents:
        for value in (doc.source_url, doc.discovered_from):
            _url(value)
        for value in (doc.locator, doc.issuer_name, doc.ticker, doc.exchange, doc.class_title):
            if not value.strip() or re.search(r"[\x00-\x1f\x7f]", value):
                raise ValueError("Invalid transcription text")
        if doc.filename == "dossier.json" or doc.filename.casefold() in seen:
            raise ValueError("Duplicate or reserved document path")
        seen.add(doc.filename.casefold())
        if doc.retrieved_at > now or (
            doc.published_at is not None and doc.published_at > doc.retrieved_at
        ):
            raise ValueError("Invalid document chronology")
        path = bundle / doc.filename
        _no_symlinks(path)
        body = _read(path, MAX_DOCUMENT)
        if len(body) != doc.bytes or hashlib.sha256(body).hexdigest() != doc.sha256:
            raise ValueError("Document integrity mismatch")
        documents.append(
            doc.model_dump(mode="json")
            | {
                "source_name_comparison": compare_names(
                    comparison["source_company"], doc.issuer_name
                ),
                "candidate_name_comparison": compare_names(candidate["name"], doc.issuer_name),
                "ticker_text_agrees": doc.ticker == dossier.ticker,
                "assertion_status": "OPERATOR_TRANSCRIPTION_REQUIRES_REVIEW",
            }
        )
    report = {
        "policy_version": POLICY,
        "mode": mode,
        "base_snapshot_id": base_snapshot_id,
        "reference_id": reference_id,
        "reconciliation_sha256": evidence["reconciliation"]["report_sha256"],
        "dossier_sha256": hashlib.sha256(raw).hexdigest(),
        "ticker": dossier.ticker,
        "candidate_figi": dossier.candidate_figi,
        "reference_status": record["status"],
        "documents": documents,
        "unresolved": dossier.unresolved,
        "disposition": "REVIEW_REQUIRED",
        "identity_verified": False,
        "share_class_verified": False,
        "identity_promotions": 0,
        "flags": [
            "LOCAL_BYTES_CHECKED_ORIGIN_NOT_AUTHENTICATED",
            "TRANSCRIPTIONS_NOT_MACHINE_VERIFIED",
            "NO_INDEPENDENT_FIGI_ASSIGNMENT_PROOF",
            "NO_CURRENT_OR_HISTORICAL_IDENTITY_DECISION",
            "NO_CURRENCY_OR_MARKET_CAP_UNIT_EVIDENCE",
        ]
        + (["FIXTURE_ONLY"] if mode == "FIXTURE" else []),
    }
    report["report_sha256"] = hashlib.sha256(_json(report)).hexdigest()
    return report
