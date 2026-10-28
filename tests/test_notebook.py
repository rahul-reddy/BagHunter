"""A failed or invalid notebook cannot leave a stale successful execution receipt."""

import json

import pytest

from scripts import run_research_notebook


@pytest.mark.parametrize("failure", ["unsupported", "duplicate", "interrupted", "failed"])
def test_notebook_failure_replaces_stale_receipt_and_restores_working_directory(
    tmp_path, monkeypatch, failure
):
    folder = tmp_path / "notebooks"
    folder.mkdir()
    cell = {"cell_type": "code", "id": "controlled", "source": ["raise RuntimeError()"]}
    document = {"nbformat": 4, "cells": [cell]}
    expected = RuntimeError
    if failure == "unsupported":
        document["nbformat"] = 3
        expected = ValueError
    elif failure == "duplicate":
        document["cells"].append(cell)
        expected = ValueError
    elif failure == "interrupted":
        cell["source"] = ["raise KeyboardInterrupt()"]
        expected = KeyboardInterrupt
    (folder / "fixture_research.ipynb").write_text(json.dumps(document), encoding="utf-8")
    evidence = tmp_path / "artifacts/test_results"
    evidence.mkdir(parents=True)
    (evidence / "notebook-execution.json").write_text('{"status":"PASS","run_id":"stale"}')
    monkeypatch.setattr(run_research_notebook, "ROOT", tmp_path)
    before = run_research_notebook.Path.cwd()
    with pytest.raises(expected):
        run_research_notebook.main()
    receipt = json.loads((evidence / "notebook-execution.json").read_text())
    assert receipt["status"] == "FAILED_OR_INTERRUPTED" and "run_id" not in receipt
    assert run_research_notebook.Path.cwd() == before
    assert len(receipt["notebook_sha256"]) == 64
