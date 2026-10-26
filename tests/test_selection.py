"""Saved source selection stays explicit, read-only and bound to its archives."""

from pathlib import Path

from fastapi.testclient import TestClient
from test_finviz import export as export
from test_reference import archive
from test_reference import batch as batch

from apps.api.main import app


def test_source_and_reference_selection_without_environment_or_network(batch, monkeypatch):
    evidence = archive(batch)
    monkeypatch.delenv("BAGHUNTER_FINVIZ_SNAPSHOT", raising=False)
    monkeypatch.delenv("BAGHUNTER_REFERENCE_SNAPSHOT", raising=False)

    def fail(*args, **kwargs):
        raise AssertionError("Selection attempted network or writes")

    monkeypatch.setattr(Path, "write_bytes", fail)
    monkeypatch.setattr(Path, "mkdir", fail)
    monkeypatch.setattr("httpx.HTTPTransport.handle_request", fail)
    client = TestClient(app)
    snapshot = evidence["base_snapshot_id"]
    index = client.get("/finviz/snapshots").json()
    assert len(index["snapshots"]) == 1 and index["snapshots"][0]["snapshot_id"] == snapshot
    assert index["snapshots"][0]["mode"] == "FIXTURE"
    assert client.get("/finviz/observations").status_code == 503
    params = {"snapshot": snapshot, "mode": "FIXTURE"}
    response = client.get("/finviz/observations", params=params)
    assert response.status_code == 200 and response.json()["coverage"]["snapshot_id"] == snapshot
    references = client.get("/finviz/references", params=params).json()
    assert references[0]["reference_id"] == evidence["reference_id"]
    selected = client.get(
        "/finviz/reference", params=params | {"reference": evidence["reference_id"]}
    )
    assert (
        selected.status_code == 200 and selected.json()["reference_id"] == evidence["reference_id"]
    )
    assert (
        client.get("/finviz/reference", params=params | {"reference": "0" * 64}).status_code == 503
    )
    assert (
        client.get(
            "/finviz/observations", params=params | {"mode": "EXTERNAL_UNVERIFIED"}
        ).status_code
        == 503
    )
    assert client.get("/finviz/observations", params={"snapshot": "../private"}).status_code == 422
    assert client.get("/finviz/references", params=params | {"mode": "INVALID"}).status_code == 422
