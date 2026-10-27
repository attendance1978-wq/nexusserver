"""Access logging middleware."""

from __future__ import annotations

import logging
import time

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


logger = logging.getLogger("nexusserver.access")


class RequestLogMiddleware(BaseMiddleware):
    def __call__(self, request: Request) -> Response:
        start = time.perf_counter()
        try:
            response = self.app(request)
            status = response.status_code
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            client = request.client[0] if request.client else "-"
            logger.exception("%s %s %s 500 %.1fms", client, request.method, request.path, elapsed)
            raise
        elapsed = (time.perf_counter() - start) * 1000
        client = request.client[0] if request.client else "-"
        logger.info("%s %s %s %d %.1fms", client, request.method, request.path, status, elapsed)
        return response