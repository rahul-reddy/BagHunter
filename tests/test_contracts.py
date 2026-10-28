"""Canonical Parquet fields, honest missing provenance and source/ledger boundaries."""

import copy
import hashlib
import json
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.main import app
from packages.data.contracts import SCHEMAS, canonical_tables, write_contracts
from packages.data.fixture import fixture
from packages.data.history import HistoricalInstrument, HistoricalSymbol
from packages.data.run_archive import write_integrity
from packages.shared.models import Bar, Fact


@pytest.fixture
def source_and_run():
    source = fixture()
    run = {
        "mode": "FIXTURE",
        "run_id": "a" * 16,
        "asof": "2022-01-03T23:00:00+00:00",
        "sources": [
            {
                "sha256": hashlib.sha256(source.model_dump_json().encode()).hexdigest(),
                "source_id": "fixture-v1",
                "provider": "local-generator-v1",
                "url": "fixture://fixture-v1",
                "license_note": "Synthetic local observations",
                "coverage": "Four fictional instruments",
            }
        ],
        "signals": [{"security_id": "fx-compound", "dollar_volume_20d": 12345}],
        "portfolio": {
            "executions": [
                {
                    "security_id": "fx-compound",
                    "entry": "2021-01-04",
                    "exit": "2021-02-01",
                    "shares": 5,
                    "entry_price": 10,
                    "entry_cost": 1,
                    "exit_cost": 2,
                    "terminal_wealth": 100,
                }
            ],
            "exclusions": [
                {
                    "security_id": "fx-failure",
                    "decision": "2021-01-01",
                    "reason": "PRICE_OR_LIQUIDITY_FLOOR",
                }
            ],
        },
    }
    return source, run


def test_all_named_tables_have_typed_physical_schemas_even_when_empty(source_and_run, tmp_path):
    source, run = source_and_run
    rows = canonical_tables(source, run)
    receipt = write_contracts(tmp_path, rows)
    assert set(receipt["tables"]) == set(SCHEMAS) and len(SCHEMAS) == 10
    for name, schema in SCHEMAS.items():
        table = pq.read_table(tmp_path / f"{name}.parquet")
        assert table.schema == schema
        assert table.num_rows == len(rows[name])
        assert (
            receipt["tables"][name]["sha256"]
            == hashlib.sha256((tmp_path / f"{name}.parquet").read_bytes()).hexdigest()
        )
    assert pq.read_table(tmp_path / "thesis.parquet").num_rows == 0
    assert SCHEMAS["daily_bar"].field("volume").type == pa.int64()
    assert SCHEMAS["universe_membership"].field("eligible").type == pa.bool_()
    assert len(rows["daily_bar"]) == len(source.bars)
    assert all(row["cik"] is None and row["exchange"] is None for row in rows["instrument"])
    assert all(row["vendor_recorded_at"] is None for row in rows["daily_bar"])
    assert all(row["ingestion_at"] is None for row in rows["fundamental_fact"])
    assert rows["source_manifest"][0]["retrieval_at"] is None
    assert all(row["marketcap_asof"] is None for row in rows["universe_membership"])
    benchmark = next(
        row for row in rows["universe_membership"] if row["security_id"] == "fx-market"
    )
    assert benchmark["eligible"] is False and benchmark["rejection_reason"]


def test_execution_export_preserves_costs_without_inventing_exit_price_or_time(source_and_run):
    source, run = source_and_run
    rows = canonical_tables(source, run)["backtest_execution"]
    assert len(rows) == 3
    entry, exit_row, rejection = rows
    assert entry["assumed_fill"] == 10 and entry["costs"] == 1
    assert entry["timestamp"] is None
    assert exit_row["assumed_fill"] is None and exit_row["costs"] == 2
    assert exit_row["terminal_wealth"] == 100 and exit_row["timestamp"] is None
    assert rejection["rejected_reason"] == "PRICE_OR_LIQUIDITY_FLOOR"
    assert rejection["assumed_fill"] is None and rejection["costs"] is None
    assert rejection["timestamp"] == "2021-01-01T23:00:00+00:00"


def test_filing_events_are_attributed_source_records_without_classification(source_and_run):
    source, run = source_and_run
    rows = canonical_tables(source, run)["event_evidence"]
    assert len(rows) == len({(f.security_id, f.accession) for f in source.facts})
    for row in rows:
        assert row["classification_confidence"] is None
        assert row["raw_digest"] == run["sources"][0]["sha256"]
        assert row["raw_digest_scope"] == "COMPLETE_SYNTHETIC_DATASET_NOT_ORIGINAL_FILING"
        assert datetime.fromisoformat(row["event_at"]) <= datetime.fromisoformat(
            row["first_public_at"]
        )


@pytest.mark.parametrize("mutation", ["hash", "mode", "identity", "run_id", "clock", "nan"])
def test_export_rejects_wrong_source_unknown_security_and_invalid_run(source_and_run, mutation):
    source, run = source_and_run
    if mutation == "hash":
        run["sources"][0]["sha256"] = "0" * 64
    elif mutation == "mode":
        run["mode"] = "EXTERNAL_UNVERIFIED"
    elif mutation == "identity":
        run["portfolio"]["executions"][0]["security_id"] = "unknown"
    elif mutation == "run_id":
        run["run_id"] = "../elsewhere"
    elif mutation == "clock":
        run["asof"] = "2022-01-03T23:00:00"
    else:
        run["portfolio"]["executions"][0]["entry_cost"] = float("nan")
    with pytest.raises(ValueError):
        canonical_tables(source, run)


@pytest.mark.parametrize("mutation", ["missing_table", "missing_field", "null_id", "nan"])
def test_invalid_table_contract_writes_nothing(source_and_run, tmp_path, mutation):
    rows = canonical_tables(*source_and_run)
    if mutation == "missing_table":
        rows.pop("thesis")
    elif mutation == "missing_field":
        rows["instrument"][0].pop("cik")
    elif mutation == "null_id":
        rows["instrument"][0]["permanent_security_id"] = None
    else:
        rows["backtest_execution"][0]["costs"] = float("inf")
    with pytest.raises(ValueError):
        write_contracts(tmp_path / "output", rows)
    assert not (tmp_path / "output").exists()


def test_optional_metadata_is_preserved_without_conflating_availability(source_and_run):
    source, run = source_and_run
    bar = source.bars[0].model_dump()
    bar["vendor_recorded_at"] = datetime(2026, 1, 1, tzinfo=UTC)
    assert Bar.model_validate(bar).vendor_recorded_at == bar["vendor_recorded_at"]
    assert Bar.model_validate(bar).available_at == source.bars[0].available_at
    fact = source.facts[0].model_dump()
    fact["ingestion_at"] = datetime(2026, 1, 2, tzinfo=UTC)
    assert Fact.model_validate(fact).ingestion_at == fact["ingestion_at"]
    for model, value, field in ((Bar, bar, "vendor_recorded_at"), (Fact, fact, "ingestion_at")):
        invalid = copy.deepcopy(value)
        invalid[field] = datetime(2026, 1, 1)
        with pytest.raises(ValidationError):
            model.model_validate(invalid)
    instrument = HistoricalInstrument(
        security_id="unverified-class",
        name="Test",
        first_seen="2020-01-01",
        security_type="common",
        exchange="XNAS",
        delisted=False,
        cik="0000000001",
        identifiers_version="source-reference-v2",
    )
    assert (
        instrument.cik == "0000000001" and instrument.identifiers_version == "source-reference-v2"
    )
    symbol = HistoricalSymbol(
        security_id="unverified-class",
        ticker="TEST",
        valid_from="2020-01-01",
        published_at="2020-01-01T00:00:00Z",
        source="fixture://symbol-source",
    )
    assert symbol.source == "fixture://symbol-source"


def test_read_only_download_checks_saved_manifest_and_never_rebuilds_legacy(tmp_path, monkeypatch):
    root = tmp_path / "fixture" / "latest"
    run_id = "b" * 16
    folder = root / "runs" / run_id
    (folder / "contracts").mkdir(parents=True)
    path = folder / "contracts/instrument.parquet"
    pq.write_table(pa.Table.from_pylist([], schema=SCHEMAS["instrument"]), path)
    run = {"mode": "FIXTURE", "run_id": run_id, "data_contracts": {"tables": {"instrument": {}}}}
    (folder / "run.json").write_text(json.dumps(run), encoding="utf-8")
    write_integrity(folder)
    monkeypatch.setenv("BAGHUNTER_DATA", str(root))
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/tables/instrument.parquet")
    assert response.status_code == 200 and response.content == path.read_bytes()
    assert response.headers["content-type"] == "application/vnd.apache.parquet"
    assert client.get(f"/runs/{run_id}/tables/not_a_table.parquet").status_code == 404
    assert client.get(f"/runs/{run_id}/tables/thesis.parquet").status_code == 404
    path.write_bytes(b"corrupt")
    assert client.get(f"/runs/{run_id}/tables/instrument.parquet").status_code == 503
    assert path.read_bytes() == b"corrupt"
    del run["data_contracts"]
    (folder / "run.json").write_text(json.dumps(run), encoding="utf-8")
    write_integrity(folder)
    assert client.get(f"/runs/{run_id}/tables/instrument.parquet").status_code == 404
