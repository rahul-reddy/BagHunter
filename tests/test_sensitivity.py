"""Independent rank arithmetic, missingness, liquidity exclusion and report round-trip."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.pipeline import run
from packages.research.discovery import DiscoveryPolicy
from packages.research.sensitivity import ranking_sensitivity


def signals():
    weights = DiscoveryPolicy().weights
    return [
        {
            "security_id": sid,
            "eligible": True,
            "close": 10,
            "dollar_volume_20d": volume,
            "components": {
                k: price
                if k == "price_volume"
                else growth
                if k == "fundamental_inflection"
                else None
                for k in weights
            },
        }
        for sid, price, growth, volume in [
            ("a", 100, 0, 1_500_000),
            ("b", 0, 100, 3_000_000),
            ("c", 100, None, 50_000),
        ]
    ]


def test_weight_arithmetic_missingness_and_stricter_liquidity():
    policy = DiscoveryPolicy()
    data = signals()
    result = ranking_sensitivity(data, policy)
    variants = {v["name"]: v for v in result["variants"]}
    baseline = variants["frozen_policy"]["ranked"]
    assert [r["security_id"] for r in baseline] == ["b", "a"]
    assert [r["score"] for r in baseline] == [25, 20]
    assert [r["factor_coverage"] for r in baseline] == [0.45, 0.45]
    price = variants["price_volume_only"]["ranked"]
    assert price[0]["security_id"] == "a" and price[0]["score"] == 100
    assert price[0]["rank_change"] == 1 and price[1]["rank_change"] == -1
    assert [r["security_id"] for r in variants["liquidity_floor_2x"]["ranked"]] == ["b"]
    assert variants["liquidity_floor_10x"]["ranked"] == []
    assert result == ranking_sensitivity(data, policy)
    # An unavailable family stays zero with zero covered weight, not a synthesized observation.
    missing = [{**data[0], "components": dict.fromkeys(policy.weights)}]
    row = ranking_sensitivity(missing, policy)["variants"][0]["ranked"][0]
    assert row["score"] == 0 and row["factor_coverage"] == 0


def test_invalid_and_duplicate_factor_inputs_reject():
    data = signals()
    with pytest.raises(ValueError, match="Duplicate"):
        ranking_sensitivity(data + [data[0]], DiscoveryPolicy())
    data[0]["components"]["price_volume"] = float("nan")
    with pytest.raises(ValueError, match="component"):
        ranking_sensitivity(data, DiscoveryPolicy())
    with pytest.raises(ValueError, match="threshold"):
        ranking_sensitivity([], DiscoveryPolicy(min_dollar_volume=1e308))


def test_sensitivity_reports_bind_run_and_policy_is_reusable(tmp_path, monkeypatch):
    output = tmp_path / "fixture"
    report = run(output, datetime.fromisoformat("2022-01-03T23:00:00+00:00"))
    monkeypatch.setenv("BAGHUNTER_DATA", str(output))
    base = f"/runs/{report['run_id']}/reports/"
    client = TestClient(app)
    policy = client.get(base + "discovery_policy.json")
    assert policy.status_code == 200
    assert DiscoveryPolicy.model_validate(policy.json()) == DiscoveryPolicy()
    response = client.get(base + "discovery_sensitivity.json")
    assert response.status_code == 200
    archived = json.loads(
        (output / "runs" / report["run_id"] / "reports" / "discovery_sensitivity.json").read_text(
            encoding="utf-8"
        )
    )
    assert response.json() == archived
    assert len(response.json()["variants"]) == 6
