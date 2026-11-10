"""Replay assertions preserve source identity, policy intent and transactional failure."""

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages import cli
from packages.shared.replay import ReplayConfig, read_object, verify_manifest


@pytest.mark.parametrize(
    "body",
    [b"[]", b'{"a":1,"a":2}', b'{"a":NaN}', b"{" * 65537],
    ids=["array", "duplicate", "nonfinite", "oversize"],
)
def test_replay_inputs_reject_nonobjects_duplicates_constants_and_budget(tmp_path, body):
    path = tmp_path / "input.json"
    path.write_bytes(body)
    with pytest.raises(ValueError):
        read_object(path)


def test_config_validates_all_policies_and_forbids_unknown_controls():
    config = ReplayConfig.model_validate(
        {"discovery": {"min_dollar_volume": 2e6}, "portfolio": {"seed": 19}}
    )
    assert config.discovery.min_dollar_volume == 2e6 and config.portfolio.seed == 19
    for value in (
        {"secret": "never-echo"},
        {"portfolio": {"max_position": 2}},
        {"event": {"seed": "bad"}},
    ):
        with pytest.raises(ValidationError):
            ReplayConfig.model_validate(value)


def test_manifest_verification_requires_exact_original_source(tmp_path):
    path = tmp_path / "source_manifest.json"
    expected = {"source_id": "fixture-v1", "mode": "FIXTURE", "sha256": "a" * 64}
    path.write_text(json.dumps(expected), encoding="utf-8")
    verify_manifest(path, expected)
    for changed in (
        expected | {"mode": "EXTERNAL_UNVERIFIED"},
        expected | {"sha256": "b" * 64},
        expected | {"extra": 1},
    ):
        path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="manifest differs"):
            verify_manifest(path, expected)


def test_cli_explicit_controls_pass_validated_policies_and_preserve_seed(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "config.json"
    path.write_text('{"discovery":{"min_dollar_volume":2000000}}', encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli, "run", lambda *a, **k: calls.append((a, k)) or {"mode": "FIXTURE"})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "baghunter",
            "demo",
            "--config",
            str(path),
            "--seed",
            "19",
            "--universe",
            "fixture-common-v1",
            "--source-manifest",
            "saved.json",
            "--output",
            str(tmp_path / "fixture"),
        ],
    )
    cli.main()
    args, kwargs = calls[0]
    assert args[2] == 19 and args[3].min_dollar_volume == 2e6
    assert args[4].seed == args[5].seed == 19
    assert kwargs["source_manifest"] == Path("saved.json")
    assert json.loads(capsys.readouterr().out) == {"mode": "FIXTURE"}


def test_cli_conflicting_configs_fail_before_publication_without_input_echo(
    tmp_path, monkeypatch, capsys
):
    config = tmp_path / "config.json"
    config.write_text('{"secret":"do-not-print-this"}', encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli, "run", lambda *a, **k: calls.append(a))
    for extra in ([], ["--policy", "other.json"]):
        monkeypatch.setattr(sys, "argv", ["baghunter", "demo", "--config", str(config), *extra])
        with pytest.raises(SystemExit) as error:
            cli.main()
        assert error.value.code == 2
        output = capsys.readouterr()
        assert "do-not-print-this" not in output.err + output.out
    assert calls == []


def test_bad_manifest_is_checked_before_cached_run_reactivation(tmp_path):
    from datetime import datetime

    from packages.pipeline import DEFAULT_ASOF, run

    output = tmp_path / "fixture/latest"
    output.mkdir(parents=True)
    (output / "CURRENT").write_text("preserved", encoding="utf-8")
    path = tmp_path / "source.json"
    path.write_text('{"mode":"EXTERNAL_UNVERIFIED"}', encoding="utf-8")
    with pytest.raises(ValueError, match="manifest differs"):
        run(output, datetime.fromisoformat(DEFAULT_ASOF), source_manifest=path)
    assert (output / "CURRENT").read_text(encoding="utf-8") == "preserved"
    assert not (output / "runs").exists()
