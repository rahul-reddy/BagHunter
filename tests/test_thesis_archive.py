"""Offline dossier persistence never certifies narrative, critique or investment evidence."""

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from packages.data.run_archive import write_integrity
from packages.data.thesis_archive import import_thesis


@pytest.fixture
def dossier(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "a" * 16
    root = tmp_path / "data/fixture/latest"
    folder = root / "runs" / run_id
    folder.mkdir(parents=True)
    sources = [{"sha256": "b" * 64, "source_id": "fixture-v1"}]
    candidate = {"security_id": "fx-compound", "evidence": [{"source_id": "fixture-v1"}]}
    run = {
        "run_id": run_id,
        "mode": "FIXTURE",
        "sources": sources,
        "asof": "2022-01-03T23:00:00+00:00",
        "signals": [candidate],
    }
    (folder / "run.json").write_text(json.dumps(run), encoding="utf-8")
    write_integrity(folder)
    (root / "CURRENT").write_text(run_id, encoding="utf-8")
    data = {
        "schema": "fixture-thesis-dossier-v2",
        "mode": "FIXTURE_USER_ASSUMPTIONS",
        "verified_real_theses": 0,
        "source_context": {
            "mode": "FIXTURE",
            "run_id": run_id,
            "security_id": "fx-compound",
            "source_sha256s": ["b" * 64],
        },
        "asof": run["asof"],
        "sources": sources,
        "candidate": candidate,
        "assumptions": {
            "revenue": "100000000",
            "shares": "10000000",
            "net_debt": "0",
            "reference_price": "10",
            "years": "3",
            "dilution": ".02",
            "growth": ".1",
            "margin": ".15",
            "multiple": "15",
        },
        "research_workspace": {
            "research_asof": "2026-10-28T00:00:00Z",
            "qualitative": [],
            "peers": [],
            "critic": {"reviewer": "Unverified person", "counterargument": "Synthetic test"},
        },
        "critic_status": "MATCHED_CLAIM_FROM_OPERATOR",
        "request_digest": "c" * 64,
    }
    path = tmp_path / "dossier.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, root, data


def test_import_persists_canonical_thesis_and_raw_dossier_without_promoting_assertions(dossier):
    path, root, data = dossier
    pointer = (root / "CURRENT").read_bytes()
    run_body = (root / "runs" / ("a" * 16) / "run.json").read_bytes()
    receipt = import_thesis(path, root)
    target = Path("data/research/thesis_assertions/fixture") / receipt["archive_id"]
    table = pq.read_table(target / "thesis.parquet")
    row = table.to_pylist()[0]
    assert table.num_rows == 1 and row["security_id"] == "fx-compound"
    assert row["assertion_status"] == "FIXTURE_UNVERIFIED_OPERATOR_ASSERTIONS_NOT_PREDICTORS"
    review = json.loads(row["adversarial_review"])
    assert review["status"] == "UNVERIFIED_IMPORTED_ATTRIBUTION"
    assert review["claimed_status"] == data["critic_status"]
    assert receipt["critic_independence_verified"] is False
    assert receipt["predictor_promotions"] == receipt["verified_real_theses"] == 0
    assert (target / "dossier.json").read_bytes() == path.read_bytes()
    assert (root / "CURRENT").read_bytes() == pointer
    assert (root / "runs" / ("a" * 16) / "run.json").read_bytes() == run_body
    original = {p.name: p.read_bytes() for p in target.iterdir()}
    assert import_thesis(path, root) == receipt
    assert {p.name: p.read_bytes() for p in target.iterdir()} == original
    assert not list(target.parent.glob(".staging-*"))


@pytest.mark.parametrize(
    "mutation",
    [
        "real",
        "verified",
        "source",
        "candidate",
        "identity",
        "clock",
        "run_id",
        "research_clock",
        "blank",
        "nan",
        "fractional_years",
        "out_of_bounds",
        "missing_input",
    ],
)
def test_invalid_or_foreign_dossier_never_creates_assertion_archive(dossier, mutation):
    path, root, data = dossier
    if mutation == "real":
        data["mode"] = "EXTERNAL_UNVERIFIED"
    elif mutation == "verified":
        data["verified_real_theses"] = 1
    elif mutation == "source":
        data["source_context"]["source_sha256s"] = ["0" * 64]
    elif mutation == "candidate":
        data["candidate"]["evidence"] = []
    elif mutation == "identity":
        data["source_context"]["security_id"] = "unknown"
    elif mutation == "clock":
        data["asof"] = "2022-01-03T23:00:00"
    elif mutation == "run_id":
        data["source_context"]["run_id"] = "../escape"
    elif mutation == "research_clock":
        data["research_workspace"]["research_asof"] = "2020-01-01T00:00:00Z"
    elif mutation == "blank":
        data["assumptions"]["net_debt"] = ""
    elif mutation == "nan":
        data["assumptions"]["growth"] = "NaN"
    elif mutation == "fractional_years":
        data["assumptions"]["years"] = "1.5"
    elif mutation == "out_of_bounds":
        data["assumptions"]["growth"] = "3"
    else:
        del data["assumptions"]["net_debt"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        import_thesis(path, root)
    assert not Path("data/research/thesis_assertions").exists()


def test_duplicate_json_fields_and_nonfinite_nested_claims_reject(dossier):
    path, root, data = dossier
    path.write_text('{"schema": "one", "schema": "two"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        import_thesis(path, root)
    data["untrusted_claim"] = float("inf")
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        import_thesis(path, root)


def test_corrupt_existing_thesis_is_rejected_without_repair(dossier):
    path, root, _ = dossier
    receipt = import_thesis(path, root)
    target = Path("data/research/thesis_assertions/fixture") / receipt["archive_id"]
    (target / "dossier.json").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        import_thesis(path, root)
    assert (target / "dossier.json").read_bytes() == b"corrupt"


def test_corrupt_run_and_linked_output_cannot_persist(dossier, tmp_path):
    path, root, _ = dossier
    folder = root / "runs" / ("a" * 16)
    original = (folder / "run.json").read_bytes()
    (folder / "run.json").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        import_thesis(path, root)
    assert not Path("data/research/thesis_assertions").exists()
    (folder / "run.json").write_bytes(original)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        Path("data/research").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Host lacks symlink permission; Linux CI exercises link boundary")
    with pytest.raises(ValueError, match="Linked"):
        import_thesis(path, root)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("permanent", [False, True])
def test_transient_publication_lock_retries_and_permanent_lock_leaves_no_partial_archive(
    dossier, monkeypatch, permanent
):
    path, root, _ = dossier
    original = Path.rename
    remaining = 3 if permanent else 2
    pointer = (root / "CURRENT").read_bytes()

    def locked(self, target):
        nonlocal remaining
        if self.name == "assertion" and remaining:
            remaining -= 1
            raise PermissionError("Simulated publication lock")
        return original(self, target)

    monkeypatch.setattr(Path, "rename", locked)
    if permanent:
        with pytest.raises(PermissionError):
            import_thesis(path, root)
        assert list(Path("data/research/thesis_assertions/fixture").iterdir()) == []
    else:
        receipt = import_thesis(path, root)
        target = Path("data/research/thesis_assertions/fixture") / receipt["archive_id"]
        assert (target / "dossier.json").read_bytes() == path.read_bytes()
        assert pq.read_table(target / "thesis.parquet").num_rows == 1
        assert not list(target.parent.glob(".staging-*"))
    assert (root / "CURRENT").read_bytes() == pointer
