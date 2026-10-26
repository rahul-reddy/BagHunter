import hashlib
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.main import app
from packages.backtest.toy import evaluate
from packages.data.fixture import fixture
from packages.data.providers import SecClient, UnconfiguredMarketProvider
from packages.pipeline import DEFAULT_ASOF, run
from packages.research.features import assert_pit, facts_at, snapshot, symbol_at
from packages.research.outcomes import matched_pairs, outcome, wealth_path
from packages.shared.models import Action, Bar, Symbol


@pytest.fixture(scope="module")
def dataset():
    return fixture()


@pytest.fixture(scope="module")
def published(tmp_path_factory):
    root = tmp_path_factory.mktemp("pipeline") / "fixture" / "latest"
    summary = run(root, datetime.fromisoformat(DEFAULT_ASOF), 7)
    folder = root / "runs" / summary["run_id"]
    return root, folder, json.loads((folder / "run.json").read_text())


def test_future_filings_and_amendments_are_excluded(dataset):
    original = dataset.facts[0]
    amended = original.model_copy(
        update={
            "published_at": original.published_at + timedelta(days=300),
            "accepted_at": original.accepted_at + timedelta(days=300),
            "value": 999999999,
            "amended": True,
        }
    )
    cutoff = original.published_at + timedelta(hours=24)
    assert facts_at([original, amended], original.security_id, cutoff) == [original]
    assert facts_at([original], original.security_id, cutoff - timedelta(seconds=1)) == []
    assert facts_at(
        [original, amended], original.security_id, amended.published_at + timedelta(hours=24)
    ) == [original, amended]
    assert original.value != amended.value


def test_pit_guard_rejects_future(dataset):
    with pytest.raises(ValueError, match="PIT"):
        assert_pit([dataset.facts[0].published_at], datetime(2018, 1, 1, tzinfo=UTC))


def test_snapshot_does_not_change_with_future_observations(dataset):
    cutoff = datetime(2020, 1, 1, 23, tzinfo=UTC)
    instrument = dataset.instruments[0]
    expected = snapshot(instrument, dataset.bars, dataset.facts, cutoff)
    future_facts = [
        f.model_copy(update={"value": 999999999}) if f.published_at > cutoff else f
        for f in dataset.facts
    ]
    future_bars = [
        b.model_copy(update={"close": 999999, "high": 999999}) if b.available_at > cutoff else b
        for b in dataset.bars
    ]
    assert snapshot(instrument, future_bars, future_facts, cutoff) == expected
    assert datetime.fromisoformat(expected["latest_included_publication"]) <= cutoff


def test_predictor_has_no_outcome_argument():
    import inspect

    assert set(inspect.signature(snapshot).parameters) == {"instrument", "bars", "facts", "asof"}


def test_missing_factors_are_null_and_penalized(dataset):
    f = snapshot(dataset.instruments[0], dataset.bars, [], datetime.fromisoformat(DEFAULT_ASOF))
    assert f["components"]["fundamental_inflection"] is None
    assert f["completeness"] == 0.3
    assert f["missing_weight_penalty"] == 70
    assert 0 <= f["score"] <= 30


def test_symbol_changes_do_not_merge_different_securities():
    symbols = [
        Symbol(
            security_id="old-company",
            ticker="SAME",
            valid_from=date(2000, 1, 1),
            valid_to=date(2010, 1, 1),
        ),
        Symbol(security_id="new-company", ticker="SAME", valid_from=date(2015, 1, 1)),
    ]
    assert symbol_at(symbols, "old-company", datetime(2005, 1, 1, tzinfo=UTC)) == "SAME"
    with pytest.raises(ValueError, match="identity"):
        symbol_at(symbols, "new-company", datetime(2005, 1, 1, tzinfo=UTC))


def test_invalid_records_rejected(dataset):
    bar = dataset.bars[0].model_dump()
    for change in (
        {"close": 0},
        {"volume": -1},
        {"close": float("nan")},
        {"low": 9999},
        {"available_at": datetime(2020, 1, 1)},
    ):
        with pytest.raises(ValidationError):
            Bar(**(bar | change))


def test_duplicate_and_insufficient_bars_rejected(dataset):
    with pytest.raises(ValueError, match="duplicate"):
        snapshot(
            dataset.instruments[0],
            dataset.bars + [dataset.bars[0]],
            dataset.facts,
            datetime.fromisoformat(DEFAULT_ASOF),
        )
    with pytest.raises(ValueError, match="insufficient"):
        snapshot(
            dataset.instruments[0], dataset.bars[:10], [], datetime.fromisoformat(DEFAULT_ASOF)
        )


def test_zero_volume_has_explicit_error(dataset):
    # Prevent infinite relative-volume ranks; a zero-volume baseline is not a signal.
    bars = [b.model_copy(update={"volume": 0}) for b in dataset.bars]
    with pytest.raises(ValueError, match="volume"):
        snapshot(dataset.instruments[0], bars, [], datetime.fromisoformat(DEFAULT_ASOF))


def raw_bar(day, close):
    return Bar(
        security_id="unit",
        session=day,
        available_at=datetime.combine(day, datetime.min.time(), UTC),
        open=close,
        close=close,
        high=close,
        low=close,
        volume=1,
        source_id="independent-unit",
    )


def test_split_dividend_delisting_independent_expected_wealth():
    start, second, end = date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)
    bars = [raw_bar(start, 100), raw_bar(second, 50)]
    actions = [
        Action(security_id="unit", effective_date=second, kind="split", value=2, source_id="unit"),
        Action(
            security_id="unit", effective_date=second, kind="dividend", value=1, source_id="unit"
        ),
        Action(security_id="unit", effective_date=end, kind="delist", value=20, source_id="unit"),
    ]
    assert wealth_path(bars, actions, start, end) == [(start, 100), (second, 102), (end, 42)]


def test_post_delisting_price_rejected():
    start, end = date(2020, 1, 1), date(2020, 1, 3)
    actions = [
        Action(
            security_id="unit",
            effective_date=date(2020, 1, 2),
            kind="delist",
            value=0,
            source_id="unit",
        )
    ]
    with pytest.raises(ValueError, match="after delisting"):
        wealth_path([raw_bar(start, 100), raw_bar(end, 50)], actions, start, end)


def test_incomplete_labels_stay_missing_and_failure_is_not_dropped(dataset):
    winner = outcome("fx-compound", dataset.bars, dataset.actions, date(2020, 1, 1), 1)
    assert winner["max_multiple"] >= 5
    assert winner["max_multiple"] != winner["terminal_total_return"]
    incomplete = outcome("fx-compound", dataset.bars, dataset.actions, date(2020, 1, 1), 5)
    assert incomplete["coverage_flag"] == "INCOMPLETE_HORIZON"
    assert incomplete["terminal_total_return"] is None
    failure = outcome("fx-failure", dataset.bars, dataset.actions, date(2020, 1, 1), 3)
    assert failure["delisted"]
    assert failure["terminal_total_return"] == -1


def test_cohort_uses_asof_peers_and_seed(dataset, published):
    labels = published[2]["study"]["labels"]
    anchor = datetime(2020, 1, 1, 23, tzinfo=UTC)
    pairs = matched_pairs(dataset.instruments, labels, anchor, 7)
    assert len(pairs) == 1
    assert pairs[0]["control_security_id"] == "fx-failure"
    future = [
        i.model_copy(update={"first_seen": date(2021, 1, 1)})
        if i.security_id == "fx-failure"
        else i
        for i in dataset.instruments
    ]
    assert matched_pairs(future, labels, anchor, 7) == []


def test_toy_next_open_costs_and_nonoverlapping_windows(dataset):
    result = evaluate(dataset, 7)
    assert len(result["rows"]) == 13
    bars = {(b.security_id, str(b.session)): b for b in dataset.bars}
    previous_exit = ""
    for row in result["rows"]:
        assert previous_exit < row["decision"] < row["entry"] < row["exit"]
        expected = (
            bars[row["security_id"], row["exit"]].close
            / bars[row["security_id"], row["entry"]].open
            - 1
            - 0.004
        )
        assert row["net_return"] == pytest.approx(expected)
        assert row["benchmark_net"] is not None
        previous_exit = row["exit"]


def test_missing_evaluation_exit_cannot_be_reported_as_flat_wealth(dataset):
    first_exit = evaluate(dataset, 7)["rows"][0]["exit"]
    incomplete = dataset.model_copy(
        update={
            "bars": [
                b
                for b in dataset.bars
                if not (b.security_id == "fx-market" and str(b.session) == first_exit)
            ]
        }
    )
    with pytest.raises(ValueError, match="Incomplete evaluation coverage"):
        evaluate(incomplete, 7)


def test_same_day_dividend_precedes_delisting_regardless_of_input_order():
    start, end = date(2020, 1, 1), date(2020, 1, 2)
    events = [
        Action(security_id="unit", effective_date=end, kind="delist", value=20, source_id="unit"),
        Action(security_id="unit", effective_date=end, kind="dividend", value=3, source_id="unit"),
    ]
    assert wealth_path([raw_bar(start, 100)], events, start, end)[-1][1] == 23
    assert wealth_path([raw_bar(start, 100)], list(reversed(events)), start, end)[-1][1] == 23


def test_equivalent_timezone_clocks_produce_identical_snapshots(dataset):
    # A positive offset changes the calendar date but not the instant of observation.
    utc = datetime.fromisoformat(DEFAULT_ASOF)
    offset = datetime.fromisoformat("2022-01-04T01:00:00+02:00")
    assert snapshot(dataset.instruments[0], dataset.bars, dataset.facts, utc) == snapshot(
        dataset.instruments[0], dataset.bars, dataset.facts, offset
    )


def test_pipeline_reproducible_manifest_and_separate_tables(published):
    root, folder, data = published
    first = hashlib.sha256((folder / "run.json").read_bytes()).hexdigest()
    second = run(root, datetime.fromisoformat(DEFAULT_ASOF), 7)
    assert data["run_id"] == second["run_id"]
    assert hashlib.sha256((folder / "run.json").read_bytes()).hexdigest() == first
    assert (folder / "gold" / "features.parquet").exists()
    assert (folder / "hindsight" / "labels.parquet").exists()
    raw = root.parent / "raw" / f"{data['sources'][0]['sha256']}.json"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == data["sources"][0]["sha256"]


def test_fixture_cannot_overwrite_real_output(tmp_path):
    with pytest.raises(ValueError, match="fixture"):
        run(tmp_path / "real", datetime.fromisoformat(DEFAULT_ASOF))


def test_api_empty_stale_sources_filters_and_no_order_route(published, monkeypatch, tmp_path):
    monkeypatch.setenv("BAGHUNTER_DATA", str(tmp_path / "missing"))
    with TestClient(app) as client:
        assert client.get("/health").json()["data_ready"] is False
        assert client.get("/signals").status_code == 503
        monkeypatch.setenv("BAGHUNTER_DATA", str(published[0]))
        assert client.get("/health").json()["data_ready"] is True
        assert client.get("/runs/current").json()["age_days"] > 0
        assert client.get("/signals?stage=IGNITION").json() == []
        assert client.get("/signals?asof=2099").status_code == 404
        assert client.get("/stocks/fx-compound/profile").status_code == 200
        assert client.get("/stocks/no-such/profile").status_code == 404
        assert client.get("/sources/fixture-v1").json()["mode"] == "FIXTURE"
        assert client.get("/backtests/no-such").status_code == 404
        assert client.post("/orders", json={}).status_code == 404


def test_provider_unavailable_is_not_fake_success(tmp_path):
    assert UnconfiguredMarketProvider().get_coverage_report()["status"] == "BLOCKED"
    with pytest.raises(RuntimeError, match="no fallback"):
        UnconfiguredMarketProvider().get_bars([], "2020", "2021", "raw")
    with pytest.raises(ValueError, match="contact"):
        SecClient("example example@example.com", tmp_path)


def test_sec_cache_http_failure_and_retry(tmp_path, monkeypatch):
    import httpx

    import packages.data.providers as providers

    original_client = httpx.Client
    attempts = []

    def respond(request):
        attempts.append(str(request.url))
        if len(attempts) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"cik": 320193, "filings": {"recent": {}}})

    monkeypatch.setattr(providers.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        providers.httpx,
        "Client",
        lambda **kw: original_client(transport=httpx.MockTransport(respond), **kw),
    )
    manifest = SecClient("BagHunter Lab contact@baghunter.invalid", tmp_path).submissions("320193")
    assert len(attempts) == 2
    assert manifest["status"] == "RAW_ONLY_NOT_PIT_NORMALIZED"
    assert (tmp_path / f"{manifest['sha256']}.json").exists()


def test_api_rejects_corrupt_pointer(tmp_path, monkeypatch):
    (tmp_path / "CURRENT").write_text("../../secrets")
    monkeypatch.setenv("BAGHUNTER_DATA", str(tmp_path))
    assert TestClient(app).get("/runs/current").status_code == 503
