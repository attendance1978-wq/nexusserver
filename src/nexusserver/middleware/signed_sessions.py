"""Cookie-based sessions signed with HMAC-SHA256."""

from __future__ import annotations

import json
from typing import Any

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response
from ..security import sign, unsign


class SignedSessionMiddleware(BaseMiddleware):
    """Store the session *in the cookie*, tamper-proof but **not encrypted**.

    The client can read (but not modify or forge) the data, so never put secrets
    in it. Works across restarts and multiple processes sharing ``secret_key``.
    Cookies are limited to ~4 KB. Available as ``request.state["session"]``.
    """

    MAX_COOKIE_SIZE = 4000

    def __init__(
        self,
        app,
        secret_key: str | bytes,
        cookie_name: str = "nexussession",
        max_age: int = 14 * 24 * 3600,
        secure: bool = False,
        samesite: str = "Lax",
    ) -> None:
        super().__init__(app)
        if not secret_key or len(secret_key) < 16:
            raise ValueError("secret_key must be at least 16 characters; generate one with secrets.token_hex(32)")
        self.secret_key = secret_key
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secure = secure
        self.samesite = samesite

    def _load(self, request: Request) -> dict[str, Any]:
        token = request.cookies.get(self.cookie_name)
        if not token:
            return {}
        raw = unsign(token, self.secret_key, max_age=self.max_age)
        if raw is None:
            return {}
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def __call__(self, request: Request) -> Response:
        session = self._load(request)
        before = json.dumps(session, sort_keys=True)
        request.state["session"] = session
        response = self.app(request)

        after = json.dumps(request.state["session"], sort_keys=True)
        if after != before:
            if not request.state["session"]:
                response.delete_cookie(self.cookie_name)
            else:
                token = sign(after.encode("utf-8"), self.secret_key)
                if len(token) > self.MAX_COOKIE_SIZE:
                    raise ValueError("Session data is too large for a cookie")
                response.set_cookie(
                    self.cookie_name, token, max_age=self.max_age,
                    httponly=True, samesite=self.samesite, secure=self.secure,
                )
        return response
