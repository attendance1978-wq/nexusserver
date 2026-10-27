"""Safe path handling."""

from __future__ import annotations

from pathlib import Path


def safe_join(root: str | Path, relative: str) -> Path:
    root_path = Path(root).resolve()
    target = (root_path / relative).resolve()
    if root_path not in target.parents and target != root_path:
        raise ValueError(f"Path escapes root: {relative!r}")
    return target