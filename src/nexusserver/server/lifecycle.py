"""Startup and shutdown hooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Lifecycle:
    def __init__(self) -> None:
        self._on_startup: list[Callable[[], Any]] = []
        self._on_shutdown: list[Callable[[], Any]] = []

    def on_startup(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self._on_startup.append(func)
        return func

    def on_shutdown(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self._on_shutdown.append(func)
        return func

    def startup(self) -> None:
        for func in self._on_startup:
            func()

    def shutdown(self) -> None:
        for func in reversed(self._on_shutdown):
            func()