"""Cross-origin request policies."""

from __future__ import annotations

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


class CORSMiddleware(BaseMiddleware):
    def __init__(
        self,
        app,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = False,
        max_age: int = 600,
    ) -> None:
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def _allowed_origin(self, origin: str) -> str | None:
        if "*" in self.allow_origins:
            return "*" if not self.allow_credentials else origin
        if origin in self.allow_origins:
            return origin
        return None

    def __call__(self, request: Request) -> Response:
        origin = request.headers.get("Origin", "")
        if request.method == "OPTIONS" and origin:
            response = Response(b"", status_code=204)
        else:
            response = self.app(request)

        allowed = self._allowed_origin(origin) if origin else None
        if allowed:
            response.headers["Access-Control-Allow-Origin"] = allowed
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Max-Age"] = str(self.max_age)
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response