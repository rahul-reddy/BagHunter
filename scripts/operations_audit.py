"""Bounded local archive recovery and HTTP load evidence; never fetch providers."""

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.data.run_archive import verify_integrity  # noqa: E402


def loopback_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.port is None
        or not 1 <= parsed.port <= 65535
    ):
        raise ValueError("Use an explicit http://127.0.0.1:PORT local API")
    return value.rstrip("/")


def inventory(root: Path, budget_bytes: int) -> dict[str, int]:
    if not root.is_dir() or root.is_symlink() or root.is_junction():
        raise ValueError("Archive root must be a real directory")
    size = count = 0
    pending = [root]
    while pending:
        folder = pending.pop()
        for path in folder.iterdir():
            count += 1
            if count > 100_000 or path.is_symlink() or path.is_junction():
                raise ValueError("Archive inventory limit or linked entry")
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                size += path.stat().st_size
                if size > budget_bytes:
                    raise ValueError("Archive exceeds declared disk budget")
            else:
                raise ValueError("Unsupported archive entry")
    return {"entries": count, "bytes": size, "budget_bytes": budget_bytes}


def recovery_check(root: Path, budget_bytes: int) -> dict:
    if root.is_symlink() or root.is_junction():
        raise ValueError("Linked archive root")
    root = root.resolve(strict=True)
    disk = inventory(root, budget_bytes)
    before = (root / "CURRENT").read_bytes()
    run_id = before.decode("utf-8").strip()
    if not re.fullmatch(r"[a-f0-9]{16}", run_id):
        raise ValueError("Invalid active run pointer")
    active = root / "runs" / run_id
    verify_integrity(active)
    payload = json.loads((active / "run.json").read_text(encoding="utf-8"))
    if payload["run_id"] != run_id or payload["mode"] != "FIXTURE":
        raise ValueError("Operational audit requires a bound fixture archive")
    digest = hashlib.sha256((active / "run.json").read_bytes()).hexdigest()
    # Copy only the validated active fixture. Never edit the source pointer/archive.
    with tempfile.TemporaryDirectory(prefix="baghunter-recovery-") as temporary:
        restored = Path(temporary) / "fixture"
        destination = restored / "runs" / run_id
        shutil.copytree(active, destination)
        (restored / "CURRENT").write_bytes(before)
        verify_integrity(destination)
        if hashlib.sha256((destination / "run.json").read_bytes()).hexdigest() != digest:
            raise ValueError("Restored archive differs")
    if (root / "CURRENT").read_bytes() != before:
        raise ValueError("Active run changed during audit; retry with writers stopped")
    return {
        "run_id": run_id,
        "run_sha256": digest,
        "disk": disk,
        "restore": "COPIED_ACTIVE_FIXTURE_VERIFIED_ALL_MANIFEST_ENTRIES",
        "scope": "Generated archive only; raw evidence and browser drafts need separate backup",
    }


def load_check(base: str, run_id: str, *, client: httpx.Client | None = None) -> dict:
    base = loopback_url(base)
    if not re.fullmatch(r"[a-f0-9]{16}", run_id):
        raise ValueError("Invalid load run binding")
    paths = ["/health", f"/runs/{run_id}", f"/runs/{run_id}/reports/source_manifest.json"] * 4

    def request(path: str, connection: httpx.Client) -> tuple[float, int]:
        start = time.perf_counter()
        body = bytearray()
        with connection.stream("GET", base + path) as response:
            if response.status_code != 200:
                raise ValueError("Local API load request failed")
            for part in response.iter_bytes():
                body.extend(part)
                if len(body) > 20 * 1024 * 1024:
                    raise ValueError("Local API response exceeds audit bound")
        data = json.loads(body)
        if path == "/health" and data.get("data_ready") is not True:
            raise ValueError("API is not ready")
        if path == f"/runs/{run_id}" and data.get("run_id") != run_id:
            raise ValueError("API returned another run")
        return time.perf_counter() - start, len(body)

    def execute(connection: httpx.Client) -> list[tuple[float, int]]:
        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(lambda path: request(path, connection), paths))

    start = time.perf_counter()
    if client is None:
        with httpx.Client(timeout=30, trust_env=False, follow_redirects=False) as connection:
            results = execute(connection)
    else:
        results = execute(client)
    elapsed = time.perf_counter() - start
    times = sorted(row[0] for row in results)
    return {
        "requests": len(results),
        "concurrency": 4,
        "elapsed_seconds": elapsed,
        "maximum_seconds": max(times),
        "p95_seconds": times[math.ceil(len(times) * 0.95) - 1],
        "response_bytes": sum(row[1] for row in results),
        "scope": "Bounded loopback HTTP smoke; not a capacity or production SLO claim",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/fixture/latest"))
    parser.add_argument("--disk-budget-mib", type=int, default=512)
    parser.add_argument("--api", help="Optional running local API; never starts a service")
    args = parser.parse_args()
    try:
        if not 1 <= args.disk_budget_mib <= 10_240:
            raise ValueError("Disk budget must be 1..10240 MiB")
        report = recovery_check(args.root, args.disk_budget_mib * 1024 * 1024)
        report["load"] = load_check(args.api, report["run_id"]) if args.api else None
    except (OSError, ValueError, TypeError, KeyError, httpx.HTTPError):
        raise SystemExit("Operations audit failed; raw details suppressed") from None
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
