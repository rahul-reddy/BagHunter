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

from packages.backtest.constrained import PortfolioPolicy, comparator_runs, simulate
from packages.backtest.negative_controls import negative_controls
from packages.backtest.toy import evaluate
from packages.backtest.validation import diagnostics
from packages.data.fixture import fixture
from packages.data.providers import UnconfiguredMarketProvider
from packages.data.run_archive import verify_integrity, write_integrity
from packages.research.cohorts import cohort_grid
from packages.research.discovery import DiscoveryPolicy, discover
from packages.research.event_paths import EventPathPolicy, event_report, event_rows, event_study
from packages.research.features import VERSION, eligible, snapshot
from packages.research.outcomes import matched_pairs, outcome
from packages.research.reports import (
    candidate_memo,
    case_report,
    discovery_digest,
    stage_history_report,
)
from packages.research.sensitivity import ranking_sensitivity
from packages.research.technical import technical_report

DEFAULT_ASOF = "2022-01-03T23:00:00+00:00"


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def table(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        pq.write_table(pa.Table.from_pylist(rows), path)


def run(
    output: Path,
    asof: datetime,
    seed: int = 7,
    policy: DiscoveryPolicy | None = None,
    portfolio_policy: PortfolioPolicy | None = None,
    event_policy: EventPathPolicy | None = None,
) -> dict[str, Any]:
    if asof.utcoffset() is None:
        raise ValueError("asof must include timezone")
    asof = asof.astimezone(UTC)
    # Restrict fixture publishing to a fixture directory. Never overwrite real results.
    output = output.resolve()
    if "fixture" not in output.parts:
        raise ValueError("fixture outputs must be under a directory named fixture")
    dataset = fixture()
    raw = dataset.model_dump_json().encode()
    checksum = hashlib.sha256(raw).hexdigest()
    policy = policy or DiscoveryPolicy()
    portfolio_policy = portfolio_policy or PortfolioPolicy(seed=seed)
    event_policy = event_policy or EventPathPolicy(seed=seed)
    code_hash = hashlib.sha256()
    for module in sorted(Path(__file__).parent.rglob("*.py")):
        code_hash.update(module.relative_to(Path(__file__).parent).as_posix().encode())
        code_hash.update(module.read_text(encoding="utf-8").encode())
    code_digest = code_hash.hexdigest()
    policy_digest = hashlib.sha256(
        json.dumps(policy.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    portfolio_digest = hashlib.sha256(
        json.dumps(portfolio_policy.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    event_digest = hashlib.sha256(
        json.dumps(event_policy.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    run_key = hashlib.sha256(
        f"{checksum}:{asof.isoformat()}:{seed}:{VERSION}:{code_digest}:{policy_digest}:{portfolio_digest}:{event_digest}".encode()
    ).hexdigest()
    target = output / "runs" / run_key[:16]
    if target.exists():
        verify_integrity(target)
        raw_path = output.parent / "raw" / f"{checksum}.json"
        if raw_path.read_bytes() != raw:
            raise ValueError("Cached raw source mismatch")
        cached = json.loads((target / "run.json").read_text(encoding="utf-8"))
        if cached["run_id"] != run_key[:16] or cached["mode"] != "FIXTURE":
            raise ValueError("Cached run binding mismatch")
        pointer = output / f"current-{os.getpid()}.tmp"
        pointer.write_text(run_key[:16], encoding="utf-8")
        os.replace(pointer, output / "CURRENT")
        return {
            "run_id": cached["run_id"],
            "mode": "FIXTURE",
            "output": str(output),
            "signals": len(cached["signals"]),
            "labels": len(cached["study"]["labels"]),
            "pairs": len(cached["study"]["pairs"]),
            "evaluation_windows": len(cached["backtest"]["rows"]),
            "cache_reused": True,
        }
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
    discovery = discover(dataset, asof, policy or DiscoveryPolicy())
    features = discovery["signals"]
    if not features:
        raise ValueError("No eligible fixture instruments at requested asof")
    discovery["sensitivity"] = ranking_sensitivity(features, policy or DiscoveryPolicy())
    # Labels never passed to feature assembly. Separate on-disk hindsight namespace.
    anchor = datetime(2020, 1, 1, 23, tzinfo=UTC)
    labels = [
        outcome(i.security_id, dataset.bars, dataset.actions, anchor.date(), years)
        for i in dataset.instruments
        if eligible(i, anchor)
        for years in (1, 2, 3, 5)
    ]
    pairs = matched_pairs(dataset.instruments, labels, anchor, seed)
    study: dict[str, Any] = {
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
    study["cohorts"] = cohort_grid(dataset)
    study["event_paths"] = event_study(dataset, event_policy)
    backtest = evaluate(dataset, seed, policy)
    validation = diagnostics(backtest)
    validation["negative_controls"] = negative_controls(
        backtest["rows"], asof, seed, selector_model=backtest["model"]
    )
    validation["discovery_negative_controls"] = negative_controls(
        [
            row
            | {
                "candidates": row["discovery_candidates"],
                "eligible_count": len(row["discovery_candidates"]),
            }
            for row in backtest["rows"]
        ],
        asof,
        seed,
        selector_model=policy.version,
        selector_config_sha256=discovery["policy_sha256"],
    )
    portfolio = simulate(dataset, portfolio_policy or PortfolioPolicy())
    comparisons = comparator_runs(dataset, portfolio_policy)
    portfolio["comparator_runs"] = comparisons
    portfolio["comparators"] = [
        {
            "id": r["id"],
            "selector": r["policy"]["selector"],
            "allocation": r["policy"]["allocation"],
            "policy": r["policy"],
            "metrics": r["metrics"],
            "daily_risk": r["daily_risk"],
            "executions": len(r["executions"]),
            "excluded": len(r["exclusions"]),
            "ending_equity": r["ending_equity"],
        }
        for r in comparisons
    ]
    payload: dict[str, Any] = {
        "run_id": run_key[:16],
        "code_sha256": code_digest,
        "mode": "FIXTURE",
        "research_only": True,
        "asof": asof.isoformat(),
        "model_version": policy.version,
        "seed": seed,
        "sources": [source],
        "signals": sorted(features, key=lambda f: -f["score"]),
        "study": study,
        "backtest": backtest,
        "discovery": {k: v for k, v in discovery.items() if k != "signals"},
        "validation": validation,
        "portfolio": portfolio,
        "theses": [],
        "thesis_status": "BLOCKED: no real candidate evidence",
        "limitations": [
            "All market and filing observations are SYNTHETIC FIXTURES",
            "No empirical investment findings or live stock candidates",
            "Licensed historical PIT universe/delist data not configured",
            "SEC accession-bound facts stay quarantined; original extraction vintage unverified",
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
        table(staging / "hindsight" / "event_paths.parquet", event_rows(study["event_paths"]))
        table(staging / "hindsight" / "cohort_pairs.parquet", pairs)
        dump(staging / "reports" / "source_manifest.json", source)
        dump(staging / "reports" / "toy_backtest.json", backtest)
        dump(staging / "reports" / "validation.json", validation)
        dump(staging / "reports" / "technical_evidence.json", technical_report(payload))
        dump(staging / "reports" / "negative_controls.json", validation["negative_controls"])
        dump(
            staging / "reports" / "discovery_negative_controls.json",
            validation["discovery_negative_controls"],
        )
        dump(staging / "reports" / "portfolio.json", portfolio)
        dump(staging / "reports" / "portfolio_comparators.json", portfolio["comparator_runs"])
        dump(staging / "reports" / "portfolio_policy.json", portfolio["policy"])
        dump(staging / "reports" / "cohort_grid.json", study["cohorts"])
        dump(staging / "reports" / "event_paths.json", study["event_paths"])
        (staging / "reports" / "event_paths.md").write_text(
            event_report(study["event_paths"], payload["run_id"]), encoding="utf-8"
        )
        (staging / "reports" / "historical_cases.md").write_text(
            case_report(payload), encoding="utf-8"
        )
        (staging / "reports" / "discovery_digest.md").write_text(
            discovery_digest(payload), encoding="utf-8"
        )
        for feature in features:
            path = staging / "reports" / "theses" / f"{feature['security_id']}.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text(candidate_memo(payload, feature["security_id"]), encoding="utf-8")
        table(staging / "hindsight" / "multi_anchor_labels.parquet", study["cohorts"]["labels"])
        dump(staging / "reports" / "discovery_policy.json", discovery["policy"])
        dump(staging / "reports" / "stage_history.json", stage_history_report(payload))
        dump(staging / "reports" / "discovery_sensitivity.json", discovery["sensitivity"])
        with (staging / "reports" / "historical_cohorts.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=list(labels[0]))
            writer.writeheader()
            writer.writerows(labels)
        with (staging / "reports" / "baghunter_watchlist.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
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
            f"\nDate-local negative controls at {asof.isoformat()}: "
            f"{validation['negative_controls']['windows']} matured testable windows. "
            "See negative_controls.json for frozen ranks, irrelevant ranks, date-local null ranges "
            "and availability exclusions. Descriptive fixture checks only; no p-value, alpha "
            "or untouched-holdout claim.\n"
        )
        write_integrity(staging)
        # Immutable run folder + atomic pointer avoids partial reads during refresh.
        runs = output / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        target = runs / payload["run_id"]
        if target.exists():
            verify_integrity(target)
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
