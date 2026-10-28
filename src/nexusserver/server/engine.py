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
from .connection import ClientClosed, Connection
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
        self._active: set[socket.socket] = set()
        self._active_lock = threading.Lock()

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
            self._close_active()
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
        self._close_active()

    def _close_active(self) -> None:
        """Wake workers blocked on idle keep-alive connections."""
        with self._active_lock:
            for sock in list(self._active):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def _handle_client(self, sock: socket.socket, address: tuple[str, int]) -> None:
        conn = Connection(sock, address, timeout=self.config.read_timeout)
        with self._active_lock:
            self._active.add(sock)
        try:
            served = 0
            while not self._stop_event.is_set():
                keep_alive = self._serve_one(conn, address, first=served == 0, served=served)
                served += 1
                if not keep_alive:
                    break
        finally:
            with self._active_lock:
                self._active.discard(sock)
            conn.close()

    def _serve_one(self, conn: Connection, address: tuple[str, int], first: bool, served: int) -> bool:
        """Handle one request on ``conn``. Returns True if the connection may be reused."""
        cfg = self.config
        request: Request | None = None
        keep_alive = False
        conn.set_timeout(cfg.read_timeout if first else cfg.keep_alive_timeout)
        try:
            raw = conn.recv_request(cfg.max_header_size, cfg.max_request_size)
            conn.set_timeout(cfg.read_timeout)
            request = parse_request(raw, client=address, max_body_size=cfg.max_request_size)
            response = self.handler(request)
            keep_alive = (
                cfg.keep_alive
                and served + 1 < cfg.max_keepalive_requests
                and self._wants_keep_alive(request)
                and not self._stop_event.is_set()
            )
        except ClientClosed:
            return False
        except socket.timeout:
            if not first:
                return False  # idle keep-alive connection timed out: close quietly
            response = Response("408 Request Timeout", status_code=408)
        except HTTPError as exc:
            response = Response(f"{exc.status_code} {exc.message}", status_code=exc.status_code,
                                headers=exc.headers)
        except OSError:
            return False
        except Exception:
            logger.exception("Error handling request from %s", address)
            response = Response("500 Internal Server Error", status_code=500)

        try:
            self._write_response(conn.sock, response, request, keep_alive)
        except OSError:
            logger.debug("Client %s went away before the response was sent", address)
            return False
        return keep_alive

    @staticmethod
    def _wants_keep_alive(request: Request) -> bool:
        tokens = {t.strip().lower() for t in request.headers.get("Connection", "").split(",")}
        if request.http_version == "HTTP/1.0":
            return "keep-alive" in tokens
        return "close" not in tokens

    def _write_response(self, sock: socket.socket, response: Response, request: Request | None,
                        keep_alive: bool = False) -> None:
        if "Content-Length" not in response.headers:
            response.headers["Content-Length"] = str(len(response.body))
        response.headers.setdefault("Server", "NexusServer")
        if keep_alive:
            response.headers["Connection"] = "keep-alive"
            response.headers["Keep-Alive"] = f"timeout={int(self.config.keep_alive_timeout)}"
        else:
            response.headers["Connection"] = "close"

        lines = [f"HTTP/1.1 {response.status_code} {response.status_phrase}"]
        lines.extend(f"{name}: {value}" for name, value in response.headers.raw_items())
        head = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")
        no_body = (request is not None and request.method == "HEAD") or response.status_code in (204, 304)
        sock.sendall(head + (b"" if no_body else response.body))
