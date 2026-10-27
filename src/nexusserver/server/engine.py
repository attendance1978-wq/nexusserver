"""HTTP server startup and shutdown."""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable

from ..config import Config
from ..exceptions import HTTPError
from ..http.parser import parse_request
from ..http.request import Request
from ..http.response import Response
from .connection import Connection
from .sockets import create_listener
from .threading import ThreadPool


logger = logging.getLogger("nexusserver.server")

Handler = Callable[[Request], Response]


class HTTPEngine:
    def __init__(self, handler: Handler, config: Config) -> None:
        self.handler = handler
        self.config = config
        self.ready = threading.Event()  # set once the socket is listening
        self._listener: socket.socket | None = None
        self._pool = ThreadPool(max_workers=config.max_workers)
        self._stop_event = threading.Event()

    @property
    def address(self) -> tuple[str, int]:
        """The bound ``(host, port)`` (useful with ``port=0``). Valid once ``ready`` is set."""
        if self._listener is None:
            raise RuntimeError("Server is not listening yet")
        return self._listener.getsockname()[:2]

    def start(self) -> None:
        self._listener = create_listener(self.config.host, self.config.port, self.config.backlog)
        host, port = self.address
        logger.info("Listening on http://%s:%d", host, port)
        self.ready.set()
        try:
            while not self._stop_event.is_set():
                try:
                    client_sock, address = self._listener.accept()
                except OSError:
                    break
                self._pool.submit(self._handle_client, client_sock, address)
        finally:
            self._pool.shutdown(wait=True)
            if self._listener is not None:
                self._listener.close()

    def stop(self) -> None:
        self._stop_event.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass

    def _handle_client(self, sock: socket.socket, address: tuple[str, int]) -> None:
        conn = Connection(sock, address, timeout=self.config.read_timeout)
        request: Request | None = None
        try:
            raw = conn.recv_request(self.config.max_header_size, self.config.max_request_size)
            if not raw:
                return
            request = parse_request(raw, client=address, max_body_size=self.config.max_request_size)
            response = self.handler(request)
        except HTTPError as exc:
            response = Response(f"{exc.status_code} {exc.message}", status_code=exc.status_code,
                                headers=exc.headers)
        except socket.timeout:
            response = Response("408 Request Timeout", status_code=408)
        except Exception:
            logger.exception("Error handling request from %s", address)
            response = Response("500 Internal Server Error", status_code=500)

        try:
            self._write_response(conn.sock, response, request)
        except OSError:
            logger.debug("Client %s went away before the response was sent", address)
        finally:
            conn.close()

    def _write_response(self, sock: socket.socket, response: Response, request: Request | None) -> None:
        if "Content-Length" not in response.headers:
            response.headers["Content-Length"] = str(len(response.body))
        response.headers.setdefault("Server", "NexusServer")
        response.headers["Connection"] = "close"

        lines = [f"HTTP/1.1 {response.status_code} {response.status_phrase}"]
        lines.extend(f"{name}: {value}" for name, value in response.headers.raw_items())
        head = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")
        body = b"" if request is not None and request.method == "HEAD" else response.body
        sock.sendall(head + body)
