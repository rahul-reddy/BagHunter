"""Fictional rows test provider-scale preservation, quarantine and corrupt input boundaries."""

import csv
import hashlib
import io
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from packages.data import finviz


@pytest.fixture
def export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path, manifest_path = tmp_path / "screen.csv", tmp_path / "manifest.json"
    rows = [
        [
            "1",
            "DEMO-A",
            "Fictional café",
            "Tech",
            "Widgets",
            "USA",
            "123.45",
            "12.5",
            "3.25",
            "-1.25%",
            "0",
        ],
        ["2", "DEMO-B", "Imaginary company", "-", "-", "-", "-", "N/A", "-", "-", "-"],
    ]
    manifest = {
        "provider": "Finviz Elite",
        "source_url": "https://elite.finviz.com/export",
        "parameters": {"v": "111"},
        "filters": [],
        "requested_at": "2020-01-01T12:00:00Z",
        "retrieved_at": "2020-01-01T12:00:01Z",
        "provider_observation_time": None,
        "status": "CURRENT_SNAPSHOT_UNVERIFIED_NOT_HISTORICAL_PIT",
        "historical_coverage": "unverified",
        "adjustment_semantics": "unverified",
    }

    def save(*, edit_rows=None, edit_manifest=None, columns=None):
        copied = [list(row) for row in rows]
        if edit_rows:
            edit_rows(copied)
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(columns or finviz.COLUMNS)
        writer.writerows(copied)
        body = stream.getvalue().encode("utf-8-sig")
        csv_path.write_bytes(body)
        value = manifest | {
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "rows": len(copied),
            "columns": columns or finviz.COLUMNS,
        }
        if edit_manifest:
            edit_manifest(value)
        manifest_path.write_text(json.dumps(value), encoding="utf-8")
        return csv_path, manifest_path

    save()
    return save


def ingest(export, mode="FIXTURE", **kwargs):
    csv_path, manifest_path = export(**kwargs)
    return finviz.ingest_snapshot(csv_path, manifest_path, mode=mode, usage_authorized=True)


def archive(report):
    return Path("data/finviz/snapshots") / report["mode"].lower() / report["snapshot_id"]


def test_units_missingness_identity_and_lineage(export):
    report = ingest(export)
    path = archive(report)
    rows = pq.read_table(path / "observations.parquet").to_pylist()
    assert rows[0]["market_cap_reported"] == Decimal("123.45")  # no guessed million multiplier
    assert rows[0]["change_fraction"] == Decimal("-0.0125")
    assert rows[0]["volume_shares"] == 0
    assert rows[0]["company"] == "Fictional café"
    assert rows[0]["security_id"] is None and rows[0]["security_type"] == "unknown"
    assert rows[1]["market_cap_reported"] is None and rows[1]["volume_shares"] is None
    assert report["missing"]["price_reported"] == 1
    assert report["status"] == "QUARANTINED_CURRENT_SNAPSHOT"
    assert "FIXTURE_ONLY" in report["flags"]
    assert report["provider_observation_time"] is None
    assert hashlib.sha256((path / "raw.csv").read_bytes()).hexdigest() == report["source_sha256"]
    assert ingest(export) == report  # preserves original ingestion time
    assert not list(Path("data").rglob("CURRENT"))
    assert not Path("data/fixture").exists()


def test_external_mode_separate_and_still_quarantined(export):
    fixture = ingest(export)
    external = ingest(export, "EXTERNAL_UNVERIFIED")
    assert fixture["snapshot_id"] != external["snapshot_id"]
    assert external["status"] == "QUARANTINED_CURRENT_SNAPSHOT"
    assert "NO_PIT_HISTORY" in external["flags"]
    assert "FIXTURE_ONLY" not in external["flags"]
    assert archive(fixture).exists() and archive(external).exists()


def test_zero_reported_pe_is_retained_and_flagged(export):
    report = ingest(export, edit_rows=lambda rows: rows[0].__setitem__(7, "0"))
    assert report["zero_pe_reported"] == 1
    assert (
        pq.read_table(archive(report) / "observations.parquet").to_pylist()[0]["pe_reported"] == 0
    )


def test_transient_publish_lock_is_retried(export, monkeypatch):
    original = Path.rename
    attempts = []

    def rename(path, target):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError("transient lock")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", rename)
    report = ingest(export)
    assert len(attempts) == 2 and archive(report).exists()


def test_symlink_output_is_rejected(export, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    try:
        (tmp_path / "data").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="symlinks"):
        ingest(export)
    with pytest.raises(ValueError, match="symlinks"):
        finviz.read_snapshot("0" * 64, "FIXTURE")
    assert not list((tmp_path / "elsewhere").iterdir())


@pytest.mark.parametrize(
    "field,value",
    [
        (1, "demo-a"),
        (2, "-"),
        (2, "bad\x01text"),
        (6, "NaN"),
        (6, "123M"),
        (6, "-3"),
        (6, "999999999999999999999999.12345678"),
        (7, "-1"),
        (8, "0"),
        (8, "Infinity"),
        (9, "2"),
        (9, "%"),
        (9, "-%"),
        (9, "N/A%"),
        (9, "+%"),
        (9, "-101%"),
        (10, "-1"),
        (10, "0.5"),
        (10, str(2**63)),
    ],
)
def test_invalid_cells_fail_closed(export, field, value):
    with pytest.raises(ValueError):
        ingest(export, edit_rows=lambda rows: rows[0].__setitem__(field, value))
    assert not Path("data").exists()


def test_duplicate_ticker_and_schema_drift(export):
    with pytest.raises(ValueError):
        ingest(export, edit_rows=lambda rows: rows[1].__setitem__(1, "DEMO-A"))
    with pytest.raises(ValueError):
        ingest(export, columns=finviz.COLUMNS + ["Unknown"])
    with pytest.raises(ValueError):
        ingest(export, edit_rows=lambda rows: rows[0].pop())


@pytest.mark.parametrize(
    "edit",
    [
        lambda m: m.update(retrieved_at="2099-01-01T00:00:00Z"),
        lambda m: m.update(requested_at="2020-01-02T00:00:00Z"),
        lambda m: m.update(retrieved_at="2020-01-01T12:00:01"),
        lambda m: m.update(source_url="https://elite.finviz.com/export?auth=PRIVATE"),
        lambda m: m.update(parameters={"v": "111", "auth": "PRIVATE"}),
        lambda m: m.update(filters=["arbitrary filter"]),
        lambda m: m.update(auth="PRIVATE"),
        lambda m: m.update(rows=3),
        lambda m: m.update(bytes=1),
        lambda m: m.update(sha256="0" * 64),
    ],
)
def test_manifest_trust_boundaries(export, edit):
    with pytest.raises(ValueError):
        ingest(export, edit_manifest=edit)


def test_limits_and_authorization(export, monkeypatch):
    csv_path, manifest_path = export()
    with pytest.raises(ValueError):
        finviz.ingest_snapshot(csv_path, manifest_path, mode="FIXTURE", usage_authorized=False)
    with pytest.raises(ValueError):
        finviz.ingest_snapshot(csv_path, manifest_path, mode="REAL", usage_authorized=True)
    monkeypatch.setattr(finviz, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="size limit"):
        finviz.load_export(csv_path, manifest_path)
    monkeypatch.setattr(finviz, "MAX_BYTES", 20 * 1024 * 1024)
    monkeypatch.setattr(finviz, "MAX_ROWS", 1)
    with pytest.raises(ValueError):
        finviz.load_export(csv_path, manifest_path)


@pytest.mark.parametrize(
    "name",
    [
        "raw.csv",
        "source-manifest.json",
        "observations.json",
        "coverage.json",
        "observations.parquet",
    ],
)
def test_archive_tampering_rejected(export, name):
    report = ingest(export)
    (archive(report) / name).write_bytes(b"corrupted")
    with pytest.raises((ValueError, OSError)):
        ingest(export)


def test_future_archive_clock_rejected(export):
    report = ingest(export)
    path = archive(report) / "coverage.json"
    value = json.loads(path.read_text())
    value["ingested_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        ingest(export)


def test_publish_failure_does_not_publish_partial_snapshot(export, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError("file locked")

    monkeypatch.setattr(finviz, "_parquet", fail)
    with pytest.raises(PermissionError):
        ingest(export)
    assert not list(Path("data/finviz/snapshots/fixture").iterdir())


def test_cli_suppresses_sensitive_manifest_values(export):
    csv_path, manifest_path = export(
        edit_manifest=lambda m: m.update(
            source_url="https://elite.finviz.com/export?auth=PRIVATE_SENTINEL"
        )
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "packages.cli",
            "ingest-finviz",
            "--csv",
            str(csv_path),
            "--manifest",
            str(manifest_path),
            "--mode",
            "FIXTURE",
            "--usage-authorized",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "PRIVATE_SENTINEL" not in result.stdout + result.stderr
    assert "Finviz import rejected" in result.stderr


def test_snapshot_reader_is_read_only_and_preserves_decimals(export, monkeypatch):
    report = ingest(export)

    def fail(*args, **kwargs):
        raise AssertionError("Reader attempted a mutation")

    monkeypatch.setattr(Path, "mkdir", fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    monkeypatch.setattr(Path, "write_text", fail)
    monkeypatch.setattr(Path, "rename", fail)
    checked, rows = finviz.read_snapshot(report["snapshot_id"], "FIXTURE")
    assert checked == report
    assert rows[0].market_cap_reported == Decimal("123.45")


def test_large_percentage_keeps_all_supported_digits(export):
    report = ingest(
        export, edit_rows=lambda rows: rows[0].__setitem__(9, "12345678901234567890.12345678%")
    )
    _, rows = finviz.read_snapshot(report["snapshot_id"], "FIXTURE")
    assert rows[0].change_fraction == Decimal("123456789012345678.9012345678")


@pytest.mark.parametrize(
    "name",
    [
        "raw.csv",
        "source-manifest.json",
        "observations.json",
        "coverage.json",
        "observations.parquet",
    ],
)
def test_snapshot_reader_rejects_tampering(export, name):
    report = ingest(export)
    (archive(report) / name).write_bytes(b"PRIVATE_CORRUPT_INPUT")
    with pytest.raises((ValueError, OSError)):
        finviz.read_snapshot(report["snapshot_id"], "FIXTURE")


def test_finviz_api_is_separate_paginated_and_explicitly_selected(export, monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    report = ingest(export)
    client = TestClient(app)
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", report["snapshot_id"])
    monkeypatch.delenv("BAGHUNTER_FINVIZ_MODE", raising=False)
    # No silent fallback to the fixture namespace when external mode is configured by default.
    assert client.get("/finviz/observations").status_code == 503
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", "FIXTURE")
    response = client.get("/finviz/observations?limit=1").json()
    assert response["coverage"]["mode"] == "FIXTURE"
    assert response["total"] == 2 and len(response["observations"]) == 1
    assert response["observations"][0]["market_cap_reported"] == "123.45"
    assert response["observations"][0]["volume_shares"] == "0"
    assert response["observations"][0]["change_percent_reported"] == "-1.25"
    assert response["observations"][0]["security_id"] is None
    assert response["stale"] is True and response["coverage"]["provider_observation_time"] is None
    assert client.get("/runs/current").status_code == 503  # no demo run required by Finviz
    assert (
        client.get("/finviz/observations?offset=1&limit=1").json()["observations"][0]["ticker"]
        == "DEMO-B"
    )
    assert client.get("/finviz/observations?q=FICTIONAL").json()["total"] == 1
    assert client.get("/finviz/observations?q=no-match").json()["observations"] == []
    assert client.get("/finviz/observations?offset=2").json()["observations"] == []
    for query in ["limit=101", "limit=0", "offset=-1", "offset=100001", "q=" + "x" * 101]:
        assert client.get("/finviz/observations?" + query).status_code == 422
    assert client.post("/finviz/observations").status_code == 405
    (archive(report) / "coverage.json").write_bytes(b"PRIVATE_CORRUPT_INPUT")
    error = client.get("/finviz/observations")
    assert error.status_code == 503 and "PRIVATE" not in error.text


@pytest.mark.parametrize(
    "snapshot,mode", [("../../.env", "FIXTURE"), ("", "FIXTURE"), ("0" * 64, "INVALID")]
)
def test_finviz_api_rejects_invalid_selection_without_creating_files(
    tmp_path, monkeypatch, snapshot, mode
):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", snapshot)
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", mode)
    assert TestClient(app).get("/finviz/observations").status_code == 503
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("value", [None, "PRIVATE_SCALAR", 3, True, []])
def test_scalar_coverage_report_is_rejected_with_generic_unavailable(export, monkeypatch, value):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    report = ingest(export)
    (archive(report) / "coverage.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        finviz.read_snapshot(report["snapshot_id"], "FIXTURE")
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", report["snapshot_id"])
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", "FIXTURE")
    response = TestClient(app).get("/finviz/observations")
    assert response.status_code == 503
    assert "PRIVATE_SCALAR" not in response.text


def test_reported_observation_filters_preserve_missingness_units_and_source(export, monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    report = ingest(export)
    client = TestClient(app)
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", report["snapshot_id"])
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", "FIXTURE")
    endpoint = "/finviz/observations"
    assert (
        client.get(
            endpoint + "?sector=Tech&country=USA&min_volume=0&max_pe=12.5&price_presence=REPORTED"
        ).json()["total"]
        == 1
    )
    assert client.get(endpoint + "?sector=tech").json()["total"] == 0  # exact reported category
    assert client.get(endpoint + "?min_volume=1").json()["total"] == 0  # zero != missing
    assert client.get(endpoint + "?max_pe=12.49").json()["total"] == 0
    missing = client.get(endpoint + "?price_presence=MISSING").json()
    assert [r["ticker"] for r in missing["observations"]] == ["DEMO-B"]
    assert missing["facets"] == {"sectors": ["Tech"], "countries": ["USA"]}
    assert missing["coverage"]["snapshot_id"] == report["snapshot_id"]
    assert missing["observations"][0]["security_id"] is None
    assert client.get(endpoint + "?min_volume=0").json()["applied_filters"]["min_volume"] == "0"
    for query in (
        "min_volume=-1",
        "min_volume=1.5",
        "min_volume=1000000000000000000000001",
        "max_pe=NaN",
        "max_pe=Infinity",
        "max_pe=-1",
        "price_presence=ELIGIBLE",
    ):
        assert client.get(endpoint + "?" + query).status_code == 422


def test_positive_pe_filter_excludes_reported_zero_and_missing(export, monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    report = ingest(export, edit_rows=lambda rows: rows[0].__setitem__(7, "0"))
    monkeypatch.setenv("BAGHUNTER_FINVIZ_SNAPSHOT", report["snapshot_id"])
    monkeypatch.setenv("BAGHUNTER_FINVIZ_MODE", "FIXTURE")
    client = TestClient(app)
    assert client.get("/finviz/observations").json()["total"] == 2
    assert client.get("/finviz/observations?max_pe=20").json()["total"] == 0
