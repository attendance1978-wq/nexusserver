"""Input validation helpers."""

from __future__ import annotations

from typing import Any

from ..exceptions import BadRequest


def require_fields(data: dict[str, Any], fields: list[str]) -> None:
    missing = [f for f in fields if f not in data]
    if missing:
        raise BadRequest(f"Missing required fields: {', '.join(missing)}")


def as_int(value: Any, default: int | None = None) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        if default is not None:
            return default
        raise BadRequest(f"Invalid integer: {value!r}")