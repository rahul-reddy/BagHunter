"""Explicit manual provider ingestion. Credentials never enter archives or public metadata."""

import hashlib
import json
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from packages.data.finviz import COLUMNS, MAX_BYTES, _json, _parse, _read, ingest_snapshot
from packages.data.providers import SecClient
from packages.data.sec_facts import NORMALIZATION_VERSION, normalize_sec
from packages.data.sec_history import (
    HISTORY_POLICY,
    MAX_HISTORY_FILES,
    MAX_RAW_BYTES,
    history_descriptors,
    normalize_history,
)


def refresh_finviz(token: str, *, usage_authorized: bool) -> dict[str, Any]:
    if not usage_authorized or not token or len(token) > 512 or any(ord(c) < 33 for c in token):
        raise ValueError("Authorized Finviz token required")
    endpoint = "https://elite.finviz.com/export.ashx"
    requested = datetime.now(UTC)
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        for hop in range(3):
            if hop:
                time.sleep(0.6)
            with client.stream("GET", endpoint, params={"v": "111", "auth": token}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    target = response.request.url.join(response.headers.get("location", ""))
                    if (
                        hop == 2
                        or target.scheme != "https"
                        or target.host != "elite.finviz.com"
                        or target.port not in (None, 443)
                        or target.path not in ("/export", "/export.ashx")
                        or target.userinfo
                        or target.fragment
                    ):
                        raise ValueError("Finviz redirect rejected")
                    endpoint = f"https://elite.finviz.com{target.path}"
                    continue
                response.raise_for_status()
                if "text/csv" not in response.headers.get("content-type", "").lower():
                    raise ValueError("Finviz response is not the supported CSV export")
                chunks = []
                size = 0
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("Finviz response exceeds size limit")
                    chunks.append(chunk)
                body = b"".join(chunks)
                break
        else:
            raise ValueError("Finviz redirect limit exceeded")
    if token.encode() in body:
        raise ValueError("Credential-bearing provider body rejected")
    rows = _parse(body)
    retrieved = datetime.now(UTC)
    digest = hashlib.sha256(body).hexdigest()
    manifest = {
        "provider": "Finviz Elite",
        "source_url": "https://elite.finviz.com/export.ashx",
        "parameters": {"v": "111"},
        "filters": [],
        "requested_at": requested.isoformat(),
        "retrieved_at": retrieved.isoformat(),
        "provider_observation_time": None,
        "status": "CURRENT_SNAPSHOT_UNVERIFIED_NOT_HISTORICAL_PIT",
        "sha256": digest,
        "rows": len(rows),
        "columns": COLUMNS,
        "bytes": len(body),
        "historical_coverage": "unverified",
        "adjustment_semantics": "unverified",
    }
    root = Path.cwd() / "data/finviz/inbox"
    if root.resolve() != root:
        raise ValueError("Finviz inbox must not traverse symlinks")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{retrieved.strftime('%Y%m%dT%H%M%S%fZ')}-{digest[:12]}"
    with tempfile.TemporaryDirectory(prefix=".refresh-", dir=root) as temporary:
        stage = Path(temporary) / "export"
        stage.mkdir()
        (stage / "screener.csv").write_bytes(body)
        (stage / "manifest.json").write_bytes(_json(manifest))
        stage.rename(destination)
    report = ingest_snapshot(
        destination / "screener.csv",
        destination / "manifest.json",
        mode="EXTERNAL_UNVERIFIED",
        usage_authorized=True,
    )
    return {k: report[k] for k in ("snapshot_id", "mode", "rows", "retrieved_at", "status")}


def sync_sec(
    cik: str, user_agent: str, asof: datetime, output: Path, *, include_history: bool = False
) -> dict[str, Any]:
    if asof.utcoffset() is None or asof > datetime.now(UTC):
        raise ValueError("SEC research clock must be aware and not future")
    if not cik.isdigit() or len(cik) > 10 or int(cik) <= 0:
        raise ValueError("Invalid SEC CIK")
    cik = f"{int(cik):010d}"
    if output.resolve() != output.absolute():
        raise ValueError("SEC output must not traverse symlinks")
    client = SecClient(user_agent, output / "raw")
    submissions = client.submissions(cik)
    companyfacts = client.companyfacts(cik)
    raw_submissions = _read(output / "raw" / f"{submissions['sha256']}.json", MAX_BYTES)
    raw_facts = _read(output / "raw" / f"{companyfacts['sha256']}.json", MAX_BYTES)
    local_id = f"sec-cik-{cik}-unverified"
    history: dict[str, bytes] = {}
    history_sources = []
    derived = None
    if include_history:
        descriptors = history_descriptors(raw_submissions)
        raw_size = len(raw_submissions) + len(raw_facts)
        for descriptor in descriptors:
            if raw_size >= MAX_RAW_BYTES:
                raise ValueError("SEC history raw size exceeds bound")
            source = client.submission_history(cik, descriptor["name"])
            body = _read(output / "raw" / f"{source['sha256']}.json", MAX_BYTES)
            raw_size += len(body)
            if raw_size > MAX_RAW_BYTES:
                raise ValueError("SEC history raw size exceeds bound")
            history[descriptor["name"]] = body
            history_sources.append({"name": descriptor["name"], "source": source})
        derived, normalized = normalize_history(raw_submissions, raw_facts, history, local_id, asof)
    else:
        normalized = normalize_sec(raw_submissions, raw_facts, local_id, asof)
    manifest = {
        "version": "sec-bundle-v1",
        "normalization_policy": NORMALIZATION_VERSION,
        "cik": cik,
        "security_id": local_id,
        "asof": asof.astimezone(UTC).isoformat(),
        "lag_hours": 24,
        "status": "QUARANTINED_SEC_ENTITY_NOT_SECURITY_IDENTITY",
        "submissions": submissions,
        "companyfacts": companyfacts,
    }
    if include_history:
        manifest.update(
            version="sec-bundle-v2-history",
            history_policy=HISTORY_POLICY,
            history_sources=history_sources,
        )
    identity = hashlib.sha256(_json(manifest)).hexdigest()
    root = output / "bundles"
    if root.resolve() != root.absolute():
        raise ValueError("SEC bundle root must not traverse symlinks")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / identity
    if destination.resolve() != destination.absolute():
        raise ValueError("SEC bundle must not traverse symlinks")
    files = {
        "manifest.json": _json(manifest),
        "submissions.json": raw_submissions,
        "companyfacts.json": raw_facts,
        "normalized.json": _json(normalized),
    }
    if derived is not None:
        files.update(history)
        files["derived-submissions.json"] = derived
    if sum(map(len, files.values())) > 80 * 1024 * 1024:
        raise ValueError("SEC bundle total size exceeds bound")
    if any(len(body) > MAX_BYTES for body in files.values()):
        raise ValueError("SEC bundle output exceeds size limit")
    if destination.exists():
        if destination.is_symlink() or {p.name for p in destination.iterdir()} != set(files):
            raise ValueError("SEC bundle member mismatch")
        for name, body in files.items():
            path = destination / name
            if path.is_symlink() or _read(path, MAX_BYTES) != body:
                raise ValueError("SEC bundle integrity mismatch")
    else:
        with tempfile.TemporaryDirectory(prefix=".sync-", dir=root) as temporary:
            stage = Path(temporary) / "bundle"
            stage.mkdir()
            for name, body in files.items():
                (stage / name).write_bytes(body)
            stage.rename(destination)
    return {
        "bundle_id": identity,
        "cik": cik,
        "status": manifest["status"],
        "facts": len(normalized["facts"]),
        "excluded_counts": normalized["excluded_counts"],
    }


def read_sec_bundle(bundle_id: str, *, include_statements: bool = False) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", bundle_id):
        raise ValueError("Invalid SEC bundle ID")
    folder = Path.cwd() / "data/real/sec/bundles" / bundle_id
    if folder.resolve() != folder:
        raise ValueError("SEC bundle must not traverse symlinks")
    if (folder / "manifest.json").is_symlink():
        raise ValueError("Linked SEC manifest")
    manifest = json.loads(_read(folder / "manifest.json", 64 * 1024))
    history_mode = manifest.get("version") == "sec-bundle-v2-history"
    keys = {
        "version",
        "normalization_policy",
        "cik",
        "security_id",
        "asof",
        "lag_hours",
        "status",
        "submissions",
        "companyfacts",
    }
    if history_mode:
        keys |= {"history_policy", "history_sources"}
    if (
        set(manifest) != keys
        or manifest["version"] not in ("sec-bundle-v1", "sec-bundle-v2-history")
        or manifest["normalization_policy"] != NORMALIZATION_VERSION
        or not re.fullmatch(r"\d{10}", manifest["cik"])
        or int(manifest["cik"]) <= 0
        or manifest["security_id"] != f"sec-cik-{manifest['cik']}-unverified"
        or manifest["status"] != "QUARANTINED_SEC_ENTITY_NOT_SECURITY_IDENTITY"
        or manifest["lag_hours"] != 24
        or hashlib.sha256(_json(manifest)).hexdigest() != bundle_id
    ):
        raise ValueError("SEC bundle manifest binding mismatch")
    names = {"manifest.json", "submissions.json", "companyfacts.json", "normalized.json"}
    if history_mode:
        if (
            manifest["history_policy"] != HISTORY_POLICY
            or not isinstance(manifest["history_sources"], list)
            or len(manifest["history_sources"]) > MAX_HISTORY_FILES
        ):
            raise ValueError("Invalid SEC history manifest")
        for item in manifest["history_sources"]:
            if (
                set(item) != {"name", "source"}
                or not isinstance(item["name"], str)
                or not re.fullmatch(
                    rf"CIK{manifest['cik']}-submissions-\d{{3}}\.json", item["name"]
                )
                or item["name"] in names
            ):
                raise ValueError("Invalid or duplicate SEC history archive member")
            names.add(item["name"])
        names.add("derived-submissions.json")
    if {p.name for p in folder.iterdir()} != names or any(
        p.is_symlink() or not p.is_file() for p in folder.iterdir()
    ):
        raise ValueError("SEC bundle member mismatch")
    if sum(p.stat().st_size for p in folder.iterdir()) > 80 * 1024 * 1024:
        raise ValueError("SEC bundle total size exceeds bound")
    asof = datetime.fromisoformat(manifest["asof"])
    if asof.utcoffset() is None or asof > datetime.now(UTC):
        raise ValueError("Invalid SEC research clock")
    raw = {}
    for name in ("submissions", "companyfacts"):
        metadata = manifest[name]
        prefix = "submissions" if name == "submissions" else "api/xbrl/companyfacts"
        if (
            set(metadata) != {"url", "sha256", "retrieved_at", "status", "license_note"}
            or metadata["url"] != f"https://data.sec.gov/{prefix}/CIK{manifest['cik']}.json"
            or metadata["status"] != "RAW_ONLY_NOT_PIT_NORMALIZED"
            or metadata["license_note"] != "SEC public source; no market data entitlement"
        ):
            raise ValueError("SEC source binding mismatch")
        retrieved = datetime.fromisoformat(metadata["retrieved_at"])
        if retrieved.utcoffset() is None or retrieved > datetime.now(UTC):
            raise ValueError("Invalid SEC retrieval clock")
        raw[name] = _read(folder / f"{name}.json", MAX_BYTES)
        if hashlib.sha256(raw[name]).hexdigest() != metadata["sha256"]:
            raise ValueError("SEC source checksum mismatch")
    if history_mode:
        parts = {}
        for item in manifest["history_sources"]:
            body = _read(folder / item["name"], MAX_BYTES)
            metadata = item["source"]
            expected_url = f"https://data.sec.gov/submissions/{item['name']}"
            _verify_sec_metadata(metadata, expected_url, body)
            parts[item["name"]] = body
        derived, normalized = normalize_history(
            raw["submissions"], raw["companyfacts"], parts, manifest["security_id"], asof
        )
        if _read(folder / "derived-submissions.json", MAX_BYTES) != derived:
            raise ValueError("SEC derived submissions integrity mismatch")
    else:
        normalized = normalize_sec(
            raw["submissions"], raw["companyfacts"], manifest["security_id"], asof
        )
    if _read(folder / "normalized.json", MAX_BYTES) != _json(normalized):
        raise ValueError("SEC normalized integrity mismatch")
    report = {"bundle_id": bundle_id, "manifest": manifest, "normalized": normalized}
    if include_statements:
        from packages.data.sec_statements import normalize_statements

        report["statements"] = normalize_statements(
            derived if history_mode else raw["submissions"],
            raw["companyfacts"],
            manifest["security_id"],
            asof,
        )
    return report


def _verify_sec_metadata(metadata: dict[str, Any], url: str, body: bytes) -> None:
    if (
        set(metadata) != {"url", "sha256", "retrieved_at", "status", "license_note"}
        or metadata["url"] != url
        or metadata["status"] != "RAW_ONLY_NOT_PIT_NORMALIZED"
        or metadata["license_note"] != "SEC public source; no market data entitlement"
        or hashlib.sha256(body).hexdigest() != metadata["sha256"]
    ):
        raise ValueError("SEC historical source binding/checksum mismatch")
    retrieved = datetime.fromisoformat(metadata["retrieved_at"])
    if retrieved.utcoffset() is None or retrieved > datetime.now(UTC):
        raise ValueError("Invalid SEC historical retrieval clock")
