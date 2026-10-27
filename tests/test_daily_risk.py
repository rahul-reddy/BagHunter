"""Intraholding losses, missing marks, cash, distributions and daily-risk assumptions."""

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.backtest.constrained import PortfolioPolicy, simulate
from packages.backtest.risk import daily_risk
from packages.data.fixture import fixture


def test_drawdown_observes_losses_hidden_between_profitable_endpoints():
    curve = [
        {"date": f"2020-01-0{n + 1}", "equity": value}
        for n, value in enumerate([100, 120, 60, 130])
    ]
    result = daily_risk(curve)
    assert result["max_drawdown"] == -0.5
    assert result["total_return"] == pytest.approx(0.3)
    assert result["maximum_underwater_sessions"] == 1
    assert result["worst_daily_return"] == -0.5
    assert result["annualized_volatility"] > 0
    assert result["sharpe_zero_risk_free"] is not None
    assert "FIXTURE" in result["status"]


@pytest.mark.parametrize(
    "curve",
    [
        [{"date": "2020-01-01", "equity": -1}],
        [{"date": "2020-01-01", "equity": float("inf")}],
        [{"date": "2020-01-01", "equity": 0}],
        [{"date": "2020-01-02", "equity": 100}, {"date": "2020-01-01", "equity": 100}],
        [{"date": "2020-01-01", "equity": 100}, {"date": "2020-01-01", "equity": 100}],
    ],
)
def test_invalid_or_ambiguous_marks_reject(curve):
    with pytest.raises(ValueError):
        daily_risk(curve)


def test_flat_cash_and_exhausted_equity_do_not_invent_risk_ratios():
    cash = daily_risk(
        [
            {"date": "2020-01-01", "equity": 100},
            {"date": "2020-01-02", "equity": 100},
            {"date": "2020-01-03", "equity": 100},
        ]
    )
    assert cash["max_drawdown"] == 0 and cash["annualized_volatility"] == 0
    assert cash["sharpe_zero_risk_free"] is None and cash["sortino_zero_target"] is None
    zero = daily_risk(
        [
            {"date": "2020-01-01", "equity": 100},
            {"date": "2020-01-02", "equity": 0},
            {"date": "2020-01-03", "equity": 0},
        ]
    )
    assert zero["max_drawdown"] == -1 and zero["total_return"] == -1
    assert zero["ratio_status"] == "UNDEFINED_AFTER_EQUITY_EXHAUSTION"
    assert zero["annualized_volatility"] is None


def test_simulation_marks_intraholding_dip_and_reconciles_cash():
    data = fixture()
    policy = PortfolioPolicy()
    base = simulate(data, policy)
    trade = base["executions"][0]
    day = date.fromisoformat(trade["entry"]) + timedelta(days=5)
    # The fixture calendar is weekdays; choose the first known bar at/after the requested dip.
    dip = next(b for b in data.bars if b.security_id == trade["security_id"] and b.session >= day)
    bars = [
        b.model_copy(
            update={
                "close": b.close * 0.2,
                "open": b.open * 0.2,
                "high": b.high * 0.2,
                "low": b.low * 0.2,
            }
        )
        if b is dip
        else b
        for b in data.bars
    ]
    report = simulate(data.model_copy(update={"bars": bars}), policy)
    assert report["daily_risk"]["max_drawdown"] < -0.15
    assert report["daily_risk"]["max_drawdown"] <= report["metrics"]["max_drawdown"]
    assert report["daily_curve"][-1]["equity"] == pytest.approx(report["ending_equity"])
    assert report["rows"][0]["ending_equity"] == pytest.approx(base["rows"][0]["ending_equity"])
    assert any(r["basis"] == "CASH_GAP" for r in report["daily_curve"])
    incomplete = data.model_copy(update={"bars": [b for b in data.bars if b is not dip]})
    with pytest.raises(ValueError, match="Missing daily portfolio mark"):
        simulate(incomplete, policy)


def test_empty_legacy_cohort_export_preserves_header(tmp_path, monkeypatch):
    folder = tmp_path / "runs" / ("1" * 16)
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(
        json.dumps(
            {
                "run_id": "1" * 16,
                "mode": "FIXTURE",
                "signals": [],
                "sources": [],
                "study": {"labels": []},
                "backtest": {},
            }
        )
    )
    monkeypatch.setenv("BAGHUNTER_DATA", str(tmp_path))
    response = TestClient(app).get(f"/runs/{'1' * 16}/reports/historical_cohorts.csv")
    assert response.status_code == 200
    assert response.text.startswith("security_id,anchor,horizon_years")
    assert len(response.text.splitlines()) == 1
    client = TestClient(app)
    assert client.get(f"/runs/{'1' * 16}/reports/event_paths.json").json() is None
    history = client.get(f"/runs/{'1' * 16}/reports/stage_history.json").json()
    assert history["asof"] is None and history["histories"] == {}
    assert history["history_scope"] == "LEGACY_ARCHIVED_WINDOW"
    assert (
        "unavailable in this archive" in client.get(f"/runs/{'1' * 16}/reports/event_paths.md").text
    )
