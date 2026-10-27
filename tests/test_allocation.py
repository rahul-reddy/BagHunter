"""Independent target arithmetic, dated risk and execution constraints."""

from datetime import timedelta
from statistics import pstdev

import pytest
from pydantic import ValidationError

from packages.backtest.allocation import MODES, allocation_targets, dated_volatility
from packages.backtest.constrained import PortfolioPolicy, comparator_runs, simulate
from packages.data.fixture import fixture


def candidate(sid, sector, volatility):
    return {
        "security_id": sid,
        "sector": sector,
        "allocation_volatility": {"value": volatility},
        "asof_time": "2020-01-01T23:00:00+00:00",
        "latest_included_publication": "2020-01-01T22:00:00+00:00",
        "source_ids": ["fixture"],
        "selection_score": 1,
    }


def weights(plan, field="requested_weight"):
    return {r["security_id"]: r[field] for r in plan["targets"]}


def test_exact_equal_risk_sector_targets_and_proportional_caps():
    pool = [candidate("a", "x", 0.1), candidate("b", "x", 0.2), candidate("c", "y", 0.2)]
    assert weights(allocation_targets(pool, "equal_weight", 1, 1)) == pytest.approx(
        {"a": 1 / 3, "b": 1 / 3, "c": 1 / 3}
    )
    assert weights(allocation_targets(pool, "inverse_volatility", 1, 1)) == {
        "a": 0.5,
        "b": 0.25,
        "c": 0.25,
    }
    assert weights(allocation_targets(pool, "sector_neutral", 1, 1)) == {
        "a": 0.25,
        "b": 0.25,
        "c": 0.5,
    }
    capped = allocation_targets(pool, "inverse_volatility", 0.4, 0.3)
    assert weights(capped, "planned_weight") == pytest.approx(
        {"a": 0.4 * 0.3 / 0.65, "b": 0.25 * 0.3 / 0.65, "c": 0.25}
    )
    assert capped["planned_weight_total"] == pytest.approx(0.55)
    assert weights(
        allocation_targets(list(reversed(pool)), "inverse_volatility", 0.4, 0.3), "planned_weight"
    ) == weights(capped, "planned_weight")
    assert all("requested_weight" not in f for f in pool)


def test_missing_zero_risk_sector_and_numeric_boundaries():
    pool = [candidate("a", "x", 0), candidate("b", "x", None), candidate("c", "", 0.2)]
    risk = allocation_targets(pool, "inverse_volatility", 1, 1)
    assert weights(risk) == {"c": 1}
    assert {r["security_id"] for r in risk["exclusions"]} == {"a", "b"}
    assert weights(allocation_targets(pool, "sector_neutral", 1, 1)) == {"a": 0.5, "b": 0.5}
    for invalid in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            allocation_targets([candidate("a", "x", invalid)], "inverse_volatility", 1, 1)
    with pytest.raises(ValueError, match="underflow"):
        allocation_targets(
            [candidate("a", "x", 1e-300), candidate("b", "x", 1e300)], "inverse_volatility", 1, 1
        )
    with pytest.raises(ValueError, match="Duplicate"):
        allocation_targets([pool[0], pool[0]], "equal_weight", 1, 1)
    with pytest.raises(ValueError, match="Unsupported"):
        allocation_targets([], "unknown", 1, 1)


def test_dated_volatility_exact_arithmetic_and_future_invariance():
    data = fixture()
    known = [b for b in data.bars if b.security_id == "fx-compound"][:301]
    clock = known[-1].available_at
    sample = known[-61:]
    returns = [b.close / a.close - 1 for a, b in zip(sample[:-1], sample[1:], strict=True)]
    risk = dated_volatility(data.bars, "fx-compound", clock, 60)
    assert risk["value"] == pytest.approx(pstdev(returns) * 252**0.5)
    assert risk["observations"] == 61
    assert risk["latest_available_at"] <= clock.isoformat()
    later = sample[-1].model_copy(
        update={"available_at": clock + timedelta(seconds=1), "close": 1e12}
    )
    assert dated_volatility(data.bars + [later], "fx-compound", clock, 60) == risk
    assert dated_volatility(sample[:60], "fx-compound", clock, 60)["value"] is None
    with pytest.raises(ValueError, match="Duplicate"):
        dated_volatility(data.bars + [sample[-1]], "fx-compound", clock, 60)
    with pytest.raises(ValueError):
        dated_volatility(data.bars, "fx-compound", clock.replace(tzinfo=None), 60)


@pytest.mark.parametrize("mode", MODES)
def test_shared_whole_share_cash_cost_capacity_and_sector_constraints(mode):
    policy = PortfolioPolicy(
        allocation=mode, max_position=0.4, max_sector=0.45, min_price=0.01, min_dollar_volume=0
    )
    report = simulate(fixture(), policy)
    for t in report["executions"]:
        assert t["shares"] > 0 and int(t["shares"]) == t["shares"]
        assert t["entry_notional"] <= t["capacity_limit"]
        assert (
            t["entry_notional"] + t["entry_cost"]
            <= t["planned_weight"] * t["starting_capital"] + 1e-8
        )
        assert t["planned_weight"] <= 0.4
        assert t["entry_cost"] == pytest.approx(t["entry_notional"] * 0.002)
    for ledger in report["allocation_ledger"]:
        assert all(v <= 0.45 + 1e-12 for v in ledger["realized_sector_weights"].values())
        assert sum(ledger["realized_sector_weights"].values()) + ledger[
            "entry_cash_fraction"
        ] == pytest.approx(1)
    if mode == "cash":
        assert report["executions"] == [] and report["ending_equity"] == policy.capital
        assert report["daily_risk"]["annualized_volatility"] == 0
        assert report["daily_risk"]["sharpe_zero_risk_free"] is None


def test_missing_entry_stays_cash_and_future_prices_do_not_set_targets():
    data = fixture()
    policy = PortfolioPolicy(allocation="inverse_volatility", min_dollar_volume=0, min_price=0.01)
    base = simulate(data, policy)
    first = base["executions"][0]
    missing = data.model_copy(
        update={
            "bars": [
                b
                for b in data.bars
                if not (b.security_id == first["security_id"] and str(b.session) == first["entry"])
            ]
        }
    )
    changed = simulate(missing, policy)
    assert base["allocation_ledger"][0]["targets"] == changed["allocation_ledger"][0]["targets"]
    assert (
        changed["allocation_ledger"][0]["entry_cash_fraction"]
        > base["allocation_ledger"][0]["entry_cash_fraction"]
    )
    altered = data.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        "close": b.close * 1.1,
                        "open": b.open * 1.1,
                        "high": b.high * 1.1,
                        "low": b.low * 1.1,
                    }
                )
                if str(b.session) > first["decision"]
                else b
                for b in data.bars
            ]
        }
    )
    assert (
        simulate(altered, policy)["allocation_ledger"][0]["targets"]
        == base["allocation_ledger"][0]["targets"]
    )


def test_fixed_comparators_preserve_policies_and_full_ledgers():
    comparisons = comparator_runs(
        fixture(), PortfolioPolicy(max_position=0.3, max_sector=0.4, one_way_cost_bps=50)
    )
    assert len(comparisons) == 7 and len({r["id"] for r in comparisons}) == 7
    assert {r["policy"]["allocation"] for r in comparisons} == set(MODES)
    for r in comparisons:
        assert r["policy"]["max_position"] == 0.3 and r["policy"]["max_sector"] == 0.4
        assert r["policy"]["one_way_cost_bps"] == 50
        assert r["allocation_ledger"] and r["daily_curve"]
        assert "exclusions" in r and "executions" in r
    with pytest.raises(ValidationError):
        PortfolioPolicy(allocation="optimized_hindsight")
    with pytest.raises(ValidationError):
        PortfolioPolicy(volatility_window=30)


def test_zero_volatility_pool_stays_cash_with_sourced_exclusions():
    data = fixture()
    flat = data.model_copy(
        update={
            "bars": [
                b.model_copy(update={"open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0})
                for b in data.bars
            ]
        }
    )
    report = simulate(flat, PortfolioPolicy(allocation="inverse_volatility", min_dollar_volume=0))
    assert report["executions"] == [] and report["ending_equity"] == 100_000
    assert all(p["entry_cash_fraction"] == 1 for p in report["allocation_ledger"])
    for plan in report["allocation_ledger"]:
        assert plan["exclusions"]
        for excluded in plan["exclusions"]:
            assert excluded["reason"] == "ZERO_REFERENCE_VOLATILITY"
            assert excluded["volatility"]["value"] == 0
            assert excluded["volatility"]["source_ids"] == ["fixture-v1"]
            assert excluded["volatility"]["latest_available_at"] <= plan["asof_time"]
