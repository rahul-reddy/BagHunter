"""Fictional attributed documents exercise trust, binding and archive boundaries."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_finviz import export as export
from test_reference import archive
from test_reference import batch as batch

from packages.data.finviz import _json, read_snapshot
from packages.data.issuer import MAX_DOCUMENT, audit_issuer


@pytest.fixture
def dossier(batch, tmp_path):
    evidence = archive(batch)
    bundle = tmp_path / "issuer"
    bundle.mkdir()
    body = b"Fictional issuer document. No real market evidence."
    (bundle / "issuer.txt").write_bytes(body)
    manifest = {
        "version": "issuer-evidence-dossier-v1",
        "mode": "FIXTURE",
        "base_snapshot_id": evidence["base_snapshot_id"],
        "reference_id": evidence["reference_id"],
        "ticker": "DEMO-A",
        "candidate_figi": "BBG000TST001",
        "documents": [
            {
                "filename": "issuer.txt",
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "source_url": "https://issuer.example.org/report",
                "discovered_from": "https://issuer.example.org/reports",
                "retrieved_at": "2020-01-03T00:00:00Z",
                "published_at": None,
                "locator": "Cover page",
                "issuer_name": "Fictional café",
                "ticker": "DEMO-A",
                "exchange": "Fictional exchange",
                "class_title": "Common stock",
            }
        ],
        "unresolved": ["Independent FIGI assignment absent"],
    }
    return bundle, manifest


def save(dossier):
    bundle, manifest = dossier
    (bundle / "dossier.json").write_bytes(_json(manifest))
    return bundle


def audit(dossier):
    bundle = save(dossier)
    m = dossier[1]
    return audit_issuer(bundle, m["base_snapshot_id"], m["reference_id"], "FIXTURE")


def test_reproducible_readonly_no_promotion(dossier, monkeypatch):
    report = audit(dossier)
    digest = report.pop("report_sha256")
    assert digest == hashlib.sha256(_json(report)).hexdigest()
    assert report["documents"][0]["source_name_comparison"] == "EXACT_TEXT"
    assert report["documents"][0]["candidate_name_comparison"] == "DIFFERENT_TEXT"
    assert report["documents"][0]["ticker_text_agrees"] is True
    assert not report["identity_verified"] and not report["share_class_verified"]
    assert report["identity_promotions"] == 0
    assert report["disposition"] == "REVIEW_REQUIRED"
    assert "FIXTURE_ONLY" in report["flags"]

    def fail(*args, **kwargs):
        raise AssertionError("Audit attempted a write or request")

    monkeypatch.setattr(Path, "write_bytes", fail)
    monkeypatch.setattr(Path, "mkdir", fail)
    monkeypatch.setattr("httpx.Client.send", fail)
    m = dossier[1]
    checked = audit_issuer(dossier[0], m["base_snapshot_id"], m["reference_id"], "FIXTURE")
    assert checked == report | {"report_sha256": digest}
    _, rows = read_snapshot(m["base_snapshot_id"], "FIXTURE")
    assert all(r.security_id is None and r.security_type == "unknown" for r in rows)


@pytest.mark.parametrize(
    "key,value",
    [
        ("filename", "../outside.txt"),
        ("filename", "C:\\outside.txt"),
        ("filename", "dossier.json"),
        ("sha256", "0" * 64),
        ("bytes", 1),
        ("bytes", True),
        ("bytes", MAX_DOCUMENT + 1),
        ("source_url", "https://secret@issuer.example.org/report"),
        ("source_url", "https://issuer.example.org/report?token=PRIVATE"),
        ("source_url", "http://issuer.example.org/report"),
        ("source_url", "https://issuer.example.org:444/report"),
        ("discovered_from", "file:///private"),
        ("retrieved_at", "2999-01-01T00:00:00Z"),
        ("retrieved_at", "2020-01-03"),
        ("published_at", "2020-01-04T00:00:00Z"),
        ("issuer_name", "bad\x00text"),
        ("class_title", "  "),
        ("identity_verified", True),
    ],
)
def test_invalid_document_rejected(dossier, key, value):
    dossier[1]["documents"][0][key] = value
    with pytest.raises((ValueError, OSError)):
        audit(dossier)


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", "future"),
        ("mode", "EXTERNAL_UNVERIFIED"),
        ("ticker", "UNQUERIED"),
        ("candidate_figi", "BBG000TST999"),
        ("unresolved", []),
        ("documents", []),
        ("identity_verified", True),
    ],
)
def test_invalid_dossier_rejected(dossier, key, value):
    dossier[1][key] = value
    with pytest.raises(ValueError):
        audit(dossier)


def test_binding_checked_before_reading_reference(dossier, monkeypatch):
    save(dossier)

    def fail(*args):
        raise AssertionError("Mismatched selection should fail first")

    monkeypatch.setattr("packages.data.issuer.inspect_reference", fail)
    m = dossier[1]
    for base, ref, mode in [
        ("0" * 64, m["reference_id"], "FIXTURE"),
        (m["base_snapshot_id"], "0" * 64, "FIXTURE"),
        (m["base_snapshot_id"], m["reference_id"], "EXTERNAL_UNVERIFIED"),
    ]:
        with pytest.raises(ValueError, match="selection mismatch"):
            audit_issuer(dossier[0], base, ref, mode)


def test_tamper_missing_duplicate_and_resource_limits(dossier):
    bundle, m = dossier
    m["documents"].append(m["documents"][0].copy())
    with pytest.raises(ValueError, match="Duplicate"):
        audit(dossier)
    m["documents"].pop()
    (bundle / "issuer.txt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        audit(dossier)
    (bundle / "issuer.txt").unlink()
    with pytest.raises(OSError):
        audit(dossier)
    (bundle / "issuer.txt").write_bytes(b"x" * (MAX_DOCUMENT + 1))
    with pytest.raises(ValueError, match="size limit"):
        audit(dossier)


def test_conflicting_transcriptions_never_approve(dossier):
    doc = dossier[1]["documents"][0]
    doc.update(ticker="OTHER", exchange="Different exchange", class_title="Preferred stock")
    report = audit(dossier)
    assert report["documents"][0]["ticker_text_agrees"] is False
    assert report["identity_promotions"] == 0 and report["disposition"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("target", ["document", "manifest", "bundle"])
def test_symlinks_rejected(dossier, tmp_path, target):
    bundle = save(dossier)
    original = bundle / ("issuer.txt" if target == "document" else "dossier.json")
    if target == "bundle":
        original = bundle
    moved = tmp_path / "original"
    original.rename(moved)
    try:
        original.symlink_to(moved, target_is_directory=target == "bundle")
    except OSError:
        pytest.skip("Symlink creation unavailable")
    m = dossier[1]
    with pytest.raises(ValueError, match="Linked"):
        audit_issuer(bundle, m["base_snapshot_id"], m["reference_id"], "FIXTURE")


def test_cli_summary_and_private_error(dossier):
    bundle = save(dossier)
    m = dossier[1]
    args = [
        sys.executable,
        "-m",
        "packages.cli",
        "audit-issuer",
        "--bundle",
        str(bundle),
        "--snapshot",
        m["base_snapshot_id"],
        "--reference",
        m["reference_id"],
        "--mode",
        "FIXTURE",
    ]
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    summary = json.loads(result.stdout)
    assert summary["document_count"] == 1 and summary["identity_promotions"] == 0
    assert "Fictional" not in result.stdout and "documents" not in summary
    m["documents"][0]["source_url"] = "https://issuer.example.org/?token=PRIVATE"
    save(dossier)
    failed = subprocess.run(args, capture_output=True, text=True)
    assert failed.returncode == 2 and "raw details suppressed" in failed.stderr
    assert "PRIVATE" not in failed.stderr + failed.stdout
