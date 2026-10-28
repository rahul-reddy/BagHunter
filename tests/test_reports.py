"""Report content, source clocks and explicitly selected comparison intervals."""

import copy
import importlib

import pytest
from fastapi.testclient import TestClient

from packages.research.reports import candidate_memo, case_report, discovery_digest


def feature(sid="fixture-one", asof="2022-02-01T00:00:00Z"):
    return {
        "security_id": sid,
        "ticker": sid.upper(),
        "asof_time": asof,
        "stage": "IGNITION",
        "stage_reason": "Fictional configured trigger",
        "score": 50,
        "completeness": 0.5,
        "sector": "Fixture sector",
        "close": 10,
        "processing_lag_hours": 24,
        "evidence": [
            {
                "metric": "annual_revenue",
                "value": 42,
                "unit": "USD",
                "period_end": "2021-12-31",
                "accepted_at": "2022-01-10T12:00:00Z",
                "published_at": "2022-01-10T12:00:00Z",
                "accession": "fixture-new",
                "source_id": "fixture-source",
                "source_url": "fixture://filing",
            }
        ],
    }


def run_report():
    anchor = feature(asof="2021-01-01T00:00:00Z")
    anchor["evidence"][0].update(
        period_end="2019-12-31",
        accepted_at="2020-03-01T00:00:00Z",
        published_at="2020-03-01T00:00:00Z",
        accession="fixture-anchor",
    )
    return {
        "run_id": "a" * 16,
        "mode": "FIXTURE",
        "asof": "2022-02-01T00:00:00Z",
        "model_version": "fixture-model",
        "code_sha256": "c" * 64,
        "sources": [{"sha256": "b" * 64}],
        "signals": [feature()],
        "backtest": {},
        "limitations": ["Fictional acceptance input, not empirical evidence"],
        "discovery": {"policy_sha256": "d" * 64},
        "study": {
            "anchor": "2021-01-01T00:00:00Z",
            "denominator": 2,
            "anchor_features": [anchor],
            "pairs": [
                {
                    "case_security_id": "fixture-one",
                    "control_security_id": "fixture-two",
                    "matching_seed": 7,
                    "control_weight": 1,
                    "control_sampling_probability": 1,
                    "strata": ["Fixture sector"],
                }
            ],
            "labels": [
                {
                    "security_id": "fixture-one",
                    "horizon_years": 1,
                    "max_multiple": 10,
                    "terminal_total_return": 2,
                    "max_drawdown": -0.5,
                    "coverage_flag": "FIXTURE_ONLY",
                }
            ],
        },
    }


def test_dossier_cites_primary_reference_and_first_usable_clock_without_mutating_input():
    run = run_report()
    original = copy.deepcopy(run)
    text = candidate_memo(run, "fixture-one")
    assert "source-bound-reports-v2" in text
    assert "[fixture-source](fixture://filing)" in text
    assert "usable after 2022-01-11T12:00:00+00:00 (24h processing lag)" in text
    assert "accepted 2022-01-10" in text and "published 2022-01-10" in text
    assert "fixture-model" in text and "not a live quote" in text
    assert run == original


@pytest.mark.parametrize(
    "mutation",
    [
        {"published_at": "2022-02-01T00:00:00Z"},
        {"accepted_at": "2022-02-02T00:00:00Z"},
        {"published_at": "2022-01-01T00:00:00"},
        {"value": float("inf")},
        {"source_url": "https://user:private-value@example.invalid/filing"},
        {"source_url": "https://example.invalid/filing?token=private-value"},
        {"source_url": "javascript:alert(1)"},
    ],
)
def test_future_nonfinite_naive_or_private_fact_cannot_become_report_evidence(mutation):
    run = run_report()
    run["signals"][0]["evidence"][0].update(mutation)
    with pytest.raises(ValueError) as caught:
        candidate_memo(run, "fixture-one")
    assert "private-value" not in str(caught.value)


def test_legacy_clock_missing_is_unavailable_and_longer_lag_is_enforced():
    run = run_report()
    del run["signals"][0]["evidence"][0]["accepted_at"]
    assert "unavailable; legacy filing clocks missing" in candidate_memo(run, "fixture-one")
    run = run_report()
    run["signals"][0]["processing_lag_hours"] = 720
    with pytest.raises(ValueError, match="unavailable"):
        candidate_memo(run, "fixture-one")


def test_case_uses_independent_anchor_not_current_profile_and_separates_outcomes():
    run = run_report()
    run["signals"][0]["close"] = 999
    text = case_report(run)
    assert "close: 10" in text and "close: 999" not in text
    assert "fixture-anchor" in text and "fixture-new" not in text
    assert "Later hindsight outcomes — not anchor predictors" in text
    assert "maximum 10; terminal return 2" in text and "industry proxy" in text
    assert "no current profile substituted" in text
    run["study"]["anchor_features"][0]["asof_time"] = run["asof"]
    with pytest.raises(ValueError, match="anchor binding"):
        case_report(run)


def test_digest_requires_selected_interval_and_retains_membership_theme_filing_changes():
    run = run_report()
    assert "No prior run selected" in discovery_digest(run)
    old = copy.deepcopy(run)
    old.update(run_id="b" * 16, asof="2022-01-01T00:00:00Z", code_sha256="e" * 64)
    old["signals"][0].update(stage="WATCH", evidence=[])
    removed = feature("fixture-removed")
    removed["evidence"] = []
    old["signals"].append(removed)
    added = feature("fixture-added")
    added.update(stage="CONFIRMED", evidence=[])
    run["signals"].append(added)
    run["signals"][0]["evidence"].append(
        dict(run["signals"][0]["evidence"][0], metric="net_income")
    )
    text = discovery_digest(run, old)
    assert f"Changes since run {old['run_id']}" in text
    assert "WATCH → IGNITION" in text and "added to the research queue" in text
    assert "not assumed delisted or worthless" in text and "not isolated market moves" in text
    fresh = text.split("### Newly usable filing accessions")[1].split("### Sector-proxy")[0]
    assert fresh.count("fixture-new") == 1
    assert "emerging/confirmed count 0 → 1" in text
    assert "not an industry-wide breadth estimate" in text and "incomplete factor coverage" in text
    legacy = dict(old, code_sha256=None, discovery={})
    assert "comparability is unknown" in discovery_digest(run, legacy)
    for previous in [
        run,
        dict(old, mode="EXTERNAL_UNVERIFIED"),
        dict(old, asof="2023-01-01T00:00:00Z"),
    ]:
        with pytest.raises(ValueError, match="earlier run"):
            discovery_digest(run, previous)


def test_report_api_interval_binding_errors_and_corrupt_evidence_fail_closed(monkeypatch):
    module = importlib.import_module("apps.api.main")
    run = run_report()
    old = copy.deepcopy(run)
    old.update(run_id="b" * 16, asof="2022-01-01T00:00:00Z")
    old["signals"][0]["evidence"] = []
    monkeypatch.setattr(module, "read_run", lambda run_id: old if run_id == old["run_id"] else run)
    client = TestClient(module.app)
    prefix = f"/runs/{run['run_id']}/reports"
    response = client.get(f"{prefix}/discovery_digest.md", params={"previous": old["run_id"]})
    assert response.status_code == 200 and old["run_id"] in response.text
    assert (
        client.get(f"{prefix}/discovery_digest.md", params={"previous": run["run_id"]}).status_code
        == 422
    )
    assert client.get(f"{prefix}/discovery_digest.md?previous=../../.env").status_code == 422
    assert (
        client.get(f"{prefix}/historical_cases.md", params={"previous": old["run_id"]}).status_code
        == 422
    )
    fingerprint = old.pop("discovery")
    comparison = client.get(f"/runs/{run['run_id']}/compare/{old['run_id']}").json()
    assert comparison["policy_changed"] is None
    old["discovery"] = fingerprint
    old["asof"] = "2022-01-01T00:00:00"
    assert (
        client.get(f"{prefix}/discovery_digest.md", params={"previous": old["run_id"]}).status_code
        == 503
    )
    run["signals"][0]["evidence"][0]["published_at"] = run["asof"]
    bad = client.get(f"{prefix}/discovery_digest.md")
    assert bad.status_code == 503 and "42" not in bad.text
    assert client.get(f"/runs/{run['run_id']}/dossiers/fixture-one").status_code == 503
    assert client.get(f"/runs/{run['run_id']}/dossiers/unknown").status_code == 404
