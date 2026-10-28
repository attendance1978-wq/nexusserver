"""Bearer token authentication."""

from __future__ import annotations

import hmac

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response


class BearerTokenMiddleware(BaseMiddleware):
    """Require ``Authorization: Bearer <token>`` (compared in constant time).

    ``token`` may be a string or several strings (to rotate tokens). Paths in
    ``exempt_paths`` are open. Use HTTPS (or loopback only): tokens travel in clear text.
    """

    def __init__(self, app, token: str | list[str] | tuple[str, ...], exempt_paths: tuple[str, ...] = (),
                 realm: str = "api") -> None:
        super().__init__(app)
        tokens = [token] if isinstance(token, str) else list(token)
        if not tokens or any(len(t) < 16 for t in tokens):
            raise ValueError("Bearer tokens must be at least 16 characters long")
        self._tokens = [t.encode("utf-8") for t in tokens]
        self.exempt_paths = exempt_paths
        self.realm = realm.replace('"', "")

    def _valid(self, presented: str) -> bool:
        candidate = presented.encode("utf-8")
        ok = False
        for token in self._tokens:  # check all, so timing does not reveal which matched
            ok |= hmac.compare_digest(candidate, token)
        return ok

    def __call__(self, request: Request) -> Response:
        if request.path in self.exempt_paths:
            return self.app(request)
        scheme, _, presented = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not presented.strip() or not self._valid(presented.strip()):
            response = Response("401 Unauthorized", status_code=401)
            response.headers["WWW-Authenticate"] = f'Bearer realm="{self.realm}"'
            return response
        return self.app(request)
