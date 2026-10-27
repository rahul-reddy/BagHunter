"""Fixed fixture stresses, source binding, policy boundaries and unavailable variants."""

import copy
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from packages.backtest.constrained import PortfolioPolicy, simulate
from packages.backtest.risk import daily_risk
from packages.backtest.robustness import robustness
from packages.data.fixture import fixture
from packages.research.features import snapshot
from packages.shared.models import Fact


@pytest.fixture(scope="module")
def stress_report():
    return robustness(fixture(), PortfolioPolicy())


def test_every_stress_is_retained_with_shared_engine_and_explicit_hindsight(stress_report):
    report = stress_report
    assert len(report["attempts"]) == 12
    assert len({row["id"] for row in report["attempts"]}) == 12
    assert sum(report["contributions"]["names"].values()) == pytest.approx(
        report["baseline"]["ending_equity"] - report["base_policy"]["capital"]
    )
    for attempt in report["attempts"]:
        if attempt["report"] is None:
            assert attempt["status"] == "UNAVAILABLE" and attempt["reason"]
            continue
        result = attempt["report"]
        assert result["dataset_sha256"] == report["dataset_sha256"]
        assert result["daily_curve"] and result["allocation_ledger"]
        for key, value in report["base_policy"].items():
            if key not in attempt["requested_changes"]:
                assert result["policy"][key] == value
        for plan in result["allocation_ledger"]:
            clock = datetime.fromisoformat(plan["asof_time"])
            for target in plan["targets"]:
                assert target["filing_lag_hours"] == result["policy"]["filing_lag_hours"]
                for fact in target["known_filing_inputs"]:
                    assert (
                        max(
                            datetime.fromisoformat(fact["published_at"]).astimezone(UTC),
                            datetime.fromisoformat(fact["accepted_at"]).astimezone(UTC),
                        )
                        + timedelta(hours=target["filing_lag_hours"])
                        <= clock
                    )
        for trade in result["executions"]:
            assert trade["entry_notional"] <= trade["capacity_limit"]
            assert (
                trade["entry_notional"] + trade["entry_cost"]
                <= trade["starting_capital"] * result["policy"]["max_position"] + 1e-8
            )
    drop_name, drop_sector = report["attempts"][:2]
    assert (
        drop_name["selection_scope"]
        == drop_sector["selection_scope"]
        == "EX_POST_CONTRIBUTION_DIAGNOSTIC"
    )
    assert report["contributions"]["highest_name"] not in {
        t["security_id"] for t in drop_name["report"]["executions"]
    }
    assert report["contributions"]["highest_sector"] not in {
        t["sector"] for t in drop_sector["report"]["executions"]
    }
    assert any(
        e["reason"] == "DECLARED_SECURITY_EXCLUSION" for e in drop_name["report"]["exclusions"]
    )
    assert report["attempts"][-1]["report"] is None
    assert "ADJUSTED_SERIES_CONTRACT" in report["attempts"][-1]["reason"]
    json.dumps(report, allow_nan=False)


def test_baseline_binding_rejects_different_data_or_policy(stress_report):
    data = fixture()
    with pytest.raises(ValueError, match="binding"):
        robustness(
            data.model_copy(update={"facts": []}), PortfolioPolicy(), stress_report["baseline"]
        )
    with pytest.raises(ValueError, match="binding"):
        robustness(data, PortfolioPolicy(max_position=0.1), stress_report["baseline"])


def test_failed_stresses_and_empty_ex_post_groups_do_not_disappear():
    report = robustness(fixture(), PortfolioPolicy(min_dollar_volume=1e308, one_way_cost_bps=1000))
    assert report["contributions"]["highest_name"] is None
    assert report["attempts"][0]["reason"] == "NO_EXECUTED_NAMES"
    rejected = {a["id"]: a for a in report["attempts"] if a["status"] == "REJECTED"}
    assert "wider_cost_2x_or_100bps" in rejected
    assert rejected["liquidity_floor_10x"]["requested_changes"]["min_dollar_volume"] is None
    assert rejected["liquidity_floor_10x"]["unrepresentable_fields"] == ["min_dollar_volume"]
    assert all(row["report"] is None for row in rejected.values())
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize(
    "change",
    [
        {"filing_lag_hours": 23},
        {"filing_lag_hours": 721},
        {"excluded_security_ids": ["a", "a"]},
        {"excluded_sectors": [""]},
        {"excluded_cap_buckets": [" micro"]},
        {"delist_proceeds": "infer_terminal_price"},
    ],
)
def test_declared_policy_bounds_reject(change):
    with pytest.raises(ValidationError):
        PortfolioPolicy(**change)


def test_explicit_exclusions_are_exact_canonical_and_do_not_silently_ignore_typos():
    data = fixture()
    policy = PortfolioPolicy(excluded_security_ids=("fx-steady", "fx-compound"))
    assert policy.excluded_security_ids == ("fx-compound", "fx-steady")
    report = simulate(data, policy)
    assert not {"fx-compound", "fx-steady"} & {t["security_id"] for t in report["executions"]}
    micro = data.model_copy(
        update={
            "instruments": [
                i.model_copy(update={"cap_bucket": "fixture-micro"})
                if i.security_id == "fx-compound"
                else i
                for i in data.instruments
            ]
        }
    )
    excluded = simulate(micro, PortfolioPolicy(excluded_cap_buckets=("fixture-micro",)))
    assert "fx-compound" not in {t["security_id"] for t in excluded["executions"]}
    assert any(e["reason"] == "DECLARED_CAP_BUCKET_EXCLUSION" for e in excluded["exclusions"])
    with pytest.raises(ValueError, match="Declared exclusion"):
        simulate(data, PortfolioPolicy(excluded_security_ids=("mistyped",)))
    with pytest.raises(ValueError, match="Declared exclusion"):
        simulate(data, PortfolioPolicy(excluded_sectors=("Not a known sector",)))


def test_longer_filing_lag_changes_available_growth_without_rewriting_sources():
    data = fixture()
    day = sorted({b.session for b in data.bars})[260]
    clock = datetime.combine(day, datetime.min.time(), UTC).replace(hour=23)
    common = {
        "security_id": "fx-compound",
        "metric": "annual_revenue",
        "unit": "USD",
        "source_id": "independent-fixture",
        "source_url": "https://example.invalid/fixture",
    }
    before = Fact(
        **common,
        period_end="2017-12-31",
        value=100,
        accession="before",
        accepted_at=clock - timedelta(days=20),
        published_at=clock - timedelta(days=20),
    )
    current = Fact(
        **common,
        period_end="2018-12-31",
        value=150,
        accession="current",
        accepted_at=clock - timedelta(hours=25),
        published_at=clock - timedelta(hours=25),
    )
    facts = [before, current]
    original = copy.deepcopy(facts)
    assert snapshot(data.instruments[0], data.bars, facts, clock)["revenue_growth"] == 0.5
    delayed = snapshot(data.instruments[0], data.bars, facts, clock, lag_hours=72)
    assert delayed["revenue_growth"] is None and delayed["processing_lag_hours"] == 72
    changed = data.model_copy(update={"facts": facts})
    report = simulate(changed, PortfolioPolicy(selector="revenue_growth", filing_lag_hours=72))
    assert any(
        e["decision"] == str(day) and e["reason"] == "MISSING_DATED_REVENUE_GROWTH"
        for e in report["exclusions"]
    )
    assert facts == original
    with pytest.raises(ValueError, match="lag"):
        snapshot(data.instruments[0], data.bars, facts, clock, lag_hours=0)


def test_zero_proceeds_is_a_declared_assumption_not_a_source_repair():
    data = fixture()
    revised = data.model_copy(
        update={"actions": [a.model_copy(update={"value": 2.0}) for a in data.actions]}
    )
    original = revised.model_dump_json()
    base = simulate(revised, PortfolioPolicy(min_price=0.01, min_dollar_volume=0))
    stress = simulate(
        revised,
        PortfolioPolicy(min_price=0.01, min_dollar_volume=0, delist_proceeds="zero_sensitivity"),
    )
    assert base["ending_equity"] > stress["ending_equity"]
    assert any(t["delisted"] for t in stress["executions"])
    assert stress["action_assumptions"][0]["reported_proceeds"] == 2
    assert stress["action_assumptions"][0]["assumed_proceeds"] == 0
    assert revised.model_dump_json() == original
    broken = data.model_copy(
        update={"actions": [a.model_copy(update={"value": -1}) for a in data.actions]}
    )
    with pytest.raises(ValueError):
        simulate(broken, PortfolioPolicy(delist_proceeds="zero_sensitivity"))
    unknown = data.model_copy(update={"actions": []})
    with pytest.raises(ValueError):
        simulate(
            unknown,
            PortfolioPolicy(
                min_price=0.01, min_dollar_volume=0, delist_proceeds="zero_sensitivity"
            ),
        )


def test_drawdown_recovery_retains_an_unfinished_tail():
    def curve(values):
        return [{"date": f"2020-01-{i + 1:02d}", "equity": value} for i, value in enumerate(values)]

    recovered = daily_risk(curve([100, 80, 90, 100]))
    assert recovered["max_drawdown_recovery_sessions"] == 2
    assert recovered["drawdown_recovery_status"] == "RECOVERED"
    open_tail = daily_risk(curve([100, 90, 80, 85]))
    assert open_tail["max_drawdown_recovery_sessions"] is None
    assert open_tail["underwater_sessions_at_end"] == 3
    assert open_tail["drawdown_recovery_status"] == "UNRECOVERED_AT_END"
    assert (
        daily_risk(curve([100, 0, 0]))["drawdown_recovery_status"]
        == "UNDEFINED_AFTER_EQUITY_EXHAUSTION"
    )
