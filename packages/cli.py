import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

from packages.backtest.constrained import PortfolioPolicy
from packages.data.finviz import _json, _read, ingest_snapshot
from packages.data.history import LocalHistoryProvider, ingest
from packages.data.issuer import audit_issuer
from packages.data.provider_config import provider_setting
from packages.data.provider_refresh import refresh_finviz, sync_sec
from packages.data.providers import SecClient
from packages.data.reconciliation import inspect_reference
from packages.data.reference import fetch_reference
from packages.data.sec_facts import normalize_sec
from packages.pipeline import DEFAULT_ASOF, run
from packages.research.discovery import DiscoveryPolicy


def main() -> None:
    parser = argparse.ArgumentParser(description="BagHunter — research only; demo is FIXTURE")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "ingest-demo", "study-demo", "backtest-demo"):
        cmd = sub.add_parser(name, help="Rebuild complete synthetic vertical slice")
        cmd.add_argument("--asof", default=DEFAULT_ASOF)
        cmd.add_argument("--seed", type=int, default=7)
        cmd.add_argument("--output", type=Path, default=Path("data/fixture/latest"))
        cmd.add_argument("--policy", type=Path, help="Local JSON discovery policy; fixture only")
        cmd.add_argument("--portfolio-policy", type=Path, help="Local JSON portfolio constraints")
    sec = sub.add_parser("sec-fetch", help="Raw real SEC submissions; not mixed with fixture")
    sec.add_argument("--cik", required=True)
    sec.add_argument("--output", type=Path, default=Path("data/real/sec/raw"))
    sec.add_argument("--env-file", type=Path, default=Path(".env"))
    sync = sub.add_parser(
        "sync-sec", help="Fetch real SEC pair and normalize into unverified bundles"
    )
    sync.add_argument("--cik", required=True)
    sync.add_argument("--asof", default=None)
    sync.add_argument(
        "--include-history",
        action="store_true",
        help="Fetch declared older submissions; bounded and source-preserving",
    )
    sync.add_argument("--env-file", type=Path, default=Path(".env"))
    refresh = sub.add_parser(
        "refresh-finviz", help="Fetch and quarantine a current overview snapshot"
    )
    refresh.add_argument("--env-file", type=Path, default=Path(".env"))
    refresh.add_argument("--usage-authorized", required=True, action="store_true")
    normalize = sub.add_parser(
        "normalize-sec", help="Accession-bound local SEC facts; quarantine only"
    )
    normalize.add_argument("--submissions", type=Path, required=True)
    normalize.add_argument("--companyfacts", type=Path, required=True)
    normalize.add_argument("--security-id", required=True)
    normalize.add_argument("--asof", required=True)
    normalize.add_argument("--lag-hours", type=int, default=24)
    normalize.add_argument("--output", type=Path, default=Path("data/real/sec/quarantine"))
    for name in ("audit-history", "ingest-history"):
        cmd = sub.add_parser(
            name, help="Validate a normalized export; quarantine only, no activation"
        )
        cmd.add_argument("--bundle", required=True, type=Path)
        if name == "ingest-history":
            cmd.add_argument("--output", type=Path, default=Path("data/imported"))
    finviz = sub.add_parser("ingest-finviz", help="Quarantine a local Finviz overview CSV snapshot")
    finviz.add_argument("--csv", required=True, type=Path)
    finviz.add_argument("--manifest", required=True, type=Path)
    finviz.add_argument("--mode", required=True, choices=["FIXTURE", "EXTERNAL_UNVERIFIED"])
    finviz.add_argument("--usage-authorized", required=True, action="store_true")
    reference = sub.add_parser(
        "fetch-reference", help="Fetch at most ten current OpenFIGI candidates"
    )
    reference.add_argument("--snapshot", required=True)
    reference.add_argument("--offset", type=int, default=0)
    reference.add_argument("--limit", type=int, default=10)
    reconcile = sub.add_parser(
        "reconcile-reference", help="Compare saved company/class evidence offline"
    )
    reconcile.add_argument("--snapshot", required=True)
    reconcile.add_argument("--reference", required=True)
    reconcile.add_argument("--mode", required=True, choices=["FIXTURE", "EXTERNAL_UNVERIFIED"])
    issuer = sub.add_parser("audit-issuer", help="Audit one local issuer evidence dossier offline")
    issuer.add_argument("--bundle", type=Path, required=True)
    issuer.add_argument("--snapshot", required=True)
    issuer.add_argument("--reference", required=True)
    issuer.add_argument("--mode", required=True, choices=["FIXTURE", "EXTERNAL_UNVERIFIED"])
    args = parser.parse_args()
    if args.command == "normalize-sec":
        try:
            report = normalize_sec(
                _read(args.submissions, 20 * 1024 * 1024),
                _read(args.companyfacts, 20 * 1024 * 1024),
                args.security_id,
                datetime.fromisoformat(args.asof),
                args.lag_hours,
            )
            if "quarantine" not in args.output.resolve().parts:
                raise ValueError("SEC normalized outputs must remain in quarantine")
            body = _json(report)
            digest = hashlib.sha256(body).hexdigest()
            args.output.mkdir(parents=True, exist_ok=True)
            target = args.output / f"{digest}.json"
            if target.exists() and _read(target, 20 * 1024 * 1024) != body:
                raise ValueError("Existing SEC output integrity mismatch")
            if not target.exists():
                with target.open("xb") as stream:
                    stream.write(body)
            result = {
                "status": report["status"],
                "facts": len(report["facts"]),
                "sha256": digest,
                "excluded_counts": report["excluded_counts"],
            }
        except (ValueError, OSError, TypeError, KeyError) as exc:
            print(
                f"SEC normalization rejected ({type(exc).__name__}); raw details suppressed.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command == "audit-issuer":
        try:
            report = audit_issuer(args.bundle, args.snapshot, args.reference, args.mode)
            result = {
                key: report[key]
                for key in (
                    "policy_version",
                    "mode",
                    "base_snapshot_id",
                    "reference_id",
                    "reconciliation_sha256",
                    "dossier_sha256",
                    "report_sha256",
                    "disposition",
                    "identity_promotions",
                    "flags",
                )
            } | {"document_count": len(report["documents"])}
        except (ValueError, OSError, TypeError, KeyError, csv.Error) as exc:
            print(
                f"Issuer dossier rejected ({type(exc).__name__}); raw details suppressed. "
                "See docs/ISSUER_EVIDENCE.md.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command == "reconcile-reference":
        try:
            report = inspect_reference(args.reference, args.snapshot, args.mode)["reconciliation"]
            result = {key: value for key, value in report.items() if key != "records"}
        except (ValueError, OSError, TypeError, KeyError, csv.Error) as exc:
            print(
                f"Reference comparison rejected ({type(exc).__name__}); raw details suppressed. "
                "See docs/REFERENCE.md.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command == "fetch-reference":
        try:
            evidence = fetch_reference(args.snapshot, args.offset, args.limit)
            result = {
                k: evidence[k]
                for k in (
                    "reference_id",
                    "base_snapshot_id",
                    "mode",
                    "queried",
                    "population",
                    "counts",
                    "flags",
                )
            }
        except (ValueError, OSError, TypeError, KeyError, csv.Error, httpx.HTTPError) as exc:
            print(
                f"Reference lookup rejected ({type(exc).__name__}); raw details suppressed. "
                "See docs/REFERENCE.md.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command == "ingest-finviz":
        try:
            result = ingest_snapshot(
                args.csv, args.manifest, mode=args.mode, usage_authorized=args.usage_authorized
            )
        except (ValueError, OSError, TypeError, KeyError, csv.Error) as exc:
            print(
                f"Finviz import rejected ({type(exc).__name__}): "
                "check local inputs against docs/FINVIZ.md; raw values suppressed.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command in ("audit-history", "ingest-history"):
        try:
            result = (
                ingest(args.bundle, args.output)
                if args.command == "ingest-history"
                else LocalHistoryProvider(args.bundle).get_coverage_report()
            )
        except (ValueError, OSError, TypeError, KeyError) as exc:
            # Validation errors may embed source values; never echo raw provider input.
            print(
                f"Historical import rejected ({type(exc).__name__}): "
                "invalid schema, checksum, access "
                "or archive integrity. "
                "Inspect the local bundle against docs/HISTORICAL_IMPORT.md.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    elif args.command in ("sec-fetch", "sync-sec", "refresh-finviz"):
        try:
            if args.command == "refresh-finviz":
                result = refresh_finviz(
                    provider_setting("FINVIZ_TOKEN", args.env_file),
                    usage_authorized=args.usage_authorized,
                )
            else:
                contact = provider_setting("SEC_USER_AGENT", args.env_file)
                if args.command == "sec-fetch":
                    result = SecClient(contact, args.output).submissions(args.cik)
                else:
                    from datetime import UTC

                    result = sync_sec(
                        args.cik,
                        contact,
                        datetime.fromisoformat(args.asof) if args.asof else datetime.now(UTC),
                        Path("data/real/sec"),
                        include_history=args.include_history,
                    )
        except (ValueError, OSError, TypeError, KeyError, csv.Error, httpx.HTTPError) as exc:
            print(
                f"Provider ingestion rejected ({type(exc).__name__}); "
                "credentials and response details suppressed.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    else:
        try:
            policy = (
                DiscoveryPolicy.model_validate_json(_read(args.policy, 64 * 1024))
                if args.policy
                else None
            )
            portfolio_policy = (
                PortfolioPolicy.model_validate_json(_read(args.portfolio_policy, 64 * 1024))
                if args.portfolio_policy
                else None
            )
            result = run(
                args.output, datetime.fromisoformat(args.asof), args.seed, policy, portfolio_policy
            )
        except (ValueError, OSError, TypeError, KeyError) as exc:
            print(
                f"Fixture refresh rejected ({type(exc).__name__}); raw details suppressed.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
