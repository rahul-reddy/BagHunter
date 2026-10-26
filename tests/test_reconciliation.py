"""Company text and share-class evidence never substitute for independent identity proof."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_finviz import export as export
from test_reference import archive, candidate, path
from test_reference import batch as batch

from packages.data.finviz import _json, read_snapshot
from packages.data.reconciliation import compare_names, inspect_reference


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("Fictional Inc. Class A", "Fictional Inc. Class A", "EXACT_TEXT"),
        (" Fictional  CAFÉ ", "fictional café", "CASE_WHITESPACE_ONLY"),
        ("Fictional Inc.", "Fictional Inc", "DIFFERENT_TEXT"),
        ("Fictional Inc", "Fictional", "DIFFERENT_TEXT"),
        ("Fictional Class A", "Fictional Class B", "DIFFERENT_TEXT"),
        ("Fictional café", "Fictional cafe", "DIFFERENT_TEXT"),
        ("Fictional A", "Fictional-A", "DIFFERENT_TEXT"),
    ],
)
def test_text_comparison_preserves_distinguishing_names(left, right, expected):
    assert compare_names(left, right) == expected


def inspect(evidence):
    return inspect_reference(evidence["reference_id"], evidence["base_snapshot_id"], "FIXTURE")[
        "reconciliation"
    ]


def test_report_is_source_bound_deterministic_readonly_and_not_promotion(batch, monkeypatch):
    evidence = archive(batch, [{"data": [candidate(name="Fictional café")]}, {"data": []}])

    def fail(*args, **kwargs):
        raise AssertionError("Comparison attempted a write")

    monkeypatch.setattr(Path, "write_bytes", fail)
    monkeypatch.setattr(Path, "mkdir", fail)
    report = inspect(evidence)
    assert inspect(evidence) == report
    digest = report.pop("report_sha256")
    assert digest == hashlib.sha256(_json(report)).hexdigest()
    assert report["reference_id"] == evidence["reference_id"]
    assert report["reference_response_sha256"] == evidence["response_sha256"]
    assert report["name_comparison_counts"] == {"EXACT_TEXT": 1}
    assert report["issue_counts"] == {}
    first, second = report["records"]
    assert first["source_company"] == "Fictional café"
    assert first["source_security_id"] is None and first["source_security_type"] == "unknown"
    assert first["disposition"] == "REVIEW_REQUIRED"
    assert first["candidates"][0]["identity_verified"] is False
    assert first["candidates"][0]["share_class_verified"] is False
    assert second["disposition"] == "NO_CANDIDATE_EVIDENCE"
    assert report["identity_promotions"] == 0
    assert "FIXTURE_ONLY" in report["flags"]
    _, rows = read_snapshot(evidence["base_snapshot_id"], "FIXTURE")
    assert all(row.security_id is None and row.security_type == "unknown" for row in rows)


@pytest.mark.parametrize("field", ["figi", "compositeFIGI", "shareClassFIGI"])
def test_shared_identifiers_are_scoped_by_level_and_source_ticker(batch, field):
    first = candidate()
    second = candidate(ticker="DEMO-B", figi="BBG000TST003", shareClassFIGI="BBG000TST004")
    second[field] = first[field]
    report = inspect(archive(batch, [{"data": [first]}, {"data": [second]}]))
    assert report["issue_counts"][f"SHARED_{field.upper()}_IN_BATCH"] == 2
    assert report["records"][0]["candidates"][0]["shared_identifiers"] == {field: ["DEMO-B"]}
    assert report["records"][1]["candidates"][0]["shared_identifiers"] == {field: ["DEMO-A"]}


def test_ambiguity_context_and_missing_class_are_not_resolved_by_names(batch):
    report = inspect(
        archive(
            batch,
            [
                {
                    "data": [
                        candidate(name="Fictional café", shareClassFIGI=None, compositeFIGI=None),
                        candidate(figi="BBG000TST003", name="Fictional café"),
                    ]
                },
                {"data": [candidate(ticker="OTHER", name="Imaginary company")]},
            ],
        )
    )
    first, second = report["records"]
    assert first["reference_status"] == "AMBIGUOUS"
    assert len(first["candidates"]) == 2
    assert first["candidates"][0]["name_comparison"] == "EXACT_TEXT"
    assert set(first["candidates"][0]["issues"]) >= {
        "AMBIGUOUS",
        "MISSING_SHARECLASSFIGI",
        "MISSING_COMPOSITEFIGI",
    }
    assert "CONTEXT_MISMATCH" in second["candidates"][0]["issues"]
    assert all(
        c["disposition"] == "REVIEW_REQUIRED" for r in report["records"] for c in r["candidates"]
    )


def test_same_class_within_one_source_not_cross_ticker_conflict(batch):
    report = inspect(
        archive(
            batch,
            [
                {"data": [candidate(), candidate(figi="BBG000TST003")]},
                {"data": []},
            ],
        )
    )
    assert all(not c["shared_identifiers"] for c in report["records"][0]["candidates"])


def test_source_binding_and_corruption_reject_instead_of_producing_comparison(batch):
    evidence = archive(batch)
    with pytest.raises(ValueError):
        inspect_reference(evidence["reference_id"], "0" * 64, "FIXTURE")
    (path(evidence) / "response.json").write_bytes(b"[]")
    with pytest.raises(ValueError):
        inspect(evidence)


def test_changed_reference_changes_report_digest(batch):
    first = inspect(archive(batch))
    second = inspect(archive(batch, [{"data": [candidate(name="Different name")]}, {"data": []}]))
    assert first["report_sha256"] != second["report_sha256"]


def test_cli_outputs_summary_without_source_rows_or_invalid_inputs(batch):
    evidence = archive(batch)
    command = [
        sys.executable,
        "-m",
        "packages.cli",
        "reconcile-reference",
        "--snapshot",
        evidence["base_snapshot_id"],
        "--reference",
        evidence["reference_id"],
        "--mode",
        "FIXTURE",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["identity_promotions"] == 0 and "records" not in summary
    assert "Fictional" not in result.stdout and "DEMO-A" not in result.stdout
    command[command.index("--reference") + 1] = "PRIVATE_SENTINEL"
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2
    assert "PRIVATE_SENTINEL" not in result.stdout + result.stderr
