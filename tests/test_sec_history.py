"""Historical SEC metadata provenance, overlap/conflict handling and bounded source selection."""

import copy
import json
from datetime import UTC, datetime

import httpx
import pytest

from packages.data import providers, sec_history
from packages.data.provider_refresh import read_sec_bundle, sync_sec
from packages.data.sec_facts import normalize_sec
from packages.data.sec_history import history_descriptors, normalize_history

NAME = "CIK0000000001-submissions-001.json"
CLOCK = datetime(2021, 4, 1, tzinfo=UTC)


def inputs():
    older = {
        "accessionNumber": ["0000000001-20-000001"],
        "acceptanceDateTime": ["2020-02-01T12:00:00Z"],
        "filingDate": ["2020-02-01"],
        "form": ["10-K"],
        "primaryDocument": ["original.htm"],
    }
    recent = {
        "accessionNumber": ["0000000001-21-000001"],
        "acceptanceDateTime": ["2021-02-01T12:00:00Z"],
        "filingDate": ["2021-02-01"],
        "form": ["10-K"],
        "primaryDocument": ["new.htm"],
    }
    current = {
        "cik": "1",
        "filings": {
            "recent": recent,
            "files": [
                {
                    "name": NAME,
                    "filingCount": 1,
                    "filingFrom": "2020-02-01",
                    "filingTo": "2020-02-01",
                }
            ],
        },
    }
    facts = {
        "cik": 1,
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "accn": older["accessionNumber"][0],
                                "form": "10-K",
                                "start": "2019-01-01",
                                "end": "2019-12-31",
                                "filed": "2020-02-01",
                                "val": 100,
                            },
                            {
                                "accn": recent["accessionNumber"][0],
                                "form": "10-K",
                                "start": "2020-01-01",
                                "end": "2020-12-31",
                                "filed": "2021-02-01",
                                "val": 200,
                            },
                        ]
                    }
                }
            }
        },
    }
    return current, facts, older


def raw(value):
    return json.dumps(value).encode()


def test_history_recovers_older_facts_without_changing_availability_or_original_sources():
    current, facts, older = inputs()
    before = copy.deepcopy((current, facts, older))
    recent = normalize_sec(raw(current), raw(facts), "test-id", CLOCK)
    assert [f["value"] for f in recent["facts"]] == [200]
    derived, full = normalize_history(
        raw(current), raw(facts), {NAME: raw(older)}, "test-id", CLOCK
    )
    assert [f["value"] for f in full["facts"]] == [100, 200]
    assert full["excluded_counts"]["missing_accession_metadata"] == 0
    assert full["submission_history"]["metadata_rows"] == 2
    assert full["submission_history"]["parts"] == 1
    assert full["submissions_sha256"] != full["submission_history"]["current_submissions_sha256"]
    assert json.loads(derived)["derivation_policy"] == "sec-submissions-union-v1"
    assert (current, facts, older) == before
    _, early = normalize_history(
        raw(current), raw(facts), {NAME: raw(older)}, "test-id", datetime(2020, 4, 1, tzinfo=UTC)
    )
    assert [f["value"] for f in early["facts"]] == [100]


def test_exact_cross_source_overlap_deduplicates_but_conflicts_reject():
    current, facts, older = inputs()
    for field, values in older.items():
        current["filings"]["recent"][field] += values
    _, report = normalize_history(raw(current), raw(facts), {NAME: raw(older)}, "test-id", CLOCK)
    assert report["submission_history"]["duplicate_rows"] == 1
    assert len(report["facts"]) == 2
    older["primaryDocument"][0] = "conflict.htm"
    with pytest.raises(ValueError, match="Conflicting"):
        normalize_history(raw(current), raw(facts), {NAME: raw(older)}, "test-id", CLOCK)


def test_missing_older_primary_document_remains_explicit_and_never_gets_an_invented_citation():
    current, facts, older = inputs()
    older["primaryDocument"][0] = ""
    _, report = normalize_history(raw(current), raw(facts), {NAME: raw(older)}, "test-id", CLOCK)
    assert [f["value"] for f in report["facts"]] == [200]
    assert report["submission_history"]["missing_primary_document_rows"] == 1
    assert report["submission_history"]["metadata_rows"] == 2
    assert report["submission_history"]["usable_metadata_rows"] == 1
    assert report["excluded_counts"]["missing_accession_metadata"] == 1


def test_internal_duplicates_reject():
    current, facts, older = inputs()
    for values in older.values():
        values *= 2
    current["filings"]["files"][0]["filingCount"] = 2
    with pytest.raises(ValueError, match="Duplicate accession inside"):
        normalize_history(raw(current), raw(facts), {NAME: raw(older)}, "test-id", CLOCK)


@pytest.mark.parametrize(
    "change",
    ["wrong_cik", "traversal", "duplicate", "too_many", "bad_count", "bad_range", "extra_field"],
)
def test_untrusted_history_descriptors_reject_before_part_requests(change):
    current, _, _ = inputs()
    item = current["filings"]["files"][0]
    if change == "wrong_cik":
        item["name"] = "CIK0000000002-submissions-001.json"
    if change == "traversal":
        item["name"] = "../../.env"
    if change == "duplicate":
        current["filings"]["files"] *= 2
    if change == "too_many":
        current["filings"]["files"] *= 11
    if change == "bad_count":
        item["filingCount"] = True
    if change == "bad_range":
        item["filingFrom"] = "2021-01-01"
    if change == "extra_field":
        item["secret"] = "must-not-propagate"
    with pytest.raises(ValueError):
        history_descriptors(raw(current))


@pytest.mark.parametrize(
    "change", ["missing_part", "extra_part", "count", "range", "columns", "size", "payload_cik"]
)
def test_incomplete_or_mismatched_parts_do_not_silently_reduce_denominator(change, monkeypatch):
    current, facts, older = inputs()
    parts = {NAME: raw(older)}
    if change == "missing_part":
        parts = {}
    if change == "extra_part":
        parts["unexpected.json"] = raw(older)
    if change == "count":
        current["filings"]["files"][0]["filingCount"] = 2
    if change == "range":
        current["filings"]["files"][0]["filingFrom"] = "2020-02-02"
        current["filings"]["files"][0]["filingTo"] = "2020-02-02"
    if change == "columns":
        del older["filingDate"]
        parts[NAME] = raw(older)
    if change == "size":
        monkeypatch.setattr(sec_history, "MAX_RAW_BYTES", 4)
    if change == "payload_cik":
        older["cik"] = 2
        parts[NAME] = raw(older)
    with pytest.raises(ValueError):
        normalize_history(raw(current), raw(facts), parts, "test-id", CLOCK)


def test_full_sync_reader_retains_v1_and_verifies_every_history_and_derived_byte(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    current, facts, older = inputs()
    requests = []
    original = httpx.Client

    def respond(request):
        requests.append(request.url.path)
        body = (
            older
            if request.url.path.endswith(NAME)
            else facts
            if "/companyfacts/" in request.url.path
            else current
        )
        return httpx.Response(200, json=body)

    monkeypatch.setattr(providers.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(respond), **kw)
    )
    output = tmp_path / "data/real/sec"
    v1 = sync_sec("1", "Fixture fixture@baghunter.invalid", CLOCK, output)
    v2 = sync_sec("1", "Fixture fixture@baghunter.invalid", CLOCK, output, include_history=True)
    assert v1["facts"] == 1 and v2["facts"] == 2
    assert sum(path.endswith(NAME) for path in requests) == 1
    assert read_sec_bundle(v1["bundle_id"])["manifest"]["version"] == "sec-bundle-v1"
    bundle = read_sec_bundle(v2["bundle_id"])
    assert bundle["manifest"]["version"] == "sec-bundle-v2-history"
    monkeypatch.setattr(httpx, "Client", original)
    from fastapi.testclient import TestClient

    from apps.api.main import app

    api = TestClient(app)
    endpoint = f"/sec/bundles/{v2['bundle_id']}"
    first = api.get(endpoint + "?limit=1").json()
    empty = api.get(endpoint + "?metric=annual_net_income").json()
    assert len(first["normalized"]["facts"]) == 1 and empty["total"] == 0
    assert first["financial_profile"] == empty["financial_profile"]
    assert first["financial_profile"]["periods"] == 2
    assert first["financial_profile"]["latest"]["revenue_growth"] == 1
    folder = output / "bundles" / v2["bundle_id"]
    derived = folder / "derived-submissions.json"
    original_derived = derived.read_bytes()
    derived.write_bytes(b"{}")
    with pytest.raises(ValueError, match="derived submissions integrity"):
        read_sec_bundle(v2["bundle_id"])
    derived.write_bytes(original_derived)
    (folder / NAME).write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        read_sec_bundle(v2["bundle_id"])


@pytest.mark.parametrize(
    "name", ["../../.env", "CIK0000000002-submissions-001.json", "https://attacker.invalid/a.json"]
)
def test_client_never_follows_unbound_history_name(tmp_path, monkeypatch, name):
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("No request allowed"))
    with pytest.raises(ValueError, match="filename/CIK"):
        providers.SecClient("Fixture fixture@baghunter.invalid", tmp_path).submission_history(
            "1", name
        )
