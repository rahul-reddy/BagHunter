"""Accession-bound SEC companyfacts normalization; quarantined, never a PIT-vintage guarantee."""

import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from packages.shared.models import Fact

TAGS = {
    "Revenues": "annual_revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "annual_revenue",
    "SalesRevenueNet": "annual_revenue",
    "NetIncomeLoss": "annual_net_income",
    "OperatingIncomeLoss": "annual_operating_income",
    "NetCashProvidedByUsedInOperatingActivities": "annual_operating_cashflow",
}
NORMALIZATION_VERSION = "sec-annual-v2-publication-day"


def normalize_sec(
    submissions_raw: bytes,
    companyfacts_raw: bytes,
    security_id: str,
    asof: datetime,
    lag_hours: int = 24,
) -> dict[str, Any]:
    if asof.utcoffset() is None or not 0 <= lag_hours <= 720:
        raise ValueError("Aware asof and bounded nonnegative processing lag required")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", security_id):
        raise ValueError("Explicit local security ID required")
    if len(submissions_raw) > 20 * 1024 * 1024 or len(companyfacts_raw) > 20 * 1024 * 1024:
        raise ValueError("SEC source exceeds bounded local parser size")
    submissions = json.loads(submissions_raw)
    companyfacts = json.loads(companyfacts_raw)
    cik = str(submissions["cik"])
    if not cik.isdigit() or len(cik) > 10 or int(cik) != int(companyfacts["cik"]):
        raise ValueError("SEC CIK binding mismatch")
    accessions = accession_metadata(submissions)
    rows: dict[tuple[str, str, str], Fact] = {}
    unresolved = {
        "missing_accession_metadata": 0,
        "future_or_processing_lag": 0,
        "unsupported_period_or_form": 0,
        "unsupported_unit": 0,
    }
    for tag, metric in TAGS.items():
        concept = companyfacts.get("facts", {}).get("us-gaap", {}).get(tag)
        if concept is None:
            continue
        for unit, records in concept["units"].items():
            if not isinstance(records, list) or len(records) > 100_000:
                raise ValueError("Invalid or unbounded SEC fact records")
            for record in records:
                if unit != "USD":
                    unresolved["unsupported_unit"] += 1
                    continue
                accession = record["accn"]
                meta = accessions.get(accession)
                if meta is None:
                    unresolved["missing_accession_metadata"] += 1
                    continue
                if meta["form"] not in ("10-K", "10-K/A") or record["form"] != meta["form"]:
                    unresolved["unsupported_period_or_form"] += 1
                    continue
                end, start = date.fromisoformat(record["end"]), date.fromisoformat(record["start"])
                if not 330 <= (end - start).days <= 400:
                    unresolved["unsupported_period_or_form"] += 1
                    continue
                accepted = meta["accepted"]
                if accepted + timedelta(hours=lag_hours) > asof:
                    unresolved["future_or_processing_lag"] += 1
                    continue
                # Filing day and acceptance can differ after-hours/weekends. Date-only filed
                # is never an acceptance clock; use its following UTC midnight as a conservative
                # publication upper bound, then apply the configured processing lag.
                filed = date.fromisoformat(record["filed"])
                if type(record["val"]) not in (int, float):
                    raise ValueError("SEC fact must contain a numeric value")
                if (
                    (meta["filed"] is not None and filed != meta["filed"])
                    or (meta["filed"] is None and abs((filed - accepted.date()).days) > 1)
                    or filed < accepted.date() - timedelta(days=1)
                ):
                    raise ValueError("SEC fact filing date conflicts with accession metadata")
                publication = max(
                    accepted, datetime.combine(filed + timedelta(days=1), datetime.min.time(), UTC)
                )
                if publication + timedelta(hours=lag_hours) > asof:
                    unresolved["future_or_processing_lag"] += 1
                    continue
                fact = Fact(
                    security_id=security_id,
                    period_end=end,
                    accepted_at=accepted,
                    published_at=publication,
                    metric=metric,
                    value=record["val"],
                    unit=unit,
                    accession=accession,
                    amended=meta["form"].endswith("/A"),
                    source_id=f"sec-{int(cik)}-{accession}",
                    source_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession.replace('-', '')}/{meta['primary']}",
                )
                key = (metric, str(end), accession)
                if key in rows and rows[key].value != fact.value:
                    raise ValueError("Conflicting SEC taxonomy aliases or duplicate fact values")
                rows[key] = fact
    return {
        "normalization_policy": NORMALIZATION_VERSION,
        "status": "QUARANTINED_ACCESSION_BOUND_NOT_RESEARCH_READY",
        "cik": str(int(cik)),
        "security_id": security_id,
        "identity_assignment": "OPERATOR_SUPPLIED_UNVERIFIED",
        "asof": asof.astimezone(UTC).isoformat(),
        "processing_lag_hours": lag_hours,
        "submissions_sha256": hashlib.sha256(submissions_raw).hexdigest(),
        "companyfacts_sha256": hashlib.sha256(companyfacts_raw).hexdigest(),
        "facts": [f.model_dump(mode="json") for _, f in sorted(rows.items())],
        "excluded_counts": unresolved,
        "limitations": [
            "Current aggregate companyfacts is not proof of original extraction vintage",
            "Publication proxy: max(acceptance, following UTC midnight of official filing day)",
            "Configured processing lag follows the conservative publication proxy, not period end",
            "Recent submissions only: older facts without exact acceptance metadata are excluded",
            "Annual USD entity-wide concepts only; no class shares, quarters or custom taxonomies",
            "No automatic identity assignment, vintage certification or research activation",
        ],
    }


def accession_metadata(submissions: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact original accession metadata for all supported statement adapters."""
    index = submissions["filings"]["recent"]
    fields = ("accessionNumber", "acceptanceDateTime", "form", "primaryDocument")
    if any(not isinstance(index.get(k), list) for k in fields):
        raise ValueError("SEC accession metadata required")
    count = len(index["accessionNumber"])
    if count > 10_000 or any(len(index[k]) != count for k in fields):
        raise ValueError("SEC accession column cardinality mismatch")
    if "filingDate" in index and (
        not isinstance(index["filingDate"], list) or len(index["filingDate"]) != count
    ):
        raise ValueError("SEC filing-date cardinality mismatch")
    accessions = {}
    for n in range(count):
        accession = index["accessionNumber"][n]
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or accession in accessions:
            raise ValueError("Invalid or duplicate accession")
        accepted = datetime.fromisoformat(index["acceptanceDateTime"][n].replace("Z", "+00:00"))
        if accepted.utcoffset() is None:
            raise ValueError("Ambiguous SEC acceptance timezone")
        primary = index["primaryDocument"][n]
        if not re.fullmatch(
            r"(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,199}/){0,3}[A-Za-z0-9][A-Za-z0-9_.-]{0,199}",
            primary,
        ):
            raise ValueError("Invalid SEC primary document path")
        accessions[accession] = {
            "accepted": accepted.astimezone(UTC),
            "form": index["form"][n],
            "primary": primary,
            "filed": date.fromisoformat(index["filingDate"][n]) if "filingDate" in index else None,
        }
    return accessions
