"""Rate limiting (fixed window, per client)."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


class RateLimitMiddleware(BaseMiddleware):
    """Allow ``limit`` requests per ``window`` seconds per key; answer 429 beyond that.

    The key defaults to the client IP address. ``X-Forwarded-For`` is *not*
    trusted (clients can forge it); behind a reverse proxy pass your own
    ``key_func``. State is in memory and per process.
    """

    def __init__(
        self,
        app,
        limit: int = 100,
        window: float = 60.0,
        key_func: Callable[[Request], str] | None = None,
        exempt_paths: tuple[str, ...] = (),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(app)
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit = limit
        self.window = window
        self.key_func = key_func or (lambda request: request.client[0] if request.client else "-")
        self.exempt_paths = exempt_paths
        self._clock = clock
        self._hits: dict[str, tuple[float, int]] = {}  # key -> (window_start, count)
        self._lock = threading.Lock()
        self._last_purge = clock()

    def _purge(self, now: float) -> None:
        if now - self._last_purge < self.window:
            return
        self._last_purge = now
        for key in [k for k, (start, _) in self._hits.items() if now - start >= self.window]:
            del self._hits[key]

    def __call__(self, request: Request) -> Response:
        if request.path in self.exempt_paths:
            return self.app(request)
        key = self.key_func(request)
        now = self._clock()
        with self._lock:
            self._purge(now)
            start, count = self._hits.get(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0
            count += 1
            self._hits[key] = (start, count)
            remaining = max(0, self.limit - count)
            reset = max(0.0, self.window - (now - start))

        if count > self.limit:
            response = Response("429 Too Many Requests", status_code=429)
            response.headers["Retry-After"] = str(max(1, math.ceil(reset)))
        else:
            response = self.app(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(math.ceil(reset))
        return response
