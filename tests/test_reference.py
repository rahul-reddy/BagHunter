"""Fictional reference candidates: never a canonical identity or a historical mapping."""

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from test_finviz import export as export

from apps.api.main import app
from packages.data import reference
from packages.data.finviz import _json, ingest_snapshot, read_snapshot


def candidate(ticker="DEMO-A", figi="BBG000TST001", **extra):
    return {
        "figi": figi,
        "ticker": ticker,
        "name": "Fictional reference name",
        "exchCode": "US",
        "marketSector": "Equity",
        "securityType": "Common Stock",
        "securityType2": "Common Stock",
        "compositeFIGI": figi,
        "shareClassFIGI": "BBG000TST002",
        "securityDescription": ticker,
    } | extra


@pytest.fixture
def batch(export):
    csv_path, manifest_path = export()
    base = ingest_snapshot(csv_path, manifest_path, mode="FIXTURE", usage_authorized=True)
    _, rows = read_snapshot(base["snapshot_id"], "FIXTURE")
    jobs = reference._jobs(rows, 0, 2)

    def build(results=None, **edits):
        request = _json(jobs)
        raw = _json(
            results
            if results is not None
            else [{"data": [candidate()]}, {"warning": "No identifier found."}]
        )
        receipt = reference.Receipt(
            version=reference.VERSION,
            provider="OpenFIGI",
            source_url=reference.URL,
            mode="FIXTURE",
            base_snapshot_id=base["snapshot_id"],
            offset=0,
            limit=2,
            requested_at="2020-01-02T12:00:00Z",
            retrieved_at="2020-01-02T12:00:01Z",
            request_sha256=hashlib.sha256(request).hexdigest(),
            response_sha256=hashlib.sha256(raw).hexdigest(),
        ).model_copy(update=edits)
        return receipt, request, raw

    return build


def archive(batch, *args, **kwargs):
    return reference.archive_reference(*batch(*args, **kwargs))


def path(evidence):
    return Path("data/reference/openfigi") / evidence["mode"].lower() / evidence["reference_id"]


def test_reference_lineage_current_candidates_not_identity_promotion(batch, monkeypatch):
    evidence = archive(batch)
    assert evidence["counts"] == {"SINGLE_CANDIDATE": 1, "NO_MATCH_REPORTED": 1}
    assert evidence["queried"] == 2 and evidence["population"] == 2
    assert evidence["records"][0]["candidates"][0]["securityType"] == "Common Stock"
    assert all(
        not row["identity_promoted"] and not row["name_match_verified"]
        for row in evidence["records"]
    )
    assert (
        "FIXTURE_ONLY" in evidence["flags"]
        and "CURRENT_REFERENCE_ONLY_NOT_PIT" in evidence["flags"]
    )
    assert archive(batch) == evidence

    def fail(*args, **kwargs):
        raise AssertionError("Reference read attempted a write")

    monkeypatch.setattr(Path, "mkdir", fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    checked = reference.read_reference(
        evidence["reference_id"], evidence["base_snapshot_id"], "FIXTURE"
    )
    assert checked == evidence
    _, rows = read_snapshot(evidence["base_snapshot_id"], "FIXTURE")
    assert rows[0].security_id is None and rows[0].security_type == "unknown"


@pytest.mark.parametrize(
    "result,status",
    [
        ({"data": []}, "NO_CANDIDATES"),
        ({"error": "No identifier found."}, "NO_MATCH_REPORTED"),
        ({"error": "Provider refused this request"}, "PROVIDER_ISSUE"),
        ({"data": [candidate(), candidate(figi="BBG000TST003")]}, "AMBIGUOUS"),
        ({"data": [candidate(ticker="OTHER")]}, "CONTEXT_MISMATCH"),
        ({"data": [candidate(exchCode="LN")]}, "CONTEXT_MISMATCH"),
        ({"data": [candidate(marketSector="Corp")]}, "CONTEXT_MISMATCH"),
    ],
)
def test_ambiguity_errors_and_context_are_retained(batch, result, status):
    evidence = archive(batch, [result, {"data": []}])
    assert evidence["records"][0]["status"] == status
    assert evidence["records"][0]["identity_promoted"] is False


@pytest.mark.parametrize(
    "results",
    [
        None,
        {},
        [],
        [{"data": []}],
        [None, {"data": []}],
        [{"data": [], "warning": "bad"}, {"data": []}],
        [{"unknown": []}, {"data": []}],
        [{"data": [candidate(), candidate()]}, {"data": []}],
        [{"data": [candidate(figi="bad")]}, {"data": []}],
        [{"data": [candidate(name="bad\x01text")]}, {"data": []}],
        [{"data": [candidate(auth="PRIVATE")]}, {"data": []}],
        [{"error": 3}, {"data": []}],
        [{"data": [candidate(figi=f"BBG000TST{i:03d}") for i in range(101)]}, {"data": []}],
    ],
)
def test_malformed_or_unbounded_provider_results_reject(batch, results):
    receipt, request, _ = batch()
    raw = _json(results)
    receipt = receipt.model_copy(update={"response_sha256": hashlib.sha256(raw).hexdigest()})
    with pytest.raises((ValueError, TypeError)):
        reference.archive_reference(receipt, request, raw)


@pytest.mark.parametrize(
    "edit",
    [
        {"version": "future"},
        {"source_url": "https://example.invalid/?auth=PRIVATE"},
        {"provider": "Other"},
        {"offset": 2},
        {"limit": 11},
        {"requested_at": datetime(2019, 1, 1, tzinfo=UTC)},
        {"retrieved_at": datetime.now(UTC) + timedelta(days=1)},
        {"request_sha256": "0" * 64},
        {"response_sha256": "0" * 64},
    ],
)
def test_source_binding_clocks_and_resource_limits(batch, edit):
    with pytest.raises((ValueError, TypeError)):
        archive(batch, **edit)


@pytest.mark.parametrize(
    "name", ["manifest.json", "request.json", "response.json", "evidence.json"]
)
def test_reference_archive_tamper_and_wrong_base_rejected(batch, name):
    evidence = archive(batch)
    with pytest.raises(ValueError):
        reference.read_reference(evidence["reference_id"], "0" * 64, "FIXTURE")
    (path(evidence) / name).write_bytes(b"PRIVATE_CORRUPTION")
    with pytest.raises((ValueError, TypeError)):
        reference.read_reference(evidence["reference_id"], evidence["base_snapshot_id"], "FIXTURE")


def test_public_client_rate_limit_retry_without_credentials(batch, monkeypatch):
    receipt, request, response = batch()
    jobs = json.loads(request)
    attempts, waits = [], []
    monkeypatch.setenv("FINVIZ_TOKEN", "PRIVATE_SENTINEL")
    monkeypatch.setattr(reference.time, "sleep", waits.append)

    def respond(req):
        attempts.append(req)
        assert req.url.host == "api.openfigi.com" and req.method == "POST"
        assert req.content == request
        assert "PRIVATE_SENTINEL" not in str(req.headers) + req.content.decode()
        assert "x-openfigi-apikey" not in req.headers and "authorization" not in req.headers
        return (
            httpx.Response(429, headers={"retry-after": "5"})
            if len(attempts) == 1
            else httpx.Response(200, content=response)
        )

    body, started, retrieved = reference.OpenFigiClient(httpx.MockTransport(respond)).mapping(jobs)
    assert body == response and started <= retrieved
    assert len(attempts) == 2 and 5 in waits and any(wait > 3 for wait in waits)


@pytest.mark.parametrize(
    "status,header", [(302, None), (401, None), (429, "61"), (429, "bad"), (503, None)]
)
def test_public_client_rejects_http_failures_with_bounded_retries(
    batch, monkeypatch, status, header
):
    jobs = json.loads(batch()[1])
    attempts = []
    monkeypatch.setattr(reference.time, "sleep", lambda _: None)

    def respond(req):
        attempts.append(req)
        return httpx.Response(status, headers={} if header is None else {"retry-after": header})

    with pytest.raises(ValueError):
        reference.OpenFigiClient(httpx.MockTransport(respond)).mapping(jobs)
    assert len(attempts) <= 3


def test_client_rejects_oversize_response_and_unsupported_jobs(batch, monkeypatch):
    jobs = json.loads(batch()[1])
    monkeypatch.setattr(reference, "MAX_RESPONSE", 1)
    client = reference.OpenFigiClient(
        httpx.MockTransport(lambda _: httpx.Response(200, content=b"[]"))
    )
    with pytest.raises(ValueError, match="size cap"):
        client.mapping(jobs)
    for invalid in [[], jobs * 6, [jobs[0] | {"auth": "PRIVATE"}], [jobs[0] | {"idType": "OTHER"}]]:
        with pytest.raises(ValueError):
            client.mapping(invalid)


def test_reference_api_generic_errors_and_no_network(batch, monkeypatch):
    evidence = archive(batch)
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", evidence["base_snapshot_id"])
    monkeypatch.setenv("BAGHUNTER_REFERENCE_SNAPSHOT", evidence["reference_id"])
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", "FIXTURE")

    def fail(*args, **kwargs):
        raise AssertionError("API tried a vendor request")

    monkeypatch.setattr(reference.OpenFigiClient, "mapping", fail)
    client = TestClient(app)
    assert client.get("/finviz/reference").json() == evidence
    assert client.post("/finviz/reference").status_code == 405
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", "0" * 64)
    assert client.get("/finviz/reference").status_code == 503
    monkeypatch.setenv("BAGHUNTER_REFERENCE_SNAPSHOT", "../../.env")
    result = client.get("/finviz/reference")
    assert result.status_code == 503 and ".env" not in result.text


def test_cli_rejects_invalid_selection_without_echoing_details():
    result = subprocess.run(
        [sys.executable, "-m", "packages.cli", "fetch-reference", "--snapshot", "PRIVATE_SENTINEL"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "PRIVATE_SENTINEL" not in result.stdout + result.stderr
    assert "Reference lookup rejected" in result.stderr


def test_reference_archive_rejects_symlinked_members(batch, tmp_path):
    evidence = archive(batch)
    member = path(evidence) / "response.json"
    original = member.read_bytes()
    outside = tmp_path / "outside-response.json"
    outside.write_bytes(original)
    member.unlink()
    try:
        member.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="archive members"):
        reference.read_reference(evidence["reference_id"], evidence["base_snapshot_id"], "FIXTURE")
    assert outside.read_bytes() == original


def test_atomic_reference_publish_failure_leaves_no_partial_batch(batch, monkeypatch):
    monkeypatch.setattr(reference.time, "sleep", lambda _: None)

    def fail(*args, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(PermissionError):
        archive(batch)
    assert not list(Path("data/reference/openfigi/fixture").iterdir())
