"""Fictional SEC-shaped observations; no real filing or identity claims."""

import json
from datetime import UTC, datetime

import pytest

from packages.data.sec_facts import normalize_sec


def sources():
    index = {
        "cik": "0000000001",
        "filings": {
            "recent": {
                "accessionNumber": ["0000000001-20-000001", "0000000001-20-000002"],
                "acceptanceDateTime": ["2020-02-01T12:00:00Z", "2020-03-01T12:00:00Z"],
                "form": ["10-K", "10-K/A"],
                "primaryDocument": ["original.htm", "amended.htm"],
            }
        },
    }
    fact = {
        "accn": "0000000001-20-000001",
        "form": "10-K",
        "start": "2019-01-01",
        "end": "2019-12-31",
        "filed": "2020-02-01",
        "val": 100,
    }
    amendment = fact | {
        "accn": "0000000001-20-000002",
        "form": "10-K/A",
        "filed": "2020-03-01",
        "val": 90,
    }
    facts = {"cik": 1, "facts": {"us-gaap": {"Revenues": {"units": {"USD": [fact, amendment]}}}}}
    return index, facts


def normalize(index, facts, clock="2020-04-01T00:00:00+00:00", lag=24):
    return normalize_sec(
        json.dumps(index).encode(),
        json.dumps(facts).encode(),
        "explicit-unverified-id",
        datetime.fromisoformat(clock),
        lag,
    )


def test_accession_publication_lag_and_amendment_preservation():
    index, facts = sources()
    early = normalize(index, facts, "2020-02-02T23:59:59+00:00")
    assert early["facts"] == []
    first = normalize(index, facts, "2020-02-03T00:00:00+00:00")
    assert len(first["facts"]) == 1 and first["facts"][0]["value"] == 100
    later = normalize(index, facts)
    assert [f["value"] for f in later["facts"]] == [100, 90]
    assert later["facts"][1]["amended"] is True
    assert later["facts"][0]["published_at"] == "2020-02-02T00:00:00Z"
    assert later["status"].startswith("QUARANTINED")
    assert later["identity_assignment"] == "OPERATOR_SUPPLIED_UNVERIFIED"
    assert later == normalize(index, facts)


def test_missing_original_metadata_and_foreign_units_are_not_invented():
    index, facts = sources()
    rows = facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    rows.append(rows[0] | {"accn": "0000000001-19-000009"})
    facts["facts"]["us-gaap"]["Revenues"]["units"]["EUR"] = [rows[0]]
    report = normalize(index, facts)
    assert report["excluded_counts"]["missing_accession_metadata"] == 1
    assert report["excluded_counts"]["unsupported_unit"] == 1
    assert len(report["facts"]) == 2


@pytest.mark.parametrize(
    "change",
    ["cik", "columns", "timezone", "primary", "duplicate", "date", "conflict", "nonfinite"],
)
def test_invalid_sec_boundaries_fail_closed(change):
    index, facts = sources()
    recent = index["filings"]["recent"]
    rows = facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    if change == "cik":
        facts["cik"] = 2
    if change == "columns":
        recent["form"].pop()
    if change == "timezone":
        recent["acceptanceDateTime"][0] = "2020-02-01T12:00:00"
    if change == "primary":
        recent["primaryDocument"][0] = "../../secret"
    if change == "duplicate":
        recent["accessionNumber"][1] = recent["accessionNumber"][0]
    if change == "date":
        rows[0]["filed"] = "2020-01-01"
    if change == "conflict":
        rows.append(rows[0] | {"val": 999})
    if change == "nonfinite":
        rows[0]["val"] = float("nan")
    with pytest.raises(ValueError):
        normalize(index, facts)


def test_asof_and_processing_lag_boundaries():
    index, facts = sources()
    with pytest.raises(ValueError):
        normalize(index, facts, "2020-04-01T00:00:00")
    with pytest.raises(ValueError):
        normalize(index, facts, lag=-1)
    with pytest.raises(ValueError):
        normalize_sec(b"x" * (20 * 1024 * 1024 + 1), b"{}", "demo", datetime.now(UTC))


def test_safe_nested_primary_document_paths_preserve_source_citation():
    index, facts = sources()
    index["filings"]["recent"]["primaryDocument"][0] = "xslFixture/annual.htm"
    result = normalize(index, facts)
    assert result["facts"][0]["source_url"].endswith("/xslFixture/annual.htm")


def test_friday_after_hours_acceptance_does_not_publish_before_monday_filing():
    index, facts = sources()
    index["filings"]["recent"]["acceptanceDateTime"][0] = "2020-02-07T23:00:00Z"
    index["filings"]["recent"]["filingDate"] = ["2020-02-10", "2020-03-01"]
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["filed"] = "2020-02-10"
    assert normalize(index, facts, "2020-02-09T00:00:00+00:00")["facts"] == []
    assert normalize(index, facts, "2020-02-11T23:59:59+00:00")["facts"] == []
    result = normalize(index, facts, "2020-02-12T00:00:00+00:00")
    assert len(result["facts"]) == 1
    assert result["facts"][0]["published_at"] == "2020-02-11T00:00:00Z"
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["filed"] = "2020-02-11"
    with pytest.raises(ValueError, match="filing date"):
        normalize(index, facts)


@pytest.mark.parametrize(
    "path",
    [
        "a/../annual.htm",
        "/annual.htm",
        "a//b.htm",
        "a/%2e%2e/b.htm",
        "a\\b.htm",
        "https://example.org/a.htm",
        "a/b/c/d/e.htm",
    ],
)
def test_primary_document_paths_cannot_traverse_or_change_origin(path):
    index, facts = sources()
    index["filings"]["recent"]["primaryDocument"][0] = path
    with pytest.raises(ValueError, match="primary document"):
        normalize(index, facts)
