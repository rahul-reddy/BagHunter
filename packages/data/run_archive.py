"""Checksum manifests for generated local run archives; integrity is not publisher authenticity."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from packages.data.finviz import _json, _read


def write_integrity(folder: Path) -> None:
    files = {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }
    (folder / "integrity.json").write_bytes(_json({"version": 1, "files": files}))


def verify_integrity(folder: Path, only: str | None = None) -> None:
    if folder.is_symlink() or folder.is_junction() or (folder / "integrity.json").is_symlink():
        raise ValueError("Linked run archive")
    manifest = json.loads(_read(folder / "integrity.json", 64 * 1024))
    files = manifest["files"]
    if manifest["version"] != 1 or not isinstance(files, dict) or not 1 <= len(files) <= 100:
        raise ValueError("Invalid run integrity manifest")
    if "run.json" not in files or (only is not None and only not in files):
        raise ValueError("Missing run integrity entry")
    for name, digest in files.items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or any(p in ("..", ".") for p in relative.parts)
            or "\\" in name
            or ":" in name
            or not re.fullmatch(r"[a-f0-9]{64}", digest)
        ):
            raise ValueError("Invalid run integrity path or digest")
        if only is not None and name != only:
            continue
        path = folder / name
        if not path.resolve().is_relative_to(folder.resolve()) or path.is_symlink():
            raise ValueError("Run integrity path escapes archive")
        if hashlib.sha256(_read(path, 20 * 1024 * 1024)).hexdigest() != digest:
            raise ValueError("Run archive checksum mismatch")
