"""Database connection management."""

from __future__ import annotations

from typing import Any, Protocol


class Connection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...