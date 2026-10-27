"""URL matching and dispatch."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..exceptions import MethodNotAllowed, NotFound
from ..http.request import Request
from ..http.response import Response
from .parameters import extract_params
from .routes import Handler, Route


class Router:
    def __init__(self) -> None:
        self._routes: list[Route] = []
        self._named: dict[str, Route] = {}

    def add_route(
        self,
        path: str,
        endpoint: Handler,
        methods: Iterable[str] | None = None,
        name: str | None = None,
    ) -> Route:
        route = Route(path=path, endpoint=endpoint, methods=set(methods or {"GET"}), name=name)
        self._routes.append(route)
        if name:
            self._named[name] = route
        return route

    def route(
        self,
        path: str,
        methods: Iterable[str] | None = None,
        name: str | None = None,
    ) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            self.add_route(path, func, methods=methods, name=name)
            return func

        return decorator

    def get(self, path: str, **kwargs) -> Callable[[Handler], Handler]:
        return self.route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs) -> Callable[[Handler], Handler]:
        return self.route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs) -> Callable[[Handler], Handler]:
        return self.route(path, methods=["PUT"], **kwargs)

    def delete(self, path: str, **kwargs) -> Callable[[Handler], Handler]:
        return self.route(path, methods=["DELETE"], **kwargs)

    def resolve(self, request: Request) -> tuple[Handler, dict[str, Any]]:
        path_matched = False
        allowed: set[str] = set()
        for route in self._routes:
            if route.matches(request.path):
                path_matched = True
                is_head_of_get = request.method == "HEAD" and "GET" in route.methods
                if request.method in route.methods or is_head_of_get:
                    params = extract_params(route.regex, route.params, request.path)
                    return route.endpoint, params
                allowed.update(route.methods)
        if path_matched:
            raise MethodNotAllowed(
                f"{request.method} not allowed; allowed: {sorted(allowed)}",
                headers={"Allow": ", ".join(sorted(allowed))},
            )
        raise NotFound(f"No route for {request.path}")

    @property
    def routes(self) -> list[Route]:
        return list(self._routes)