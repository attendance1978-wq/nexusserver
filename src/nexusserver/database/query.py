"""Query helpers."""

from __future__ import annotations

from typing import Any


def to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]