"""TCP socket management."""

from __future__ import annotations

import socket


def create_listener(host: str, port: int, backlog: int = 128) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(backlog)
    return sock