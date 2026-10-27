"""Middleware interface."""

from __future__ import annotations

from collections.abc import Callable

from ..http.request import Request
from ..http.response import Response


Handler = Callable[[Request], Response]


class BaseMiddleware:
    def __init__(self, app: Callable[[Request], Response]) -> None:
        self.app = app

    def __call__(self, request: Request) -> Response:
        return self.app(request)