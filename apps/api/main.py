"""Read-only local API. No execution endpoint or job-trigger endpoint."""

import csv
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from packages.data.finviz import read_snapshot
from packages.data.reference import read_reference

app = FastAPI(title="BagHunter — research only", version="0.1.0")


@app.get("/finviz/reference")
def finviz_reference() -> dict[str, Any]:
    mode = os.environ.get("BAGHUNTER_FINVIZ_MODE", "EXTERNAL_UNVERIFIED")
    if mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise HTTPException(503, "Invalid local reference source mode")
    try:
        return read_reference(
            os.environ.get("BAGHUNTER_REFERENCE_SNAPSHOT", ""),
            os.environ.get("BAGHUNTER_FINVIZ_SNAPSHOT", ""),
            mode,  # type: ignore[arg-type]
        )
    except (OSError, ValueError, TypeError, KeyError, csv.Error):
        raise HTTPException(
            503, "No valid reference evidence selected. See docs/REFERENCE.md."
        ) from None


@app.get("/finviz/observations")
def finviz_observations(
    q: str = Query(default="", max_length=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    snapshot_id = os.environ.get("BAGHUNTER_FINVIZ_SNAPSHOT", "")
    mode = os.environ.get("BAGHUNTER_FINVIZ_MODE", "EXTERNAL_UNVERIFIED")
    if mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise HTTPException(503, "Invalid local Finviz source mode")
    try:
        report, rows = read_snapshot(snapshot_id, mode)  # type: ignore[arg-type]
    except (OSError, ValueError, TypeError, KeyError, csv.Error):
        raise HTTPException(
            503, "No valid selected Finviz snapshot. See docs/FINVIZ.md for local setup."
        ) from None
    needle = q.strip().casefold()
    matching = sorted(
        (
            row
            for row in rows
            if needle
            in " ".join([row.ticker, row.company, row.sector or "", row.industry or ""]).casefold()
        ),
        key=lambda row: row.ticker,
    )
    now = datetime.now(UTC)
    age_hours = (now - datetime.fromisoformat(report["retrieved_at"])).total_seconds() / 3600
    return {
        "coverage": report,
        "served_at": now.isoformat(),
        "age_hours": age_hours,
        "stale": age_hours >= 24,
        "total": len(matching),
        "offset": offset,
        "limit": limit,
        "observations": [
            row.model_dump(mode="json")
            | {
                "volume_shares": None if row.volume_shares is None else str(row.volume_shares),
                "change_percent_reported": None
                if row.change_fraction is None
                else format((row.change_fraction * 100).normalize(), "f"),
            }
            for row in matching[offset : offset + limit]
        ],
    }


def current() -> dict[str, Any]:
    root = Path(os.environ.get("BAGHUNTER_DATA", "data/fixture/latest"))
    try:
        run_id = (root / "CURRENT").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9a-f]{16}", run_id):
            raise ValueError("invalid run pointer")
        data: dict[str, Any] = json.loads(
            (root / "runs" / run_id / "run.json").read_text(encoding="utf-8")
        )
        return data
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "No valid local run. Execute: uv run baghunter demo") from exc


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        current()
        ready = True
    except HTTPException:
        ready = False
    return {"status": "ok", "data_ready": ready, "research_only": True}


@app.get("/runs/current")
def latest() -> dict[str, Any]:
    data = current()
    data["served_at"] = datetime.now(UTC).isoformat()
    data["age_days"] = (datetime.now(UTC) - datetime.fromisoformat(data["asof"])).days
    return data


@app.get("/runs")
def runs() -> list[dict[str, Any]]:
    data = current()
    return [{k: data[k] for k in ("run_id", "mode", "asof", "model_version")}]


@app.get("/signals")
def signals(asof: str | None = None, stage: str | None = None) -> list[dict[str, Any]]:
    data = current()
    if asof and asof != data["asof"]:
        raise HTTPException(404, "Requested asof has not been materialized")
    return [f for f in data["signals"] if stage is None or f["stage"] == stage]


@app.get("/stocks/{security_id}/profile")
def profile(security_id: str, asof: str | None = None) -> dict[str, Any]:
    for f in signals(asof):
        if f["security_id"] == security_id:
            return f
    raise HTTPException(404, "No profile for this permanent ID")


@app.get("/sources/status")
def sources() -> list[dict[str, Any]]:
    return current()["sources"]  # type: ignore[no-any-return]


@app.get("/sources/{source_id}")
def source(source_id: str) -> dict[str, Any]:
    for item in sources():
        if item["source_id"] == source_id:
            return item
    raise HTTPException(404, "Source not found")


@app.get("/studies/{run_id}")
def study(run_id: str) -> dict[str, Any]:
    data = current()
    if data["run_id"] != run_id:
        raise HTTPException(404, "Run not found")
    return data["study"]  # type: ignore[no-any-return]


@app.get("/backtests/{run_id}")
def backtest(run_id: str) -> dict[str, Any]:
    data = current()
    if data["run_id"] != run_id:
        raise HTTPException(404, "Run not found")
    return data["backtest"]  # type: ignore[no-any-return]
