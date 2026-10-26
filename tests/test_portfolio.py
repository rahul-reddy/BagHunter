"""Execution constraints, cash conservation, missing exits and corporate actions."""

from collections import defaultdict

import pytest

from packages.backtest.constrained import PortfolioPolicy, simulate
from packages.data.fixture import fixture
from packages.shared.models import Action


def test_caps_capacity_costs_and_no_reinvestment_of_unrealized_proceeds():
    data = fixture()
    policy = PortfolioPolicy(
        max_position=0.25, max_sector=0.8, participation=0.01, min_price=0.01, min_dollar_volume=0
    )
    report = simulate(data, policy)
    decisions = defaultdict(list)
    for row in report["executions"]:
        decisions[row["decision"]].append(row)
        assert row["entry_notional"] <= row["capacity_limit"]
        assert (
            row["entry_notional"] + row["entry_cost"]
            <= row["starting_capital"] * policy.max_position + 1e-8
        )
        assert row["shares"] == int(row["shares"]) and row["shares"] > 0
        assert row["entry_cost"] == pytest.approx(row["entry_notional"] * 0.002)
    for rows in decisions.values():
        capital = rows[0]["starting_capital"]
        assert sum(r["entry_notional"] + r["entry_cost"] for r in rows) <= capital + 1e-8
        for sector in {r["sector"] for r in rows}:
            assert (
                sum(r["entry_notional"] + r["entry_cost"] for r in rows if r["sector"] == sector)
                <= capital * policy.max_sector + 1e-8
            )
    assert any(r["delisted"] for r in report["executions"])
    assert all(0 <= r["deployment_fraction"] <= 1 for r in report["rows"])


def test_empty_universe_stays_cash_and_missing_exit_rejects():
    data = fixture()
    all_cash = simulate(data, PortfolioPolicy(min_dollar_volume=1e15))
    assert all_cash["ending_equity"] == 100_000
    assert all_cash["executions"] == []
    report = simulate(data, PortfolioPolicy())
    row = report["executions"][0]
    missing = data.model_copy(
        update={
            "bars": [
                b
                for b in data.bars
                if not (b.security_id == row["security_id"] and str(b.session) == row["exit"])
            ]
        }
    )
    with pytest.raises(ValueError, match="Unresolved portfolio exit"):
        simulate(missing, PortfolioPolicy())


def test_independent_split_and_dividend_valuation_and_costs():
    data = fixture()
    base = simulate(data, PortfolioPolicy())
    trade = base["executions"][0]
    from datetime import date, timedelta

    effective = date.fromisoformat(trade["entry"]) + timedelta(days=2)
    events = [
        Action(
            security_id=trade["security_id"],
            effective_date=effective,
            kind=kind,
            value=value,
            source_id="independent-test",
        )
        for kind, value in [("split", 2), ("dividend", 1)]
    ]
    changed = data.model_copy(update={"actions": data.actions + events})
    revised = simulate(changed, PortfolioPolicy())
    first = revised["executions"][0]
    exit_close = next(
        b.close
        for b in data.bars
        if b.security_id == trade["security_id"] and str(b.session) == trade["exit"]
    )
    assert first["terminal_wealth"] == pytest.approx(trade["shares"] * (2 * exit_close + 2))
    assert first["exit_cost"] == pytest.approx(trade["shares"] * 2 * exit_close * 0.002)


@pytest.mark.parametrize("selector", ["momentum_12_1", "revenue_growth", "seeded_random"])
def test_independent_baselines_are_reproducible_and_use_the_same_caps(selector):
    data = fixture()
    policy = PortfolioPolicy(selector=selector)
    report = simulate(data, policy)
    assert report == simulate(data, policy)
    assert report["policy"]["max_position"] == 0.25
    assert all(
        row["entry_notional"] <= row["starting_capital"] * 0.25 for row in report["executions"]
    )
    if selector == "revenue_growth":
        assert any(row["reason"] == "MISSING_DATED_REVENUE_GROWTH" for row in report["exclusions"])
