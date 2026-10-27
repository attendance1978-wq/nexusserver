"""Server configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 8000
    backlog: int = 128
    max_workers: int = 16
    max_request_size: int = 16 * 1024 * 1024  # 16 MiB (request body)
    max_header_size: int = 64 * 1024  # 64 KiB (request line + headers)
    read_timeout: float = 30.0
    request_timeout: float = 30.0
    keep_alive: bool = False  # reserved: every connection is currently closed after one response
    keep_alive_timeout: float = 5.0
    reload: bool = False  # reserved: auto-reload is not implemented yet
    debug: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
