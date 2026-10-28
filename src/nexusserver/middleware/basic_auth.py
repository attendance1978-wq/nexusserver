"""HTTP Basic authentication."""

from __future__ import annotations

import base64
import binascii
import hmac
from collections.abc import Callable, Mapping

from .base import BaseMiddleware
from ..http.request import Request
from ..http.response import Response
from ..security import verify_password

_DUMMY_HASH = "scrypt$16384$8$1$AAAAAAAAAAAAAAAAAAAAAA$" + "A" * 43


class BasicAuthMiddleware(BaseMiddleware):
    """Require ``Authorization: Basic ...`` for every path except ``exempt_paths``.

    Provide either ``users`` (username -> hash from ``nexusserver.security.hash_password``)
    or ``verify(username, password) -> bool``. On success ``request.state["user"]``
    is the username. Basic auth sends credentials on every request: use HTTPS.
    """

    def __init__(
        self,
        app,
        users: Mapping[str, str] | None = None,
        verify: Callable[[str, str], bool] | None = None,
        realm: str = "Restricted",
        exempt_paths: tuple[str, ...] = (),
    ) -> None:
        super().__init__(app)
        if (users is None) == (verify is None):
            raise ValueError("Pass exactly one of 'users' or 'verify'")
        self._users = dict(users) if users is not None else None
        self._verify = verify
        self.realm = realm.replace('"', "")
        self.exempt_paths = exempt_paths

    def _check(self, username: str, password: str) -> bool:
        if self._verify is not None:
            return bool(self._verify(username, password))
        stored = self._users.get(username)
        if stored is None:
            verify_password(password, _DUMMY_HASH)  # keep timing similar for unknown users
            return False
        return verify_password(password, stored)

    def _challenge(self) -> Response:
        response = Response("401 Unauthorized", status_code=401)
        response.headers["WWW-Authenticate"] = f'Basic realm="{self.realm}", charset="UTF-8"'
        return response

    def __call__(self, request: Request) -> Response:
        if request.path in self.exempt_paths:
            return self.app(request)
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "basic" or not token:
            return self._challenge()
        try:
            decoded = base64.b64decode(token.strip(), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return self._challenge()
        username, sep, password = decoded.partition(":")
        if not sep or not self._check(username, password):
            return self._challenge()
        request.state["user"] = username
        return self.app(request)
