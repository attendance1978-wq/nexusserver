"""Client connection handling."""

from __future__ import annotations

import re
import socket

from ..exceptions import HTTPError, PayloadTooLarge

_CONTENT_LENGTH_RE = re.compile(rb"\r\ncontent-length:[ \t]*(\d+)")


class Connection:
    def __init__(self, sock: socket.socket, client: tuple[str, int], timeout: float = 30.0) -> None:
        self.sock = sock
        self.client = client
        self.sock.settimeout(timeout)

    def recv_request(self, max_header_size: int, max_body_size: int) -> bytes:
        """Read one full request (headers plus the whole body per Content-Length)."""
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            if len(buffer) > max_header_size:
                raise HTTPError("Request header section too large", status_code=431)
            chunk = self.sock.recv(65536)
            if not chunk:
                return buffer  # empty => client went away; partial => parser answers 400
            buffer += chunk

        head_end = buffer.find(b"\r\n\r\n")
        if head_end > max_header_size:
            raise HTTPError("Request header section too large", status_code=431)

        head = buffer[:head_end].lower()
        match = _CONTENT_LENGTH_RE.search(head)
        content_length = int(match.group(1)) if match else 0
        if content_length > max_body_size:
            raise PayloadTooLarge("Request body too large")

        needed = head_end + 4 + content_length
        if b"\r\nexpect: 100-continue" in head and len(buffer) < needed:
            self.sock.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        while len(buffer) < needed:
            chunk = self.sock.recv(65536)
            if not chunk:
                break
            buffer += chunk
        return buffer

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
