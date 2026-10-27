"""Session management (in-memory)."""

from __future__ import annotations

import secrets
import threading
from typing import Any

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


class SessionMiddleware(BaseMiddleware):
    """Server-side sessions keyed by a random 256-bit cookie token.

    Data lives in process memory: it is lost on restart and not shared between
    processes. Available as ``request.state["session"]`` (a plain dict).
    """

    def __init__(
        self,
        app,
        cookie_name: str = "nexussession",
        max_age: int | None = None,
        secure: bool = False,
    ) -> None:
        super().__init__(app)
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secure = secure
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> Response:
        token = request.cookies.get(self.cookie_name)
        with self._lock:
            is_new = not token or token not in self._store
            if is_new:
                token = secrets.token_urlsafe(32)
                self._store[token] = {}
            session = self._store[token]

        request.state["session"] = session
        request.state["session_id"] = token
        response = self.app(request)
        if is_new:
            response.set_cookie(
                self.cookie_name, token, max_age=self.max_age,
                httponly=True, samesite="Lax", secure=self.secure,
            )
        return response
