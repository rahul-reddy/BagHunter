"""Independent source, PIT, missingness, corruption and namespace boundaries for imports."""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.data import history
from packages.data.history import LocalHistoryProvider, Manifest, ingest
from packages.data.providers import MarketProvider

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "history-fixture"


@pytest.fixture
def bundle(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(EXAMPLE, target)
    return target


def change(bundle, name, edit):
    path = bundle / f"{name}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    edited = edit(value)
    path.write_text(json.dumps(value if edited is None else edited), encoding="utf-8")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_adapter_interface_and_dated_identity(bundle):
    provider: MarketProvider = LocalHistoryProvider(bundle)
    initial = provider.list_instruments("2020-01-01T23:00:00Z")
    assert {i["ticker"] for i in initial} == {"DEMO-H1", "DEMO-H2"}
    assert "delisted" not in initial[1] and "last_seen" not in initial[1]
    assert initial[0]["marketcap_asof"] is None
    assert len(provider.list_instruments("2020-01-03T23:00:00Z")) == 1
    assert provider.list_instruments("2020-01-04T00:00:00Z") == []  # expired, not carried forward
    assert len(provider.get_bars(["fixture-history-a"], "2020-01-02", "2020-01-03", "raw")) == 2
    with pytest.raises(ValueError, match="raw"):
        provider.get_bars(["fixture-history-a"], "2020-01-02", "2020-01-03", "adjusted")
    with pytest.raises(ValueError, match="permanent ID"):
        provider.get_actions(["unknown"])
    with pytest.raises(NotImplementedError, match="filing documents"):
        provider.get_filings("123", "2020-01-01", "2020-01-04")


def test_future_universe_revision_and_symbol_are_not_used(bundle):
    def universe(rows):
        rows.append(
            rows[0]
            | {
                "published_at": "2020-01-05T00:00:00Z",
                "eligible": False,
                "rejection_reason": "Later revision",
            }
        )

    change(bundle, "universe", universe)

    def symbols(rows):
        rows.append(rows[0] | {"ticker": "FUTURE", "published_at": "2020-01-05T00:00:00Z"})

    change(bundle, "symbols", symbols)
    provider = LocalHistoryProvider(bundle)
    assert provider.list_instruments("2020-01-02T00:00:00Z")[0]["ticker"] == "DEMO-H1"


def test_filing_processing_lag_and_amendments(bundle):
    fact = {
        "security_id": "fixture-history-a",
        "period_end": "2019-09-30",
        "accepted_at": "2020-01-02T12:00:00Z",
        "published_at": "2020-01-02T12:00:00Z",
        "metric": "revenue",
        "value": 100,
        "unit": "USD",
        "accession": "FIXTURE-ORIGINAL",
        "amended": False,
        "source_id": "fixture-history-v1",
        "source_url": "fixture://filing",
    }
    amended = fact | {
        "value": 900,
        "accepted_at": "2020-01-08T12:00:00Z",
        "published_at": "2020-01-08T12:00:00Z",
        "amended": True,
        "accession": "FIXTURE-AMENDMENT",
    }
    change(bundle, "facts", lambda _: [fact, amended])
    provider = LocalHistoryProvider(bundle)
    assert provider.get_fundamentals(["fixture-history-a"], "2020-01-03T11:59:59Z") == []
    known = provider.get_fundamentals(["fixture-history-a"], "2020-01-03T12:00:00Z")
    assert [row["value"] for row in known] == [100]
    assert len(provider.get_fundamentals(["fixture-history-a"], "2020-01-09T12:00:00Z")) == 2


@pytest.mark.parametrize("authorized", [False, 1, "true", None])
def test_authorization_is_explicit_boolean(bundle, authorized):
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["usage_authorized"] = authorized
    with pytest.raises(ValidationError, match="authorization"):
        Manifest.model_validate(manifest)


def test_credentials_in_source_reference_are_rejected_without_echo(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["source_url"] = "https://data.invalid/export?credential=do-not-echo"
    with pytest.raises(ValidationError) as caught:
        Manifest.model_validate(manifest)
    assert "do-not-echo" not in str(caught.value)


def test_checksum_tampering_is_rejected(bundle):
    (bundle / "bars.json").write_text("[]")
    with pytest.raises(ValueError, match="checksum mismatch"):
        LocalHistoryProvider(bundle)


@pytest.mark.parametrize(
    "table,mutation,expected",
    [
        ("bars", lambda rows: rows + [rows[0]], "duplicate bars"),
        ("bars", lambda rows: [rows[0] | {"security_id": "unknown"}], "unknown permanent"),
        ("bars", lambda rows: [rows[0] | {"source_id": "other"}], "source_id"),
        ("bars", lambda rows: [rows[0] | {"close": 0}], "greater than 0"),
        ("bars", lambda rows: [rows[0] | {"available_at": "2019-12-31T22:00:00Z"}], "precedes"),
        ("sessions", lambda rows: rows + [rows[0]], "sorted and unique"),
        ("symbols", lambda rows: rows + [rows[0] | {"ticker": "CONFLICT"}], None),
    ],
)
def test_corrupt_rows_fail_closed(bundle, table, mutation, expected):
    change(bundle, table, mutation)
    with pytest.raises(ValueError, match=expected):
        provider = LocalHistoryProvider(bundle)
        provider.list_instruments("2020-01-02T23:00:00Z")


def test_observations_after_retrieval_rejected(bundle):
    change(bundle, "bars", lambda rows: [rows[0] | {"available_at": "2021-01-01T22:00:00Z"}])
    with pytest.raises(ValueError, match="retrieval time"):
        LocalHistoryProvider(bundle)


def test_missing_calendar_prices_and_delist_proceeds_are_gaps(bundle):
    change(bundle, "bars", lambda rows: rows[1:])
    change(bundle, "actions", lambda _: [])
    provider = LocalHistoryProvider(bundle)
    report = provider.get_coverage_report()
    assert report["status"] == "QUARANTINED_NOT_RESEARCH_READY"
    assert report["counts"]["missing_price_sessions"] == 1
    assert set(report["coverage_flags"]) >= {
        "FIXTURE_ONLY",
        "FUNDAMENTALS_MISSING",
        "PRICE_SESSIONS_MISSING",
        "DELIST_PROCEEDS_UNRESOLVED",
    }
    assert report["unresolved_delist_ids"] == ["fixture-history-b"]


def test_quarantine_mode_separation_and_idempotent_archives(bundle, tmp_path):
    first = ingest(bundle, tmp_path / "imported")
    assert datetime.fromisoformat(first["ingested_at"]).utcoffset() is not None
    assert first == ingest(bundle, tmp_path / "imported")
    target = tmp_path / "imported" / "fixture" / first["snapshot_id"]
    assert (target / "silver" / "bars.parquet").exists()
    assert (target / "raw" / "facts.json").read_text() == "[]\n"
    assert not (target / "CURRENT").exists()
    assert not (tmp_path / "imported" / "external-unverified").exists()
    (target / "silver" / "bars.parquet").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="derived import archive"):
        ingest(bundle, tmp_path / "imported")
    with pytest.raises(ValueError, match="imported"):
        ingest(bundle, tmp_path / "fixture" / "latest")


def test_resource_caps_and_cli_error_do_not_echo_source_values(bundle, monkeypatch):
    monkeypatch.setattr(history, "MAX_EXPECTED_CELLS", 1)
    with pytest.raises(ValueError, match="audit budget"):
        LocalHistoryProvider(bundle)
    (bundle / "bars.json").write_text("invalid-source-value")
    result = subprocess.run(
        [sys.executable, "-m", "packages.cli", "audit-history", "--bundle", str(bundle)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Historical import rejected" in result.stderr
    assert "invalid-source-value" not in result.stderr


def test_byte_limit_is_bounded(tmp_path):
    target = tmp_path / "input"
    target.write_bytes(b"123456")
    with pytest.raises(ValueError, match="size limit"):
        history.read_bytes(target, limit=5)


def test_source_vintage_is_not_carried_into_the_future(bundle):
    provider = LocalHistoryProvider(bundle)
    with pytest.raises(ValueError, match="source vintage"):
        provider.list_instruments("2021-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="source vintage"):
        provider.get_fundamentals(["fixture-history-a"], "2021-01-01T00:00:00Z")


def test_realized_actions_cannot_be_future_predictions(bundle):
    change(bundle, "actions", lambda rows: [rows[0] | {"effective_date": "2021-01-01"}])
    with pytest.raises(ValueError, match="realized action"):
        LocalHistoryProvider(bundle)


def test_external_data_stays_unverified_in_separate_namespace(bundle, tmp_path):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    # Synthetic inputs exercise the external branch; this does not make them real observations.
    manifest.update(
        mode="EXTERNAL_UNVERIFIED",
        source_url="https://data.invalid/history",
        universe_basis="current_only",
        delisted_coverage="unknown",
        actions_coverage="unknown",
    )
    path.write_text(json.dumps(manifest), encoding="utf-8")
    report = ingest(bundle, tmp_path / "imported")
    assert report["mode"] == "EXTERNAL_UNVERIFIED"
    assert report["status"] == "QUARANTINED_NOT_RESEARCH_READY"
    assert set(report["coverage_flags"]) >= {
        "EXTERNAL_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED",
        "UNIVERSE_NOT_ARCHIVED_PIT",
        "DELISTED_COVERAGE_INCOMPLETE",
    }
    assert (tmp_path / "imported" / "external-unverified" / report["snapshot_id"]).is_dir()
    assert not (tmp_path / "imported" / "fixture").exists()


def test_transient_publish_locks_retry_without_partial_activation(bundle, tmp_path, monkeypatch):
    original = history.os.rename
    attempts = []

    def rename(source, target):
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError("transient file lock")
        return original(source, target)

    monkeypatch.setattr(history.os, "rename", rename)
    monkeypatch.setattr(history.time, "sleep", lambda _: None)
    report = ingest(bundle, tmp_path / "imported")
    assert len(attempts) == 3
    assert (tmp_path / "imported" / "fixture" / report["snapshot_id"] / "coverage.json").exists()


def test_future_ingestion_timestamp_cannot_be_reactivated(bundle, tmp_path):
    report = ingest(bundle, tmp_path / "imported")
    path = tmp_path / "imported" / "fixture" / report["snapshot_id"] / "coverage.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["ingested_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ValueError, match="ingestion timeline"):
        ingest(bundle, tmp_path / "imported")
