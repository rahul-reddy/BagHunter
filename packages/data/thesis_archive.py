"""Immutable offline persistence of fixture dossiers as unverified operator assertions."""

import hashlib
import json
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from packages.data.contracts import SCHEMAS
from packages.data.finviz import _json, _read
from packages.data.run_archive import verify_integrity
from packages.research.features import utc_asof
from packages.research.scenarios import Scenario
from packages.shared.numeric import require_finite

VERSION = "offline-thesis-assertions-v1"


def _plain(path: Path) -> Path:
    path = path.absolute()
    if path.resolve() != path or any(
        p.is_symlink() or p.is_junction() for p in [path, *path.parents]
    ):
        raise ValueError("Linked thesis archive path")
    return path


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate dossier field")
        result[key] = value
    return result


def import_thesis(dossier: Path, run_root: Path) -> dict[str, Any]:
    body = _read(_plain(dossier), 2 * 1024 * 1024)
    data = json.loads(body, object_pairs_hook=_object)
    require_finite(data, "thesis dossier")
    if (
        data["schema"] != "fixture-thesis-dossier-v2"
        or data["mode"] != "FIXTURE_USER_ASSUMPTIONS"
        or type(data["verified_real_theses"]) is not int
        or data["verified_real_theses"] != 0
    ):
        raise ValueError("Only explicitly unverified fixture dossiers can be imported")
    context = data["source_context"]
    run_id = context["run_id"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{16}", run_id):
        raise ValueError("Invalid dossier run ID")
    folder = _plain(run_root) / "runs" / run_id
    _plain(folder)
    verify_integrity(folder)
    run = json.loads(_read(folder / "run.json", 20 * 1024 * 1024))
    expected_context = {
        "mode": "FIXTURE",
        "run_id": run_id,
        "security_id": context["security_id"],
        "source_sha256s": [source["sha256"] for source in run["sources"]],
    }
    candidate = next(
        (row for row in run["signals"] if row["security_id"] == context["security_id"]), None
    )
    if (
        run["run_id"] != run_id
        or run["mode"] != "FIXTURE"
        or candidate is None
        or context != expected_context
        or data["candidate"] != candidate
        or data["sources"] != run["sources"]
        or utc_asof(datetime.fromisoformat(data["asof"]))
        != utc_asof(datetime.fromisoformat(run["asof"]))
    ):
        raise ValueError("Dossier does not match its saved run, candidate and sources")
    assumptions = data["assumptions"]
    if not isinstance(assumptions, dict) or set(assumptions) != set(Scenario.model_fields):
        raise ValueError("Every scenario assumption is required")
    numbers = {}
    for key, value in assumptions.items():
        if (
            not isinstance(value, str)
            or len(value) > 100
            or not re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", value)
        ):
            raise ValueError("Invalid explicit scenario assumption")
        numbers[key] = float(value)
    if not numbers["years"].is_integer():
        raise ValueError("Integer scenario horizon required")
    parsed = {**numbers, "years": int(numbers["years"])}
    Scenario.model_validate(parsed)
    workspace = data["research_workspace"]
    if not isinstance(workspace, dict):
        raise ValueError("Research workspace required")
    research_clock = utc_asof(datetime.fromisoformat(workspace["research_asof"]))
    if research_clock < utc_asof(datetime.fromisoformat(run["asof"])):
        raise ValueError("Dossier research clock precedes its saved run")
    # Imported narrative, comparisons and critique are preserved, never approved or executed.
    digest = hashlib.sha256(body).hexdigest()
    row = {
        "security_id": context["security_id"],
        "asof_time": data["asof"],
        "scenario_assumptions": _json(assumptions).decode(),
        "citations": _json(
            {
                "saved_candidate_evidence": candidate.get("evidence", []),
                "operator_qualitative_claims": workspace.get("qualitative", []),
                "operator_peer_claims": workspace.get("peers", []),
            }
        ).decode(),
        "adversarial_review": _json(
            {
                "status": "UNVERIFIED_IMPORTED_ATTRIBUTION",
                "claimed_status": data.get("critic_status"),
                "claimed_request_digest": data.get("request_digest"),
                "attachment": workspace.get("critic"),
            }
        ).decode(),
        "version": VERSION,
        "assertion_status": "FIXTURE_UNVERIFIED_OPERATOR_ASSERTIONS_NOT_PREDICTORS",
        "run_id": run_id,
        "dossier_sha256": digest,
    }
    table = pa.Table.from_pylist([row], schema=SCHEMAS["thesis"])
    root = _plain(Path.cwd() / "data/research/thesis_assertions/fixture")
    root.mkdir(parents=True, exist_ok=True)
    archive_id = hashlib.sha256(VERSION.encode() + body).hexdigest()
    target = _plain(root / archive_id)
    receipt = {
        "version": VERSION,
        "archive_id": archive_id,
        "run_id": run_id,
        "security_id": context["security_id"],
        "dossier_sha256": digest,
        "assertion_status": row["assertion_status"],
        "verified_real_theses": 0,
        "predictor_promotions": 0,
        "critic_independence_verified": False,
    }
    if target.exists():
        parquet = pa.BufferReader(_read(_plain(target / "thesis.parquet"), 4 * 1024 * 1024))
        metadata = pq.ParquetFile(parquet).metadata
        if (
            metadata.num_rows != 1
            or metadata.num_row_groups != 1
            or metadata.row_group(0).total_byte_size > 8 * 1024 * 1024
        ):
            raise ValueError("Invalid bounded thesis Parquet archive")
        parquet.seek(0)
        if (
            _read(_plain(target / "dossier.json"), len(body)) != body
            or not pq.read_table(parquet).equals(table)
            or json.loads(_read(_plain(target / "receipt.json"), 65536)) != receipt
        ):
            raise ValueError("Existing thesis assertion archive mismatch")
    else:
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=root) as temporary:
            stage = Path(temporary) / "assertion"
            stage.mkdir()
            (stage / "dossier.json").write_bytes(body)
            pq.write_table(table, stage / "thesis.parquet")
            (stage / "receipt.json").write_bytes(_json(receipt))
            for attempt in range(3):
                try:
                    stage.rename(target)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
    return receipt
