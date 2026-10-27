"""Read-only local API. No execution endpoint or job-trigger endpoint."""

import csv
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from packages.backtest.robustness import robustness_markdown
from packages.data.finviz import _read, read_snapshot
from packages.data.provider_refresh import read_sec_bundle
from packages.data.reconciliation import inspect_reference
from packages.data.run_archive import verify_integrity
from packages.data.sec_statements import statement_analysis
from packages.research.event_paths import event_report
from packages.research.reports import (
    candidate_memo,
    case_report,
    discovery_digest,
    stage_history_report,
)
from packages.research.scenarios import Scenario, scenario
from packages.research.sec_profile import financial_profile
from packages.research.technical import technical_report

app = FastAPI(title="BagHunter — research only", version="0.1.0")


@app.get("/sec/bundles/{bundle_id}/statements")
def sec_statements(
    bundle_id: str,
    basis: Literal["QUARTER", "ANNUAL", "YTD_6M", "YTD_9M", "INSTANT"] = "QUARTER",
    offset: int = Query(default=0, ge=0, le=20_000),
    limit: int = Query(default=12, ge=1, le=100),
) -> dict[str, Any]:
    try:
        bundle = read_sec_bundle(bundle_id, include_statements=True)
        statements = bundle["statements"]
        rows = [row for row in statement_analysis(statements) if row["basis"] == basis]
    except (OSError, ValueError, TypeError, KeyError):
        raise HTTPException(
            503, "SEC statement source verification or interpretation failed"
        ) from None
    return {
        "bundle_id": bundle_id,
        "manifest": bundle["manifest"],
        "statements": {k: v for k, v in statements.items() if k != "facts"},
        "source_fact_count": len(statements["facts"]),
        "basis": basis,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "rows": rows[offset : offset + limit],
        "status": "DESCRIPTIVE_ENTITY_STATEMENTS_NOT_SECURITY_RANKING",
    }


@app.get("/sec/bundles")
def sec_bundles() -> dict[str, Any]:
    root = Path.cwd() / "data/real/sec/bundles"
    if root.resolve() != root:
        raise HTTPException(503, "Invalid SEC archive root")
    entries = []
    unavailable = 0
    for folder in sorted(root.glob("*"))[:200]:
        if not re.fullmatch(r"[a-f0-9]{64}", folder.name):
            continue
        try:
            if folder.resolve() != folder or (folder / "manifest.json").is_symlink():
                raise ValueError("Linked SEC index")
            metadata = json.loads(_read(folder / "manifest.json", 64 * 1024))
            if (
                not re.fullmatch(r"\d{10}", metadata["cik"])
                or metadata["status"] != "QUARANTINED_SEC_ENTITY_NOT_SECURITY_IDENTITY"
                or datetime.fromisoformat(metadata["asof"]).utcoffset() is None
            ):
                raise ValueError("Invalid SEC index")
            entries.append(
                {"bundle_id": folder.name, "cik": metadata["cik"], "asof": metadata["asof"]}
            )
        except (OSError, ValueError, TypeError, KeyError):
            unavailable += 1
    return {
        "bundles": sorted(entries, key=lambda e: e["asof"], reverse=True),
        "unavailable": unavailable,
        "status": "INDEX_ONLY_SELECTION_REVALIDATES_ALL_SOURCES",
    }


@app.get("/sec/bundles/{bundle_id}")
def sec_bundle(
    bundle_id: str,
    metric: Literal[
        "",
        "annual_revenue",
        "annual_net_income",
        "annual_operating_income",
        "annual_operating_cashflow",
    ] = "",
    offset: int = Query(default=0, ge=0, le=100_000),
    limit: int = Query(default=8, ge=1, le=100),
) -> dict[str, Any]:
    try:
        report = read_sec_bundle(bundle_id)
    except (OSError, ValueError, TypeError, KeyError):
        raise HTTPException(
            503, "No valid selected SEC bundle; source verification failed"
        ) from None
    normalized = report["normalized"]
    matches = [f for f in normalized["facts"] if not metric or f["metric"] == metric]
    return report | {
        "financial_profile": financial_profile(normalized),
        "normalized": normalized | {"facts": matches[offset : offset + limit]},
        "total": len(matches),
        "offset": offset,
        "limit": limit,
        "source_facts": len(normalized["facts"]),
    }


@app.get("/finviz/snapshots")
def finviz_snapshots() -> dict[str, Any]:
    entries = []
    unavailable = 0
    for mode in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        root = Path("data/finviz/snapshots") / mode.lower()
        if root.is_symlink() or root.is_junction():
            continue
        for folder in sorted(root.glob("*")):
            if not re.fullmatch(r"[a-f0-9]{64}", folder.name):
                continue
            try:
                if folder.is_symlink() or (folder / "coverage.json").is_symlink():
                    raise ValueError("Linked snapshot index")
                report = json.loads(_read(folder / "coverage.json", 64 * 1024))
                if report["snapshot_id"] != folder.name or report["mode"] != mode:
                    raise ValueError("Index binding mismatch")
                if type(report["rows"]) is not int or not 1 <= report["rows"] <= 100_000:
                    raise ValueError("Invalid index row count")
                if datetime.fromisoformat(report["retrieved_at"]).utcoffset() is None:
                    raise ValueError("Invalid index timestamp")
                entries.append(
                    {k: report[k] for k in ("snapshot_id", "mode", "rows", "retrieved_at")}
                )
            except (OSError, ValueError, KeyError, TypeError):
                unavailable += 1
    return {
        "snapshots": entries,
        "unavailable": unavailable,
        "status": "INDEX_METADATA_ONLY_SELECTION_REVALIDATES_SOURCE",
    }


@app.get("/finviz/references")
def finviz_references(
    snapshot: str = Query(pattern=r"^[a-f0-9]{64}$"), mode: str = "EXTERNAL_UNVERIFIED"
) -> list[dict[str, Any]]:
    if mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise HTTPException(422, "Invalid reference mode")
    result: list[dict[str, Any]] = []
    root = Path("data/reference/openfigi") / mode.lower()
    if root.is_symlink() or root.is_junction():
        return result
    for folder in sorted(root.glob("*")):
        if not re.fullmatch(r"[a-f0-9]{64}", folder.name):
            continue
        try:
            if folder.is_symlink() or (folder / "manifest.json").is_symlink():
                continue
            report = json.loads(_read(folder / "manifest.json", 64 * 1024))
            if report["base_snapshot_id"] == snapshot and report["mode"] == mode:
                if type(report["limit"]) is not int or not 1 <= report["limit"] <= 10:
                    raise ValueError("Invalid reference index count")
                if datetime.fromisoformat(report["retrieved_at"]).utcoffset() is None:
                    raise ValueError("Invalid reference index timestamp")
                result.append(
                    {
                        "reference_id": folder.name,
                        "retrieved_at": report["retrieved_at"],
                        "limit": report["limit"],
                    }
                )
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return result


@app.get("/finviz/reference")
def finviz_reference(
    snapshot: str | None = Query(default=None, pattern=r"^[a-f0-9]{64}$"),
    reference: str | None = Query(default=None, pattern=r"^[a-f0-9]{64}$"),
    mode: str | None = None,
) -> dict[str, Any]:
    mode = mode or os.environ.get("BAGHUNTER_FINVIZ_MODE", "EXTERNAL_UNVERIFIED")
    if mode not in ("FIXTURE", "EXTERNAL_UNVERIFIED"):
        raise HTTPException(503, "Invalid local reference source mode")
    try:
        return inspect_reference(
            reference or os.environ.get("BAGHUNTER_REFERENCE_SNAPSHOT", ""),
            snapshot or os.environ.get("BAGHUNTER_FINVIZ_SNAPSHOT", ""),
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
    snapshot: str | None = Query(default=None, pattern=r"^[a-f0-9]{64}$"),
    mode: str | None = None,
    sector: str = Query(default="", max_length=512),
    country: str = Query(default="", max_length=512),
    price_presence: Literal["ANY", "REPORTED", "MISSING"] = "ANY",
    min_volume: int | None = Query(default=None, ge=0, le=10**24),
    max_pe: Annotated[
        Decimal | None, Query(ge=0, le=10**24, max_digits=33, decimal_places=8)
    ] = None,
) -> dict[str, Any]:
    snapshot_id = snapshot or os.environ.get("BAGHUNTER_FINVIZ_SNAPSHOT", "")
    mode = mode or os.environ.get("BAGHUNTER_FINVIZ_MODE", "EXTERNAL_UNVERIFIED")
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
            and (not sector or row.sector == sector)
            and (not country or row.country == country)
            and (price_presence != "REPORTED" or row.price_reported is not None)
            and (price_presence != "MISSING" or row.price_reported is None)
            and (
                min_volume is None
                or (row.volume_shares is not None and row.volume_shares >= min_volume)
            )
            and (max_pe is None or (row.pe_reported is not None and 0 < row.pe_reported <= max_pe))
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
        "facets": {
            "sectors": sorted({row.sector for row in rows if row.sector}),
            "countries": sorted({row.country for row in rows if row.country}),
        },
        "applied_filters": {
            "q": q.strip(),
            "sector": sector,
            "country": country,
            "price_presence": price_presence,
            "min_volume": None if min_volume is None else str(min_volume),
            "max_pe": None if max_pe is None else str(max_pe),
        },
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


def read_run(run_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise HTTPException(404, "Invalid research run ID")
    root = Path(os.environ.get("BAGHUNTER_DATA", "data/fixture/latest"))
    folder = root / "runs" / run_id
    try:
        if folder.is_symlink() or (folder / "run.json").is_symlink():
            raise ValueError("Linked run archive")
        has_integrity = (folder / "integrity.json").exists()
        if has_integrity:
            verify_integrity(folder, only="run.json")
        data: dict[str, Any] = json.loads(_read(folder / "run.json", 20 * 1024 * 1024))
        if data["run_id"] != run_id or data["mode"] != "FIXTURE":
            raise ValueError("Invalid run binding or mode")
        data["archive_integrity"] = (
            "RUN_CHECKSUM_VERIFIED" if has_integrity else "LEGACY_NO_CHECKSUM_MANIFEST"
        )
        return data
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No valid saved research run") from None


def current() -> dict[str, Any]:
    root = Path(os.environ.get("BAGHUNTER_DATA", "data/fixture/latest"))
    try:
        run_id = (root / "CURRENT").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9a-f]{16}", run_id):
            raise ValueError("invalid run pointer")
        return read_run(run_id)
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
    root = Path(os.environ.get("BAGHUNTER_DATA", "data/fixture/latest"))
    result = []
    for folder in sorted((root / "runs").glob("*")):
        if not re.fullmatch(r"[0-9a-f]{16}", folder.name):
            continue
        try:
            data = read_run(folder.name)
            result.append({k: data[k] for k in ("run_id", "mode", "asof", "model_version")})
        except HTTPException:
            continue
    return sorted(result, key=lambda r: (r["asof"], r["run_id"]), reverse=True)


@app.get("/runs/{run_id}")
def saved_run(run_id: str) -> dict[str, Any]:
    data = read_run(run_id)
    data["age_days"] = (datetime.now(UTC) - datetime.fromisoformat(data["asof"])).days
    return data


@app.get("/runs/{run_id}/compare/{previous_id}")
def compare_runs(run_id: str, previous_id: str) -> dict[str, Any]:
    new, old = read_run(run_id), read_run(previous_id)
    if datetime.fromisoformat(old["asof"]) > datetime.fromisoformat(new["asof"]):
        raise HTTPException(422, "Comparison baseline must not be later than the selected run")
    before = {f["security_id"]: f for f in old["signals"]}
    after = {f["security_id"]: f for f in new["signals"]}
    rows = []
    for sid in sorted(before.keys() | after.keys()):
        left, right = before.get(sid), after.get(sid)
        rows.append(
            {
                "security_id": sid,
                "change": "ADDED" if left is None else "REMOVED" if right is None else "RETAINED",
                "before_stage": left["stage"] if left else None,
                "after_stage": right["stage"] if right else None,
                "score_change": right["score"] - left["score"] if right and left else None,
            }
        )
    return {
        "run_id": run_id,
        "previous_id": previous_id,
        "mode": "FIXTURE",
        "policy_changed": new.get("discovery", {}).get("policy_sha256")
        != old.get("discovery", {}).get("policy_sha256"),
        "changes": rows,
    }


@app.get("/runs/{run_id}/reports/{report_name}")
def report_download(run_id: str, report_name: str) -> Response:
    data = read_run(run_id)
    reports = {
        "technical_evidence.json": technical_report(data),
        "source_manifest.json": data["sources"],
        "validation.json": data.get("validation", {}),
        "negative_controls.json": data.get("validation", {}).get("negative_controls", {}),
        "discovery_negative_controls.json": data.get("validation", {}).get(
            "discovery_negative_controls", {}
        ),
        "discovery_policy.json": data.get("discovery", {}).get("policy", {}),
        "stage_history.json": stage_history_report(data),
        "robustness.json": data.get("validation", {}).get("robustness"),
        "discovery_sensitivity.json": data.get("discovery", {}).get("sensitivity", {}),
        "toy_backtest.json": data["backtest"],
        "portfolio.json": data.get("portfolio", {}),
        "portfolio_comparators.json": data.get("portfolio", {}).get("comparator_runs", []),
        "portfolio_policy.json": data.get("portfolio", {}).get("policy", {}),
        "cohort_grid.json": data["study"].get("cohorts", {}),
        "event_paths.json": data["study"].get("event_paths"),
    }
    if report_name == "robustness.md":
        return Response(
            robustness_markdown(data.get("validation", {}).get("robustness"), data["run_id"]),
            media_type="text/markdown; charset=utf-8",
        )
    if report_name == "event_paths.md":
        return Response(
            event_report(data["study"].get("event_paths"), data["run_id"]),
            media_type="text/markdown; charset=utf-8",
        )
    if report_name in reports:
        return Response(
            json.dumps(reports[report_name], indent=2, allow_nan=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
        )
    if report_name in ("baghunter_watchlist.csv", "historical_cohorts.csv"):
        import io

        rows = data["signals"] if report_name.startswith("baghunter") else data["study"]["labels"]
        fields = (
            ["security_id", "ticker", "asof_time", "stage", "score", "completeness"]
            if report_name.startswith("baghunter")
            else list(rows[0])
            if rows
            else [
                "security_id",
                "anchor",
                "horizon_years",
                "outcome_method",
                "max_multiple",
                "terminal_total_return",
                "max_drawdown",
                "delisted",
                "coverage_flag",
            ]
        )
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            stream.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
        )
    if report_name == "research_limitations.md":
        return Response(
            "# FIXTURE research limitations\n\n" + "\n".join(f"- {v}" for v in data["limitations"]),
            media_type="text/markdown; charset=utf-8",
        )
    if report_name in ("historical_cases.md", "discovery_digest.md"):
        text = case_report(data) if report_name == "historical_cases.md" else discovery_digest(data)
        return Response(
            text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
        )
    raise HTTPException(404, "Unknown report")


@app.get("/runs/{run_id}/dossiers/{security_id}")
def dossier_download(run_id: str, security_id: str) -> Response:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", security_id):
        raise HTTPException(404, "Invalid security ID")
    try:
        text = candidate_memo(read_run(run_id), security_id)
    except ValueError:
        raise HTTPException(404, "No candidate in this run") from None
    return Response(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="FIXTURE-{security_id}.md"'},
    )


@app.get("/scenario")
def calculate_scenario(
    revenue: float = Query(gt=0, le=1e15),
    shares: float = Query(ge=1, le=1e15),
    growth: float = Query(ge=-0.99, le=2),
    margin: float = Query(ge=-1, le=1),
    multiple: float = Query(ge=0, le=200),
    reference_price: float = Query(ge=1e-9, le=1e9),
    net_debt: float = Query(default=0, ge=-1e15, le=1e15),
    dilution: float = Query(default=0, ge=0, le=1),
    years: int = Query(default=3, ge=1, le=10),
) -> dict[str, Any]:
    return scenario(
        Scenario(
            revenue=revenue,
            shares=shares,
            growth=growth,
            margin=margin,
            multiple=multiple,
            reference_price=reference_price,
            net_debt=net_debt,
            dilution=dilution,
            years=years,
        )
    )


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
