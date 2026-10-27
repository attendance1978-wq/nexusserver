"""Security headers."""

from __future__ import annotations

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


DEFAULT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "1; mode=block",
}


class SecurityHeadersMiddleware(BaseMiddleware):
    def __init__(self, app, extra: dict[str, str] | None = None) -> None:
        super().__init__(app)
        self.headers = {**DEFAULT_HEADERS, **(extra or {})}

    def __call__(self, request: Request) -> Response:
        response = self.app(request)
        for name, value in self.headers.items():
            if name not in response.headers:
                response.headers[name] = value
        return response