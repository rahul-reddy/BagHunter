"""Bounded SEC submissions pagination with original-source-preserving metadata union."""

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

from packages.data.finviz import MAX_BYTES, _json
from packages.data.sec_facts import normalize_sec

FIELDS = ("accessionNumber", "acceptanceDateTime", "filingDate", "form", "primaryDocument")
HISTORY_POLICY = "sec-submissions-union-v1"
MAX_HISTORY_FILES = 10
MAX_RAW_BYTES = 60 * 1024 * 1024


def history_descriptors(raw: bytes) -> list[dict[str, Any]]:
    if len(raw) > MAX_BYTES:
        raise ValueError("SEC submissions source exceeds size limit")
    current = json.loads(raw)
    cik = str(current["cik"])
    if not cik.isdigit() or len(cik) > 10 or int(cik) <= 0:
        raise ValueError("Invalid SEC history CIK")
    files = current["filings"].get("files", [])
    if not isinstance(files, list) or len(files) > MAX_HISTORY_FILES:
        raise ValueError("SEC history file count exceeds supported bound")
    names = set()
    for item in files:
        if (
            not isinstance(item, dict)
            or set(item) != {"name", "filingCount", "filingFrom", "filingTo"}
            or not isinstance(item["name"], str)
            or not re.fullmatch(rf"CIK{int(cik):010d}-submissions-\d{{3}}\.json", item["name"])
            or item["name"] in names
            or type(item["filingCount"]) is not int
            or not 1 <= item["filingCount"] <= 10_000
        ):
            raise ValueError("Invalid SEC history descriptor")
        if date.fromisoformat(item["filingFrom"]) > date.fromisoformat(item["filingTo"]):
            raise ValueError("Invalid SEC history date interval")
        names.add(item["name"])
    return sorted(files, key=lambda f: f["name"])


def normalize_history(
    current_raw: bytes,
    facts_raw: bytes,
    parts: dict[str, bytes],
    security_id: str,
    asof: datetime,
) -> tuple[bytes, dict[str, Any]]:
    descriptors = history_descriptors(current_raw)
    if set(parts) != {d["name"] for d in descriptors}:
        raise ValueError("SEC history parts do not match declared files")
    if (
        any(len(body) > MAX_BYTES for body in (current_raw, facts_raw, *parts.values()))
        or sum(map(len, (current_raw, facts_raw, *parts.values()))) > MAX_RAW_BYTES
    ):
        raise ValueError("SEC history total raw size exceeds bound")
    current = json.loads(current_raw)
    indexes: list[tuple[dict[str, Any] | None, dict[str, Any]]] = [
        (None, current["filings"]["recent"])
    ]
    indexes += [(d, json.loads(parts[d["name"]])) for d in descriptors]
    rows: dict[str, dict[str, str]] = {}
    duplicates = 0
    for descriptor, index in indexes:
        if not isinstance(index, dict) or any(not isinstance(index.get(k), list) for k in FIELDS):
            raise ValueError("SEC history requires complete accession column metadata")
        if "cik" in index and str(index["cik"]).lstrip("0") != str(int(current["cik"])):
            raise ValueError("SEC history payload CIK binding mismatch")
        count = len(index["accessionNumber"])
        if count > 10_000 or any(len(index[k]) != count for k in FIELDS):
            raise ValueError("SEC history column cardinality mismatch")
        if descriptor is not None and count != descriptor["filingCount"]:
            raise ValueError("SEC history declared filing count mismatch")
        within_source = set()
        for n in range(count):
            row = {k: index[k][n] for k in FIELDS}
            if any(not isinstance(v, str) for v in row.values()):
                raise ValueError("Invalid SEC history column value")
            filed = date.fromisoformat(row["filingDate"])
            if descriptor is not None and not (
                date.fromisoformat(descriptor["filingFrom"])
                <= filed
                <= date.fromisoformat(descriptor["filingTo"])
            ):
                raise ValueError("SEC history filing outside declared interval")
            accession = row["accessionNumber"]
            if accession in within_source:
                raise ValueError("Duplicate accession inside SEC source")
            within_source.add(accession)
            if accession in rows:
                if rows[accession] != row:
                    raise ValueError("Conflicting SEC accession metadata across sources")
                duplicates += 1
            else:
                rows[accession] = row
            if len(rows) > 10_000:
                raise ValueError("SEC merged accession count exceeds supported bound")
    # Some older non-electronic filings have no primary document. Preserve their raw rows
    # and coverage count, but never invent a source document to normalize an associated fact.
    missing_document = sum(not row["primaryDocument"] for row in rows.values())
    ordered = [rows[k] for k in sorted(rows) if rows[k]["primaryDocument"]]
    derived = _json(
        {
            "cik": current["cik"],
            "filings": {"recent": {k: [r[k] for r in ordered] for k in FIELDS}},
            "derivation_policy": HISTORY_POLICY,
        }
    )
    report = normalize_sec(derived, facts_raw, security_id, asof)
    report["submission_history"] = {
        "policy": HISTORY_POLICY,
        "parts": len(parts),
        "metadata_rows": len(rows),
        "usable_metadata_rows": len(ordered),
        "missing_primary_document_rows": missing_document,
        "duplicate_rows": duplicates,
        "current_submissions_sha256": hashlib.sha256(current_raw).hexdigest(),
        "parts_sha256": {
            name: hashlib.sha256(body).hexdigest() for name, body in sorted(parts.items())
        },
        "scope": "FETCHED_ACCESSION_METADATA_NOT_ORIGINAL_EXTRACTION_VINTAGES",
    }
    report["limitations"] = [
        "Merged current and declared historical submissions; unfetched/missing metadata is excluded"
        if text.startswith("Recent submissions only:")
        else text
        for text in report["limitations"]
    ] + ["submissions_sha256 is the derived union; original source hashes remain in the manifest"]
    return derived, report
