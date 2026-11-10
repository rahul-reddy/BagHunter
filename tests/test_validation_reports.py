"""Saved report content, missingness, provenance and immutable download boundaries."""

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.data.run_archive import write_integrity
from packages.research.validation_reports import (
    VERSION,
    failed_lookalikes_report,
    model_validation_report,
)


@pytest.fixture
def archived():
    return {
        "mode": "FIXTURE",
        "run_id": "a" * 16,
        "asof": "2022-01-03T23:00:00Z",
        "model_version": "fixture-test-model",
        "code_sha256": "c" * 64,
        "seed": 7,
        "sources": [
            {
                "source_id": "fixture-test",
                "sha256": "b" * 64,
                "url": "fixture://fixture-test",
                "coverage": "Synthetic unit cases only",
            }
        ],
        "backtest": {
            "period_start": "2020-01-01",
            "period_end": "2022-01-05",
            "rows": [{"decision": "2020-01-01"}],
            "execution": "NEXT_OPEN_FIXTURE",
            "cost_round_trip_bps": 60,
            "split": "FROZEN_UNIT_TEST",
        },
        "validation": {
            "holdout_status": "NOT_UNTOUCHED_TEST",
            "partitions": {
                "train": ["2020-01-01"],
                "validation": [],
                "holdout": [],
                "purged": [],
                "embargo_days": 5,
            },
            "metrics": {
                "selector": {
                    "windows": 1,
                    "total_return": 0,
                    "max_drawdown": -0.5,
                    "win_rate": 0,
                    "payoff_ratio": None,
                    "cagr": None,
                }
            },
            "robustness": {
                "attempts": [
                    {
                        "id": "missing_adjusted_prices",
                        "status": "UNAVAILABLE",
                        "reason": "No series",
                    }
                ]
            },
            "negative_controls": {"status": "FIXTURE_ONLY", "windows": 1},
        },
        "portfolio": {
            "policy": {"one_way_cost_bps": 35},
            "executions": [],
            "exclusions": [{"reason": "NOT_TRADABLE"}],
            "daily_risk": {
                "observations": 10,
                "sharpe_zero_risk_free": None,
                "drawdown_recovery_status": "UNRECOVERED",
            },
        },
        "study": {
            "anchor": "2020-01-01T23:00:00Z",
            "denominator": 3,
            "pairs": [
                {
                    "case_security_id": "fx-winner",
                    "control_security_id": "fx-roundtrip",
                    "strata": ("fixture-sector", "fixture-small"),
                    "matching_seed": 7,
                    "control_weight": 1,
                    "control_sampling_probability": 1,
                }
            ],
            "cohorts": {
                "labels": [
                    {
                        "security_id": "fx-roundtrip",
                        "anchor": "2020-01-01",
                        "horizon_years": 1,
                        "max_multiple": 10,
                        "terminal_total_return": -0.8,
                        "max_drawdown": -0.99,
                        "delisted": True,
                        "coverage_flag": "COMPLETE_FIXTURE",
                    },
                    {
                        "security_id": "fx-zero",
                        "anchor": "2020-01-01",
                        "horizon_years": 1,
                        "max_multiple": 1,
                        "terminal_total_return": 0,
                        "max_drawdown": 0,
                        "delisted": False,
                        "coverage_flag": "COMPLETE_FIXTURE",
                    },
                    {
                        "security_id": "fx-missing",
                        "anchor": "2020-01-01",
                        "horizon_years": 1,
                        "max_multiple": None,
                        "terminal_total_return": None,
                        "max_drawdown": None,
                        "delisted": None,
                        "coverage_flag": "INCOMPLETE_HORIZON",
                    },
                ]
            },
        },
        "limitations": ["Synthetic report test, not empirical evidence"],
    }


def test_validation_report_uses_actual_periods_policy_costs_counts_and_missing_ratios(archived):
    report = model_validation_report(archived)
    for expected in [
        VERSION,
        "2020-01-01",
        "2022-01-05",
        "1 saved windows",
        "60 bps",
        '"one_way_cost_bps": 35',
        "NOT_UNTOUCHED_TEST",
        "UNRECOVERED",
        "missing_adjusted_prices",
        "UNAVAILABLE",
        "No series",
        "not p-values",
        "code SHA-256 " + "c" * 64,
        "fixture://fixture-test",
    ]:
        assert expected in report
    assert "| selector | 1 | 0 | Unavailable | -0.5 | 0 | Unavailable |" in report
    assert "Unavailable in this archive; no classification is recomputed" in report
    assert "Retrospective evaluation/outcome dates can extend beyond" in report
    assert "Zero verified real investment theses" in report


def test_atlas_includes_roundtrip_winner_and_zero_but_does_not_turn_missing_into_failure(archived):
    report = failed_lookalikes_report(archived)
    assert "3 archived security/anchor/horizon observations" in report
    assert "1 missing terminal outcomes; 2 recorded nonpositive terminal outcomes" in report
    assert "| fx-roundtrip | 2020-01-01 | 1 | Unavailable | 10 | -0.8 | -0.99 | True |" in report
    assert "| fx-zero |" in report
    adverse, missing_section = report.split("## Missing terminal outcomes retained for audit")
    assert "| fx-missing |" not in adverse
    assert "| fx-missing | 2020-01-01 | 1 | INCOMPLETE_HORIZON |" in missing_section
    assert "No causal explanation" in report and "not independent firms" in report
    restored = json.loads(json.dumps(archived))
    assert failed_lookalikes_report(restored) == report
    assert model_validation_report(restored) == model_validation_report(archived)


def test_legacy_absence_stays_unavailable_and_known_empty_is_zero(archived):
    legacy = {
        key: value
        for key, value in archived.items()
        if key in ("mode", "run_id", "asof", "sources")
    }
    validation = model_validation_report(legacy)
    atlas = failed_lookalikes_report(legacy)
    assert "Unavailable saved windows" in validation
    assert "Saved executions: Unavailable; rejected selections: Unavailable" in validation
    assert "Unavailable archived security/anchor/horizon observations" in atlas
    assert "0 recorded nonpositive" not in atlas
    legacy["backtest"] = {"rows": []}
    assert "0 saved windows" in model_validation_report(legacy)


@pytest.mark.parametrize("builder", [model_validation_report, failed_lookalikes_report])
@pytest.mark.parametrize("mutation", ["nan", "naive_clock", "private_url", "hash", "mode"])
def test_invalid_archived_evidence_cannot_be_rendered(archived, builder, mutation):
    if mutation == "nan":
        archived["portfolio"]["policy"]["one_way_cost_bps"] = float("nan")
    elif mutation == "naive_clock":
        archived["asof"] = "2022-01-03T23:00:00"
    elif mutation == "private_url":
        archived["sources"][0]["url"] = "https://user:private@example.test/report"
    elif mutation == "hash":
        archived["sources"][0]["sha256"] = "invalid"
    else:
        archived["mode"] = "EXTERNAL_UNVERIFIED"
    with pytest.raises(ValueError):
        builder(archived)


def test_saved_download_preserves_legacy_text_and_rejects_corruption_without_regeneration(
    tmp_path, monkeypatch
):
    root = tmp_path / "fixture/latest"
    run_id = "a" * 16
    folder = root / "runs" / run_id
    (folder / "reports").mkdir(parents=True)
    data = {"run_id": run_id, "mode": "FIXTURE", "sources": [], "study": {}}
    (folder / "run.json").write_text(json.dumps(data), encoding="utf-8")
    path = folder / "reports/model_validation.md"
    path.write_text("# Legacy synthetic summary\nNo reconstructed metrics.\n", encoding="utf-8")
    write_integrity(folder)
    monkeypatch.setenv("BAGHUNTER_DATA", str(root))
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/reports/model_validation.md")
    assert response.status_code == 200 and response.content == path.read_bytes()
    assert VERSION not in response.text
    assert client.get(f"/runs/{run_id}/reports/failed_lookalikes.md").status_code == 404
    path.write_bytes(b"corrupt")
    assert client.get(f"/runs/{run_id}/reports/model_validation.md").status_code == 503
    assert path.read_bytes() == b"corrupt"
