"""Execute the repository's fixture notebook without a notebook-server dependency."""

import contextlib
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    notebook = ROOT / "notebooks/fixture_research.ipynb"
    body = notebook.read_bytes()
    destination = ROOT / "artifacts/test_results"
    destination.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "status": "RUNNING",
        "notebook_sha256": hashlib.sha256(body).hexdigest(),
        "scope": "SYNTHETIC_FIXTURE_NOT_EMPIRICAL_RESEARCH",
    }
    # Only the fixed, trusted repository notebook is executable. No supplied paths/uploads.
    namespace: dict[str, Any] = {"__name__": "baghunter_fixture_notebook"}
    transcript = io.StringIO()
    executions = []
    started = time.perf_counter()
    prior_directory = Path.cwd()
    try:
        document = json.loads(body)
        if document["nbformat"] != 4 or not 1 <= len(document["cells"]) <= 50:
            raise ValueError("Unsupported repository notebook")
        ids = [cell["id"] for cell in document["cells"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate notebook cell IDs")
        os.chdir(ROOT)
        with contextlib.redirect_stdout(transcript):
            for cell in document["cells"]:
                if cell["cell_type"] != "code":
                    continue
                source = "".join(cell["source"])
                before = time.perf_counter()
                exec(compile(source, f"{notebook.name}:{cell['id']}", "exec"), namespace)
                executions.append({"cell": cell["id"], "seconds": time.perf_counter() - before})
        research = namespace["research"]
        receipt.update(
            status="PASS",
            lockfile_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            python=sys.version.split()[0],
            run_id=research["run_id"],
            source_sha256=research["sources"][0]["sha256"],
            code_sha256=research["code_sha256"],
            verified_real_theses=0,
        )
    except BaseException as exc:
        receipt.update(status="FAILED_OR_INTERRUPTED", error_type=type(exc).__name__)
        raise
    finally:
        os.chdir(prior_directory)
        receipt.update(cells=executions, elapsed_seconds=time.perf_counter() - started)
        (destination / "notebook-transcript.txt").write_text(
            transcript.getvalue(), encoding="utf-8"
        )
        (destination / "notebook-execution.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(receipt, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
