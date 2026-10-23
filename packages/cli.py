import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from packages.data.providers import SecClient
from packages.pipeline import DEFAULT_ASOF, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Hunter — research only; demo is FIXTURE")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "ingest-demo", "study-demo", "backtest-demo"):
        cmd = sub.add_parser(name, help="Rebuild complete synthetic vertical slice")
        cmd.add_argument("--asof", default=DEFAULT_ASOF)
        cmd.add_argument("--seed", type=int, default=7)
        cmd.add_argument("--output", type=Path, default=Path("data/fixture/latest"))
    sec = sub.add_parser("sec-fetch", help="Raw real SEC submissions; not mixed with fixture")
    sec.add_argument("--cik", required=True)
    sec.add_argument("--output", type=Path, default=Path("data/real/sec/raw"))
    args = parser.parse_args()
    if args.command == "sec-fetch":
        result = SecClient(os.environ.get("SEC_USER_AGENT", ""), args.output).submissions(args.cik)
    else:
        result = run(args.output, datetime.fromisoformat(args.asof), args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
