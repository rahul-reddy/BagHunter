"""No implicit provider fallback or paid requests. SEC raw cache stays outside fixture results."""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx


class MarketProvider(Protocol):
    def list_instruments(self, asof: str) -> list[dict[str, Any]]: ...
    def get_bars(
        self, security_ids: list[str], start: str, end: str, adjustment: str
    ) -> list[dict[str, Any]]: ...
    def get_actions(self, security_ids: list[str]) -> list[dict[str, Any]]: ...
    def get_fundamentals(self, security_ids: list[str], asof: str) -> list[dict[str, Any]]: ...
    def get_filings(self, cik: str, start: str, end: str) -> list[dict[str, Any]]: ...
    def get_coverage_report(self) -> dict[str, Any]: ...


class UnconfiguredMarketProvider:
    def get_coverage_report(self) -> dict[str, Any]:
        return {
            "status": "BLOCKED",
            "provider": None,
            "delisted_coverage": "unknown",
            "reason": "No licensed PIT market-data entitlement configured",
        }

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(f"Market provider unavailable: {name}; no fallback to fixture")


class SecClient:
    """Single-process 2 req/s maximum; callers must coordinate concurrent processes.

    Fetches raw submissions only. Current companyfacts are NOT historical PIT facts.
    Historical pagination and accession-based financial parsing remain unimplemented.
    """

    def __init__(self, user_agent: str, cache: Path) -> None:
        if "@" not in user_agent or "example.com" in user_agent:
            raise ValueError("Set SEC_USER_AGENT with your organization and real contact email")
        self.user_agent = user_agent
        self.cache = cache
        self.last_request = 0.0

    def submissions(self, cik: str) -> dict[str, Any]:
        if not cik.isdigit() or len(cik) > 10:
            raise ValueError("CIK must contain 1–10 digits")
        url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        self.cache.mkdir(parents=True, exist_ok=True)
        with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=30) as client:
            for attempt in range(3):
                time.sleep(max(0, 0.5 - (time.monotonic() - self.last_request)))
                self.last_request = time.monotonic()
                response = client.get(url)
                if response.status_code in (429, 500, 502, 503) and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                body = response.content
                digest = hashlib.sha256(body).hexdigest()
                target = self.cache / f"{digest}.json"
                if not target.exists():
                    target.write_bytes(body)
                manifest = {
                    "url": url,
                    "sha256": digest,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "status": "RAW_ONLY_NOT_PIT_NORMALIZED",
                    "license_note": "SEC public source; no market data entitlement",
                }
                (self.cache / f"{digest}.manifest.json").write_text(json.dumps(manifest, indent=2))
                return manifest
        raise RuntimeError("SEC retries exhausted")
