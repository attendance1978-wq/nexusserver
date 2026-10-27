"""Request worker management."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Worker:
    def __init__(self, task: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.task = task
        self.args = args
        self.kwargs = kwargs

    def run(self) -> Any:
        return self.task(*self.args, **self.kwargs)