"""Optional response compression."""

from __future__ import annotations

import gzip

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


class GZipMiddleware(BaseMiddleware):
    def __init__(self, app, minimum_size: int = 500) -> None:
        super().__init__(app)
        self.minimum_size = minimum_size

    def __call__(self, request: Request) -> Response:
        response = self.app(request)
        accept = request.headers.get("Accept-Encoding", "")
        if (
            "gzip" in accept
            and len(response.body) >= self.minimum_size
            and "Content-Encoding" not in response.headers
        ):
            compressed = gzip.compress(response.body)
            response.body = compressed
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed))
            response.headers.add("Vary", "Accept-Encoding")
        return response