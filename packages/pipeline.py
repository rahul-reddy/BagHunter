"""Reproducible fixture pipeline; transactional publication and immutable raw snapshots."""

import csv
import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from packages.backtest.toy import evaluate
from packages.data.fixture import fixture
from packages.data.providers import UnconfiguredMarketProvider
from packages.research.features import VERSION, eligible, snapshot, symbol_at
from packages.research.outcomes import matched_pairs, outcome

DEFAULT_ASOF = "2022-01-03T23:00:00+00:00"


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def table(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        pq.write_table(pa.Table.from_pylist(rows), path)


def run(output: Path, asof: datetime, seed: int = 7) -> dict[str, Any]:
    if asof.utcoffset() is None:
        raise ValueError("asof must include timezone")
    # Restrict fixture publishing to a fixture directory. Never overwrite real results.
    output = output.resolve()
    if "fixture" not in output.parts:
        raise ValueError("fixture outputs must be under a directory named fixture")
    dataset = fixture()
    raw = dataset.model_dump_json().encode()
    checksum = hashlib.sha256(raw).hexdigest()
    source = {
        "source_id": "fixture-v1",
        "mode": "FIXTURE",
        "provider": "local-generator-v1",
        "url": "fixture://fixture-v1",
        "sha256": checksum,
        "license_note": "Synthetic local test observations; no real securities",
        "retrieved_at": "GENERATED_NOT_RETRIEVED",
        "coverage": "4 fictional instruments including benchmark; weekday calendar",
        "latest_source_timestamp": max(b.available_at for b in dataset.bars).isoformat(),
        "market_provider": UnconfiguredMarketProvider().get_coverage_report(),
    }
    features = []
    for instrument in dataset.instruments:
        if eligible(instrument, asof):
            f = snapshot(instrument, dataset.bars, dataset.facts, asof)
            f["ticker"] = symbol_at(dataset.symbols, instrument.security_id, asof)
            features.append(f)
    if not features:
        raise ValueError("No eligible fixture instruments at requested asof")
    # Labels never passed to feature assembly. Separate on-disk hindsight namespace.
    anchor = datetime(2020, 1, 1, 23, tzinfo=UTC)
    labels = [
        outcome(i.security_id, dataset.bars, dataset.actions, anchor.date(), years)
        for i in dataset.instruments
        if eligible(i, anchor)
        for years in (1, 2, 3, 5)
    ]
    pairs = matched_pairs(dataset.instruments, labels, anchor, seed)
    study = {
        "mode": "FIXTURE",
        "anchor": anchor.isoformat(),
        "labels": labels,
        "pairs": pairs,
        "denominator": 3,
        "scope": "Closed artificial universe, not empirical base rates",
        "matching": "As-of date, fixture industry/cap/liquidity/price buckets; seeded random",
        "anchor_features": [
            snapshot(i, dataset.bars, dataset.facts, anchor)
            for i in dataset.instruments
            if eligible(i, anchor)
        ],
    }
    backtest = evaluate(dataset, seed)
    run_key = hashlib.sha256(f"{checksum}:{asof.isoformat()}:{seed}:{VERSION}".encode()).hexdigest()
    code_hash = hashlib.sha256()
    for module in sorted(Path(__file__).parent.rglob("*.py")):
        code_hash.update(module.relative_to(Path(__file__).parent).as_posix().encode())
        code_hash.update(module.read_text(encoding="utf-8").encode())
    code_digest = code_hash.hexdigest()
    run_key = hashlib.sha256(f"{run_key}:{code_digest}".encode()).hexdigest()
    payload: dict[str, Any] = {
        "run_id": run_key[:16],
        "code_sha256": code_digest,
        "mode": "FIXTURE",
        "research_only": True,
        "asof": asof.isoformat(),
        "model_version": VERSION,
        "seed": seed,
        "sources": [source],
        "signals": sorted(features, key=lambda f: -f["score"]),
        "study": study,
        "backtest": backtest,
        "theses": [],
        "thesis_status": "BLOCKED: no real candidate evidence",
        "limitations": [
            "All market and filing observations are SYNTHETIC FIXTURES",
            "No empirical investment findings or live stock candidates",
            "Licensed historical PIT universe/delist data not configured",
            "SEC adapter raw download only; no PIT-normalized financial parser",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output.parent / "raw" / f"{checksum}.json"
    raw_path.parent.mkdir(exist_ok=True)
    if raw_path.exists() and raw_path.read_bytes() != raw:
        raise ValueError("raw checksum collision or corruption")
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    staging = Path(tempfile.mkdtemp(prefix="run-", dir=output.parent))
    try:
        dump(staging / "run.json", payload)
        dump(staging / "source_manifest.json", source)
        for name in ("instruments", "symbols", "bars", "facts", "actions"):
            table(
                staging / "silver" / f"{name}.parquet",
                [row.model_dump(mode="json") for row in getattr(dataset, name)],
            )
        table(staging / "gold" / "features.parquet", features)
        table(staging / "hindsight" / "labels.parquet", labels)
        table(staging / "hindsight" / "cohort_pairs.parquet", pairs)
        dump(staging / "reports" / "source_manifest.json", source)
        dump(staging / "reports" / "toy_backtest.json", backtest)
        with (staging / "reports" / "historical_cohorts.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(labels[0]))
            writer.writeheader()
            writer.writerows(labels)
        with (staging / "reports" / "alpha_watchlist.csv").open("w", newline="") as stream:
            fields = ["security_id", "ticker", "asof_time", "stage", "score", "completeness"]
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(features)
        (staging / "reports" / "research_limitations.md").write_text(
            "# FIXTURE ONLY — research limitations\n\n"
            + "\n".join(f"- {v}" for v in payload["limitations"])
            + "\n",
            encoding="utf-8",
        )
        (staging / "reports" / "failed_lookalikes.md").write_text(
            "# Synthetic failed lookalike\n\nDEMO-B is a fictional failed peer matched to DEMO-A.\n"
            "The fixture includes a zero-proceeds delisting; it is not a real case study.\n"
        )
        (staging / "reports" / "model_validation.md").write_text(
            "# Demonstration only\n\nFrozen 63-day momentum, next-open fills, 40 bps round-trip.\n"
            "13 sequential non-overlapping screening windows; no fitted model or holdout claim.\n"
            "See toy_backtest.json for dates, rows, comparators and limitations.\n"
        )
        # Immutable run folder + atomic pointer avoids partial reads during refresh.
        runs = output / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        target = runs / payload["run_id"]
        if not target.exists():
            # Windows scanners may briefly hold a freshly written directory open.
            for attempt in range(6):
                try:
                    os.replace(staging, target)
                    break
                except PermissionError:
                    if attempt == 5:
                        raise
                    time.sleep(0.1 * 2**attempt)
        pointer = output / f"current-{os.getpid()}.tmp"
        pointer.write_text(payload["run_id"], encoding="utf-8")
        os.replace(pointer, output / "CURRENT")
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "run_id": payload["run_id"],
        "mode": "FIXTURE",
        "output": str(output),
        "signals": len(features),
        "labels": len(labels),
        "pairs": len(pairs),
        "evaluation_windows": len(backtest["rows"]),
    }
