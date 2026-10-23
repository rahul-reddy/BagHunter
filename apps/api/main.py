"""Read-only local API. No execution endpoint or job-trigger endpoint."""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Alpha Hunter — research only", version="0.1.0")


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
