import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from packages.data.history import LocalHistoryProvider, ingest
from packages.data.providers import SecClient
from packages.pipeline import DEFAULT_ASOF, run


def main() -> None:
    parser = argparse.ArgumentParser(description="BagHunter — research only; demo is FIXTURE")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "ingest-demo", "study-demo", "backtest-demo"):
        cmd = sub.add_parser(name, help="Rebuild complete synthetic vertical slice")
        cmd.add_argument("--asof", default=DEFAULT_ASOF)
        cmd.add_argument("--seed", type=int, default=7)
        cmd.add_argument("--output", type=Path, default=Path("data/fixture/latest"))
    sec = sub.add_parser("sec-fetch", help="Raw real SEC submissions; not mixed with fixture")
    sec.add_argument("--cik", required=True)
    sec.add_argument("--output", type=Path, default=Path("data/real/sec/raw"))
    for name in ("audit-history", "ingest-history"):
        cmd = sub.add_parser(
            name, help="Validate a normalized export; quarantine only, no activation"
        )
        cmd.add_argument("--bundle", required=True, type=Path)
        if name == "ingest-history":
            cmd.add_argument("--output", type=Path, default=Path("data/imported"))
    args = parser.parse_args()
    if args.command in ("audit-history", "ingest-history"):
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
    elif args.command == "sec-fetch":
        result = SecClient(os.environ.get("SEC_USER_AGENT", ""), args.output).submissions(args.cik)
    else:
        result = run(args.output, datetime.fromisoformat(args.asof), args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
