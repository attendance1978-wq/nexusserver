"""Client connection handling (buffered, supports keep-alive)."""

from __future__ import annotations

import re
import socket

from ..exceptions import BadRequest, HTTPError, PayloadTooLarge
from ..http.chunked import dechunk

_CONTENT_LENGTH_RE = re.compile(rb"\r\ncontent-length:[ \t]*(\d+)")
_CHUNKED_RE = re.compile(rb"\r\ntransfer-encoding:[ \t]*chunked", re.IGNORECASE)


class ClientClosed(Exception):
    """The peer closed the connection cleanly between requests."""


class Connection:
    def __init__(self, sock: socket.socket, client: tuple[str, int], timeout: float = 30.0) -> None:
        self.sock = sock
        self.client = client
        self.sock.settimeout(timeout)
        self._buffer = b""

    def set_timeout(self, timeout: float) -> None:
        self.sock.settimeout(timeout)

    def _fill(self) -> bool:
        chunk = self.sock.recv(65536)
        if not chunk:
            return False
        self._buffer += chunk
        return True

    def recv_request(self, max_header_size: int, max_body_size: int) -> bytes:
        """Read exactly one request from the stream; leftover bytes (pipelining) stay buffered.

        Raises ``ClientClosed`` if the peer closed before sending anything.
        """
        while b"\r\n\r\n" not in self._buffer:
            if len(self._buffer) > max_header_size:
                raise HTTPError("Request header section too large", status_code=431)
            if not self._fill():
                if not self._buffer.strip():
                    raise ClientClosed()
                raw, self._buffer = self._buffer, b""
                return raw  # partial: parser answers 400

        head_end = self._buffer.find(b"\r\n\r\n")
        if head_end > max_header_size:
            raise HTTPError("Request header section too large", status_code=431)
        head = self._buffer[:head_end]
        body_start = head_end + 4

        if _CHUNKED_RE.search(head):
            return self._read_chunked(body_start, max_body_size)

        match = _CONTENT_LENGTH_RE.search(head.lower())
        content_length = int(match.group(1)) if match else 0
        if content_length > max_body_size:
            raise PayloadTooLarge("Request body too large")

        needed = body_start + content_length
        if b"\r\nexpect: 100-continue" in head.lower() and len(self._buffer) < needed:
            self.sock.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        while len(self._buffer) < needed:
            if not self._fill():
                break
        raw, self._buffer = self._buffer[:needed], self._buffer[needed:]
        return raw

    def _read_chunked(self, body_start: int, max_body_size: int) -> bytes:
        if b"\r\nexpect: 100-continue" in self._buffer[:body_start].lower():
            self.sock.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        while True:
            result = dechunk(self._buffer[body_start:], max_body_size)
            if result is not None:
                consumed = body_start + result[1]
                raw, self._buffer = self._buffer[:consumed], self._buffer[consumed:]
                return raw
            if not self._fill():
                raise BadRequest("Incomplete chunked body")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
