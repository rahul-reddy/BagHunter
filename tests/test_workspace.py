"""Independent checks for discovery, scenario arithmetic, validation and read-only run tools."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.main import app
from packages.backtest.negative_controls import negative_controls
from packages.backtest.validation import diagnostics, partition_windows, performance
from packages.data.finviz import _json
from packages.data.fixture import fixture
from packages.data.run_archive import verify_integrity
from packages.pipeline import DEFAULT_ASOF, run
from packages.research.cohorts import cohort_grid
from packages.research.discovery import DiscoveryPolicy, classify, discover
from packages.research.fundamentals import statement_ratios
from packages.research.scenarios import Scenario, scenario
from packages.shared.models import Fact


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    root = tmp_path_factory.mktemp("workspace") / "fixture" / "latest"
    first = run(root, datetime.fromisoformat(DEFAULT_ASOF))
    second = run(
        root,
        datetime.fromisoformat(DEFAULT_ASOF) + timedelta(days=1),
        policy=DiscoveryPolicy(min_dollar_volume=2_000_000),
    )
    return root, first["run_id"], second["run_id"]


def setup_feature(**changes):
    return {
        "eligible": True,
        "close": 100,
        "dollar_volume_20d": 2_000_000,
        "ema_21": 99,
        "ema_8": 99.5,
        "return_21d": 0.05,
        "base_high_60d": 101,
        "relative_volume": 1,
        "base_width_60d": 0.2,
        "revenue_growth": 0.1,
        "relative_strength_63d": 0.02,
        "sector_breadth": 0.5,
    } | changes


@pytest.mark.parametrize(
    "changes,prior,streak,expected",
    [
        ({"revenue_growth": None}, "WATCH", 0, "WATCH"),
        ({"close": 102, "relative_volume": 1.5}, "WATCH", 0, "IGNITION"),
        ({}, "WATCH", 0, "EMERGING"),
        ({}, "EMERGING", 3, "CONFIRMED"),
        ({"close": 130}, "CONFIRMED", 4, "EXTENDED/AGING"),
        ({"close": 90, "return_21d": -0.05}, "IGNITION", 1, "INVALIDATED"),
        ({"dollar_volume_20d": 999_999}, "CONFIRMED", 5, "WATCH"),
        ({"relative_strength_63d": None}, "WATCH", 0, "WATCH"),
        ({"sector_breadth": None}, "EMERGING", 5, "EMERGING"),
        ({"base_width_60d": 0.41, "relative_volume": 2, "close": 102}, "WATCH", 0, "EMERGING"),
    ],
)
def test_all_stage_boundaries(changes, prior, streak, expected):
    assert classify(setup_feature(**changes), DiscoveryPolicy(), prior, streak)[0] == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"weights": {"price_volume": 1}},
        {"min_dollar_volume": -1},
        {"confirmation_sessions": 21},
        {"max_ema_stretch": 0},
        {"weights": DiscoveryPolicy().weights | {"price_volume": 0.21}},
        {"min_price": float("nan")},
    ],
)
def test_policy_rejects_invalid_thresholds_and_weights(changes):
    with pytest.raises(ValidationError):
        DiscoveryPolicy(**changes)


def test_discovery_future_invariance_and_real_history():
    dataset = fixture()
    cutoff = datetime.fromisoformat(DEFAULT_ASOF)
    policy = DiscoveryPolicy()
    expected = discover(dataset, cutoff, policy)
    changed = dataset.model_copy(
        update={
            "facts": [
                f.model_copy(update={"value": 9e12}) if f.published_at > cutoff else f
                for f in dataset.facts
            ],
            "bars": [
                b.model_copy(update={"close": 1e6, "high": 1e6}) if b.available_at > cutoff else b
                for b in dataset.bars
            ],
        }
    )
    assert discover(changed, cutoff, policy) == expected
    assert (
        expected["policy_sha256"]
        == hashlib.sha256(_json(policy.model_dump(mode="json"))).hexdigest()
    )
    assert sum(expected["stage_counts"].values()) == 3
    for signal in expected["signals"]:
        assert len(signal["stage_history"]) == 21
        assert signal["asof_time"] == cutoff.isoformat()
        assert all(datetime.fromisoformat(h["asof"]) <= cutoff for h in signal["stage_history"])
        assert signal["stage_history"][-1]["stage"] == signal["stage"]
        assert signal["score"] == pytest.approx(
            sum(signal["weights"][k] * v for k, v in signal["components"].items() if v is not None),
            abs=1e-4,
        )
        if signal["sector_peer_count"] == 1:
            assert signal["sector_breadth"] is None
    missing = dataset.model_copy(
        update={"instruments": [i for i in dataset.instruments if i.security_type != "benchmark"]}
    )
    assert discover(missing, cutoff, policy)["regime"] == "UNAVAILABLE"


def test_scenario_independent_math_and_dilution():
    inputs = Scenario(
        revenue=100,
        shares=10,
        net_debt=20,
        growth=0.1,
        margin=0.2,
        multiple=10,
        reference_price=10,
        years=2,
        dilution=0.1,
    )
    result = scenario(inputs)
    # 121 revenue * 20% margin * 10 - 20 debt = 222 equity / 12.1 shares.
    assert result["per_share_value"] == pytest.approx(222 / 12.1)
    assert result["annualized_change"] == pytest.approx((222 / 12.1 / 10) ** 0.5 - 1)
    assert scenario(inputs.model_copy(update={"net_debt": 1000}))["per_share_value"] == 0
    assert "ASSUMPTIONS" in result["status"]
    with pytest.raises(ValidationError):
        Scenario(**(inputs.model_dump() | {"shares": 0}))


def test_statement_ratios_use_comparable_periods_and_available_revisions():
    facts = []
    for year, revenue in [(2018, 100), (2019, 120), (2020, 180)]:
        facts.append(
            Fact(
                security_id="demo",
                period_end=f"{year}-12-31",
                accepted_at=f"{year + 1}-02-01T12:00:00Z",
                published_at=f"{year + 1}-02-01T12:00:00Z",
                metric="annual_revenue",
                value=revenue,
                unit="USD",
                accession=f"original-{year}",
                source_id="fixture",
                source_url="fixture://source",
            )
        )
    operating = facts[-1].model_copy(update={"metric": "annual_operating_income", "value": 36})
    future = facts[-1].model_copy(
        update={
            "value": 9999,
            "published_at": datetime(2022, 1, 1, tzinfo=UTC),
            "accepted_at": datetime(2022, 1, 1, tzinfo=UTC),
            "amended": True,
        }
    )
    cutoff = datetime(2021, 2, 3, tzinfo=UTC)
    result = statement_ratios(facts + [operating, future], "demo", cutoff)
    assert result["revenue_growth"] == pytest.approx(0.5)
    assert result["revenue_growth_acceleration"] == pytest.approx(0.3)
    assert result["operating_margin"] == 0.2
    assert result["cashflow_margin"] is None
    wrong_units = statement_ratios(
        facts + [operating.model_copy(update={"unit": "EUR"})], "demo", cutoff
    )
    assert wrong_units["operating_margin"] is None
    assert statement_ratios([], "demo", cutoff)["revenue"] is None


def test_refresh_cache_revalidates_all_outputs_and_does_not_repair_corruption(workspace):
    root, before, _ = workspace
    # Same input/code/policy reuses the exact original run, including its manifest checksums.
    cached = run(root, datetime.fromisoformat(DEFAULT_ASOF))
    assert cached["run_id"] == before and cached["cache_reused"] is True
    report_path = root / "runs" / before / "reports" / "validation.json"
    original = report_path.read_bytes()
    report_path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        run(root, datetime.fromisoformat(DEFAULT_ASOF))
    assert report_path.read_bytes() == b"corrupted"
    report_path.write_bytes(original)


def test_cohort_grid_retains_missing_and_delisted_denominators():
    study = cohort_grid(fixture())
    first = next(
        r
        for r in study["grid"]
        if r["anchor"] == "2020-01-01"
        and r["horizon_years"] == 1
        and r["threshold"] == 5
        and r["sector"] == "ALL"
    )
    assert first["eligible"] == first["complete"] == 3 and first["cases"] == 1
    assert first["observed_fraction"] == pytest.approx(1 / 3)
    missing = next(
        r
        for r in study["grid"]
        if r["anchor"] == "2020-01-01"
        and r["horizon_years"] == 5
        and r["threshold"] == 100
        and r["sector"] == "ALL"
    )
    # The failed instrument's explicit terminal delist resolves its outcome; survivors lack 5Y.
    assert missing["eligible"] == 3 and missing["complete"] == 1 and missing["missing"] == 2
    assert missing["delisted"] == 1


def test_archive_manifest_cannot_read_outside_run(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "run.json").write_bytes(b"{}")
    (folder / "integrity.json").write_text(
        json.dumps(
            {
                "version": 1,
                "files": {"run.json": hashlib.sha256(b"{}").hexdigest(), "../private": "0" * 64},
            }
        )
    )
    # Validate every path, even when a caller requests only run.json.
    with pytest.raises(ValueError):
        verify_integrity(folder, only="run.json")


def windows():
    start = datetime(2020, 1, 1)
    return [
        {
            "decision": (start + timedelta(days=30 * i)).date().isoformat(),
            "entry": (start + timedelta(days=30 * i + 1)).date().isoformat(),
            "exit": (start + timedelta(days=30 * i + 29)).date().isoformat(),
            "net_return": 0.1 if i % 2 else -0.1,
        }
        for i in range(10)
    ]


def test_purge_embargo_and_performance_are_not_holdout_claims():
    rows = windows()
    split = partition_windows(rows, embargo_days=7)
    assert rows[5]["decision"] in split["purged"]
    assert rows[7]["decision"] in split["purged"]
    assert split["holdout"] == [rows[8]["decision"], rows[9]["decision"]]
    assert "NOT_UNTOUCHED" in split["status"]
    assert partition_windows(rows[:3])["status"] == "INSUFFICIENT_WINDOWS"
    with pytest.raises(ValueError):
        partition_windows(rows + [rows[0]])
    with pytest.raises(ValueError):
        performance([rows[0] | {"net_return": None}], "net_return")
    two = performance([rows[0] | {"net_return": 0.1}, rows[1] | {"net_return": -0.2}], "net_return")
    assert two["total_return"] == pytest.approx(-0.12)
    assert two["max_drawdown"] == pytest.approx(-0.2)
    assert two["win_rate"] == 0.5 and two["payoff_ratio"] == 0.5


def test_run_index_comparison_exports_and_scenarios(workspace, monkeypatch):
    root, before, after = workspace
    active = (root / "CURRENT").read_text()
    monkeypatch.setenv("BAGHUNTER_DATA", str(root))
    client = TestClient(app)
    listing = client.get("/runs").json()
    assert len(listing) == 2 and listing[0]["run_id"] == after
    assert client.get(f"/runs/{before}").json()["run_id"] == before
    comparison = client.get(f"/runs/{after}/compare/{before}").json()
    assert comparison["policy_changed"] and len(comparison["changes"]) == 3
    assert client.get(f"/runs/{before}/compare/{after}").status_code == 422
    data = client.get(f"/runs/{after}").json()
    validation = diagnostics(data["backtest"])
    controls = negative_controls(
        data["backtest"]["rows"], datetime.fromisoformat(data["asof"]), data["seed"]
    )
    discovery_controls = negative_controls(
        [
            row
            | {
                "candidates": row["discovery_candidates"],
                "eligible_count": len(row["discovery_candidates"]),
            }
            for row in data["backtest"]["rows"]
        ],
        datetime.fromisoformat(data["asof"]),
        data["seed"],
        selector_model=data["model_version"],
        selector_config_sha256=data["discovery"]["policy_sha256"],
    )
    assert (
        validation
        | {"negative_controls": controls, "discovery_negative_controls": discovery_controls}
        == data["validation"]
    )
    assert discovery_controls["selector_config_sha256"] == data["discovery"]["policy_sha256"]
    assert discovery_controls["input_sha256"] != controls["input_sha256"]
    assert controls["windows"] == 12 and controls["candidate_observations"] == 30
    assert controls["excluded_windows"]["unmatured"] == ["2021-12-06"]
    saved_controls = root / "runs" / after / "reports" / "negative_controls.json"
    assert json.loads(saved_controls.read_text()) == controls
    assert not {"negative_controls", "candidates", "net_return", "label_available_at"} & set(
        pq.read_schema(root / "runs" / after / "gold" / "features.parquet").names
    )
    returns = [r["total_return"] for r in validation["cost_sensitivity"]]
    assert returns == sorted(returns, reverse=True)
    for name in [
        "baghunter_watchlist.csv",
        "historical_cohorts.csv",
        "source_manifest.json",
        "validation.json",
        "negative_controls.json",
        "discovery_negative_controls.json",
        "research_limitations.md",
        "historical_cases.md",
        "discovery_digest.md",
        "portfolio.json",
        "cohort_grid.json",
    ]:
        response = client.get(f"/runs/{before}/reports/{name}")
        assert response.status_code == 200
        assert "FIXTURE" in response.text or "fx-compound" in response.text
    assert client.get(f"/runs/{before}/reports/secrets.env").status_code == 404
    dossier = client.get(f"/runs/{before}/dossiers/fx-compound")
    assert dossier.status_code == 200 and "FIXTURE RESEARCH DOSSIER" in dossier.text
    assert client.get(f"/runs/{before}/dossiers/unknown").status_code == 404
    assert client.get("/runs/invalid").status_code == 404
    assert (
        client.get(
            "/scenario",
            params={
                "revenue": 100,
                "shares": 10,
                "growth": 0.1,
                "margin": 0.2,
                "multiple": 10,
                "reference_price": 10,
            },
        ).status_code
        == 200
    )
    assert client.get("/scenario", params={"revenue": -1}).status_code == 422
    assert client.post("/scenario", json={}).status_code == 405
    # Read-only browsing must not change the active pointer.
    assert (root / "CURRENT").read_text() == active
    archive = root / "runs" / before / "run.json"
    original = archive.read_bytes()
    archive.write_text(json.dumps({"run_id": "0" * 16, "mode": "FIXTURE"}))
    assert client.get(f"/runs/{before}").status_code == 503
    archive.write_bytes(original)
