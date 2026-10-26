"""Reproducible comparisons of saved sources; never an identity approval."""

import hashlib
from collections import Counter, defaultdict
from typing import Any

from packages.data.finviz import Mode, _json, read_snapshot
from packages.data.reference import read_reference

POLICY = "company-share-class-comparison-v1"
IDENTIFIERS = ("figi", "compositeFIGI", "shareClassFIGI")


def compare_names(company: str, candidate_name: str) -> str:
    """Keep punctuation, suffixes, accents and class designations intact."""
    if company == candidate_name:
        return "EXACT_TEXT"
    if " ".join(company.casefold().split()) == " ".join(candidate_name.casefold().split()):
        return "CASE_WHITESPACE_ONLY"
    return "DIFFERENT_TEXT"


def inspect_reference(reference_id: str, base_snapshot_id: str, mode: Mode) -> dict[str, Any]:
    """Revalidate both archives and return reference plus a hash-bound comparison report.

    No network, writes, fuzzy selection, or promotion. Identifier reuse is checked only
    within this batch and each identifier level, and can represent legitimate aliases.
    """
    evidence = read_reference(reference_id, base_snapshot_id, mode)
    coverage, observations = read_snapshot(base_snapshot_id, mode)
    sources = {row.ticker: row for row in observations}
    owners: dict[str, dict[str, set[str]]] = {field: defaultdict(set) for field in IDENTIFIERS}
    for record in evidence["records"]:
        for candidate in record["candidates"]:
            for field in IDENTIFIERS:
                if candidate[field] is not None:
                    owners[field][candidate[field]].add(record["ticker"])

    records = []
    for record in evidence["records"]:
        source = sources[record["ticker"]]
        comparisons = []
        for candidate in record["candidates"]:
            name_comparison = compare_names(source.company, candidate["name"])
            issues = []
            if name_comparison == "DIFFERENT_TEXT":
                issues.append("COMPANY_NAME_DIFFERS")
            if record["status"] != "SINGLE_CANDIDATE":
                issues.append(record["status"])
            shared = {}
            for field in IDENTIFIERS:
                value = candidate[field]
                if value is None:
                    issues.append(f"MISSING_{field.upper()}")
                else:
                    others = sorted(owners[field][value] - {source.ticker})
                    if others:
                        shared[field] = others
                        issues.append(f"SHARED_{field.upper()}_IN_BATCH")
            comparisons.append(
                {
                    "figi": candidate["figi"],
                    "name_comparison": name_comparison,
                    "shared_identifiers": shared,
                    "issues": issues,
                    "disposition": "REVIEW_REQUIRED",
                    "identity_verified": False,
                    "share_class_verified": False,
                }
            )
        records.append(
            {
                "ticker": source.ticker,
                "source_company": source.company,
                "source_security_id": source.security_id,
                "source_security_type": source.security_type,
                "reference_status": record["status"],
                "disposition": "REVIEW_REQUIRED" if comparisons else "NO_CANDIDATE_EVIDENCE",
                "candidates": comparisons,
            }
        )

    report = {
        "policy_version": POLICY,
        "reference_id": reference_id,
        "base_snapshot_id": base_snapshot_id,
        "mode": mode,
        "source_sha256": coverage["source_sha256"],
        "source_retrieved_at": coverage["retrieved_at"],
        "reference_response_sha256": evidence["response_sha256"],
        "reference_retrieved_at": evidence["retrieved_at"],
        "scope": "SELECTED_BATCH_ONLY",
        "queried": evidence["queried"],
        "population": evidence["population"],
        "records": records,
        "name_comparison_counts": dict(
            Counter(c["name_comparison"] for r in records for c in r["candidates"])
        ),
        "issue_counts": dict(
            Counter(issue for r in records for c in r["candidates"] for issue in c["issues"])
        ),
        "identity_promotions": 0,
        "flags": [
            "TEXT_COMPARISON_NOT_IDENTITY_PROOF",
            "SHARE_CLASS_ASSIGNMENT_NOT_VERIFIED",
            "SHARED_IDENTIFIERS_MAY_BE_ALIASES",
            "NO_CROSS_BATCH_OR_HISTORICAL_CHECK",
            "INDEPENDENT_COMPANY_AND_CLASS_EVIDENCE_REQUIRED",
        ]
        + (["FIXTURE_ONLY"] if mode == "FIXTURE" else []),
    }
    report["report_sha256"] = hashlib.sha256(_json(report)).hexdigest()
    return evidence | {"reconciliation": report}
