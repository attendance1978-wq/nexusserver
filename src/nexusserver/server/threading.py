"""Thread-based request execution."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class ThreadPool:
    def __init__(self, max_workers: int = 16) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="nexus")

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    @property
    def name(self) -> str:
        return threading.current_thread().name