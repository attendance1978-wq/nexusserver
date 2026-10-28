"""Safe path handling."""

from __future__ import annotations

import re
from pathlib import Path


def safe_join(root: str | Path, relative: str) -> Path:
    """Join ``relative`` onto ``root``; raise ``ValueError`` if the result escapes ``root``."""
    root_path = Path(root).resolve()
    target = (root_path / relative).resolve()
    if root_path not in target.parents and target != root_path:
        raise ValueError(f"Path escapes root: {relative!r}")
    return target


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def secure_filename(filename: str, default: str = "upload") -> str:
    """Reduce a client-supplied file name to a safe basename (no directories, no odd characters)."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = _UNSAFE.sub("_", name).strip("._")
    return name[:120] or default
