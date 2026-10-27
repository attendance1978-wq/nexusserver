"""Main application and server lifecycle."""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

from ._version import __version__
from .config import Config
from .exceptions import HTTPError, InternalServerError
from .http.request import Request
from .http.response import Response
from .middleware.request_log import RequestLogMiddleware
from .middleware.security import SecurityHeadersMiddleware
from .routing.router import Router
from .server.engine import HTTPEngine
from .server.lifecycle import Lifecycle

logger = logging.getLogger("nexusserver")


Handler = Callable[[Request], Response]


class Application:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.router = Router()
        self.lifecycle = Lifecycle()
        self._middleware: list[Callable[[Callable], Callable]] = []
        self._built: Handler | None = None
        self._engine: HTTPEngine | None = None

        # Default middleware (outermost first): security headers, request logging
        self.add_middleware(SecurityHeadersMiddleware)
        self.add_middleware(RequestLogMiddleware)

    # ----- routing shortcuts -----
    def route(self, path: str, methods=None, name: str | None = None):
        return self.router.route(path, methods=methods, name=name)

    def get(self, path: str, **kwargs):
        return self.router.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.router.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.router.put(path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.router.delete(path, **kwargs)

    # ----- lifecycle hooks -----
    def on_startup(self, func: Callable[[], Any]) -> Callable[[], Any]:
        return self.lifecycle.on_startup(func)

    def on_shutdown(self, func: Callable[[], Any]) -> Callable[[], Any]:
        return self.lifecycle.on_shutdown(func)

    # ----- middleware -----
    def add_middleware(self, middleware_cls: Callable[..., Callable], **options: Any) -> None:
        """Register middleware. Keyword ``options`` are passed to its constructor.

        Middleware added first is outermost (sees the request first and the
        response last).
        """
        if options:
            middleware_cls = functools.partial(middleware_cls, **options)
        self._middleware.append(middleware_cls)
        self._built = None  # rebuild the chain on next use

    def _build_handler(self) -> Handler:
        def endpoint(request: Request) -> Response:
            try:
                handler, params = self.router.resolve(request)
                request.path_params = params
                return self._invoke(handler, request)
            except HTTPError as exc:
                return self._error_response(exc)
            except Exception as exc:
                logger.exception("Unhandled error in %s %s", request.method, request.path)
                detail = f"{type(exc).__name__}: {exc}" if self.config.debug else None
                return self._error_response(InternalServerError(detail))

        handler: Handler = endpoint
        for middleware_cls in reversed(self._middleware):
            handler = middleware_cls(handler)
        return handler

    def _invoke(self, handler: Callable, request: Request) -> Response:
        signature = inspect.signature(handler)
        kwargs: dict[str, Any] = {}
        if "request" in signature.parameters:
            kwargs["request"] = request
        for name, value in request.path_params.items():
            if name in signature.parameters:
                kwargs[name] = value
        return self._to_response(handler(**kwargs))

    @staticmethod
    def _to_response(result: Any) -> Response:
        """Normalise a handler's return value.

        Accepted: ``Response``; ``dict``/``list`` (JSON); ``str``; ``bytes``;
        ``None`` (empty body); or a tuple ``(body, status)`` /
        ``(body, status, headers)`` where body is any of the above.
        """
        status, headers = 200, None
        body = result
        if isinstance(result, tuple):
            if not 1 <= len(result) <= 3:
                raise InternalServerError("Handler returned a malformed tuple")
            body = result[0]
            status = int(result[1]) if len(result) > 1 else 200
            headers = result[2] if len(result) > 2 else None

        if isinstance(body, Response):
            if len(result if isinstance(result, tuple) else ()) > 1:
                body.status_code = status
            return body
        if isinstance(body, (dict, list)):
            return Response.json(body, status_code=status, headers=headers)
        if body is None:
            return Response(b"", status_code=status, headers=headers)
        if isinstance(body, (bytes, bytearray)):
            return Response(bytes(body), status_code=status, headers=headers,
                            content_type="application/octet-stream")
        return Response(str(body), status_code=status, headers=headers)

    def _error_response(self, exc: HTTPError) -> Response:
        return Response(
            body=f"{exc.status_code} {exc.message}".encode("utf-8"),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    def handle(self, request: Request) -> Response:
        """Run a request through middleware and routing (handy for tests)."""
        if self._built is None:
            self._built = self._build_handler()
        return self._built(request)

    # ----- lifecycle -----
    def run(self) -> None:
        logging.basicConfig(level=logging.DEBUG if self.config.debug else logging.INFO)
        if self.config.reload:
            logger.warning("Auto-reload is not implemented yet; restart the server to pick up changes.")
        logger.info("NexusServer %s", __version__)
        self.lifecycle.startup()
        self._engine = HTTPEngine(self.handle, self.config)
        try:
            self._engine.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.lifecycle.shutdown()

    def stop(self) -> None:
        if self._engine is not None:
            self._engine.stop()


# Alias
NexusServer = Application
