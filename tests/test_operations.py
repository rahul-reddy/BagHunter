"""Operational evidence rejects bad bindings, missing readiness and disk overruns."""

import json

import httpx
import pytest

from packages.data.run_archive import write_integrity
from scripts.operations_audit import inventory, load_check, loopback_url, recovery_check


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://example.com:8000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000/path",
        "http://user:secret@127.0.0.1:8000",
        "http://127.0.0.1:8000?token=secret",
        "http://127.0.0.1:99999",
        "http://127.0.0.1:8000#fragment",
    ],
)
def test_only_explicit_loopback_api_is_accepted(url):
    with pytest.raises(ValueError):
        loopback_url(url)


def archive(tmp_path):
    root = tmp_path / "fixture"
    run_id = "a" * 16
    folder = root / "runs" / run_id
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(json.dumps({"run_id": run_id, "mode": "FIXTURE"}))
    (folder / "report.json").write_text('{"retained": true}')
    write_integrity(folder)
    (root / "CURRENT").write_text(run_id)
    return root, folder, run_id


def test_restore_checks_every_output_and_preserves_pointer(tmp_path):
    root, folder, run_id = archive(tmp_path)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = recovery_check(root, 1024 * 1024)
    assert result["run_id"] == run_id and result["disk"]["bytes"] > 0
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="budget"):
        inventory(root, 1)
    (folder / "report.json").write_text("corrupted")
    with pytest.raises(ValueError, match="checksum"):
        recovery_check(root, 1024 * 1024)
    assert (folder / "report.json").read_text() == "corrupted"


def test_restore_rejects_unsafe_or_unbound_pointer(tmp_path):
    root, folder, _ = archive(tmp_path)
    (root / "CURRENT").write_text("../../elsewhere")
    with pytest.raises(ValueError, match="pointer"):
        recovery_check(root, 1024 * 1024)
    (root / "CURRENT").write_text("b" * 16)
    with pytest.raises(OSError):
        recovery_check(root, 1024 * 1024)


def test_bounded_load_requires_readiness_run_binding_and_success():
    run_id = "a" * 16
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, json={"data_ready": True, "run_id": run_id})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = load_check("http://127.0.0.1:8000", run_id, client=client)
    assert report["requests"] == len(seen) == 12
    assert report["concurrency"] == 4 and report["response_bytes"] > 0
    assert report["maximum_seconds"] >= report["p95_seconds"] >= 0
    for status, body in [
        (200, {"data_ready": False}),
        (503, {}),
        (200, {"data_ready": True, "run_id": "b" * 16}),
    ]:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request, status=status, body=body: httpx.Response(status, json=body)
            )
        ) as client:
            with pytest.raises(ValueError):
                load_check("http://127.0.0.1:8000", run_id, client=client)
