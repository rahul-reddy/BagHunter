"""No implicit provider fallback or paid requests. SEC raw cache stays outside fixture results."""

import hashlib
import json
import re
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

    Fetches bounded raw submissions and companyfacts.
    Current companyfacts are NOT historical PIT facts.
    Explicit bounded historical submission parts are supported. The accession-bound annual parser
    does not certify original extraction vintages or automatically activate research data.
    """

    def __init__(self, user_agent: str, cache: Path) -> None:
        if (
            "@" not in user_agent
            or "example.com" in user_agent
            or len(user_agent) > 512
            or any(ord(c) < 32 for c in user_agent)
        ):
            raise ValueError("Set SEC_USER_AGENT with your organization and real contact email")
        self.user_agent = user_agent
        self.cache = cache
        self.last_request = 0.0

    def submissions(self, cik: str) -> dict[str, Any]:
        return self._fetch(cik, "submissions")

    def companyfacts(self, cik: str) -> dict[str, Any]:
        return self._fetch(cik, "companyfacts")

    def submission_history(self, cik: str, name: str) -> dict[str, Any]:
        return self._fetch(cik, "history", name)

    def _fetch(self, cik: str, resource: str, part: str | None = None) -> dict[str, Any]:
        if not cik.isdigit() or len(cik) > 10 or int(cik) == 0:
            raise ValueError("CIK must contain 1–10 digits and be positive")
        filename = f"CIK{int(cik):010d}.json"
        if resource == "history":
            if not isinstance(part, str) or not re.fullmatch(
                rf"CIK{int(cik):010d}-submissions-\d{{3}}\.json", part
            ):
                raise ValueError("Invalid SEC history filename/CIK binding")
            filename = part
        url = (
            f"https://data.sec.gov/submissions/{filename}"
            if resource in ("submissions", "history")
            else f"https://data.sec.gov/api/xbrl/companyfacts/{filename}"
        )
        if self.cache.resolve() != self.cache.absolute():
            raise ValueError("SEC cache must not traverse symlinks")
        self.cache.mkdir(parents=True, exist_ok=True)
        with httpx.Client(
            headers={"User-Agent": self.user_agent}, timeout=30, follow_redirects=False
        ) as client:
            for attempt in range(3):
                time.sleep(max(0, 0.5 - (time.monotonic() - self.last_request)))
                self.last_request = time.monotonic()
                with client.stream("GET", url) as response:
                    if response.status_code in (429, 500, 502, 503) and attempt < 2:
                        time.sleep(2**attempt)
                        continue
                    response.raise_for_status()
                    if "application/json" not in response.headers.get("content-type", "").lower():
                        raise ValueError("SEC response is not JSON")
                    chunks = []
                    size = 0
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):
                        size += len(chunk)
                        if size > 20 * 1024 * 1024:
                            raise ValueError("SEC response exceeds size limit")
                        chunks.append(chunk)
                body = b"".join(chunks)
                payload = json.loads(body)
                if resource == "history":
                    fields = (
                        "accessionNumber",
                        "acceptanceDateTime",
                        "filingDate",
                        "form",
                        "primaryDocument",
                    )
                    if not isinstance(payload, dict) or any(
                        not isinstance(payload.get(k), list) or len(payload[k]) > 10_000
                        for k in fields
                    ):
                        raise ValueError("Invalid SEC historical columns")
                    if "cik" in payload and str(payload["cik"]).lstrip("0") != str(int(cik)):
                        raise ValueError("SEC history CIK binding mismatch")
                elif (
                    not isinstance(payload, dict)
                    or not str(payload.get("cik", "")).isdigit()
                    or int(payload["cik"]) != int(cik)
                    or not isinstance(
                        payload.get("filings" if resource == "submissions" else "facts"), dict
                    )
                ):
                    raise ValueError("SEC resource/CIK binding mismatch")
                digest = hashlib.sha256(body).hexdigest()
                target = self.cache / f"{digest}.json"
                metadata = self.cache / f"{digest}.manifest.json"
                if target.is_symlink() or metadata.is_symlink():
                    raise ValueError("Linked SEC cache member")
                if target.exists() or metadata.exists():
                    from packages.data.finviz import _read

                    if _read(target, 20 * 1024 * 1024) != body:
                        raise ValueError("SEC cache integrity mismatch")
                    previous: dict[str, Any] = json.loads(_read(metadata, 64 * 1024))
                    retrieved = datetime.fromisoformat(previous["retrieved_at"])
                    if (
                        set(previous) != {"url", "sha256", "retrieved_at", "status", "license_note"}
                        or previous.get("url") != url
                        or previous.get("sha256") != digest
                        or previous.get("status") != "RAW_ONLY_NOT_PIT_NORMALIZED"
                        or previous.get("license_note")
                        != "SEC public source; no market data entitlement"
                        or retrieved.utcoffset() is None
                        or retrieved > datetime.now(UTC)
                    ):
                        raise ValueError("SEC manifest integrity mismatch")
                    return previous
                manifest = {
                    "url": url,
                    "sha256": digest,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "status": "RAW_ONLY_NOT_PIT_NORMALIZED",
                    "license_note": "SEC public source; no market data entitlement",
                }
                with target.open("xb") as stream:
                    stream.write(body)
                with metadata.open("x", encoding="utf-8") as stream:
                    json.dump(manifest, stream, indent=2)
                return manifest
        raise RuntimeError("SEC retries exhausted")
