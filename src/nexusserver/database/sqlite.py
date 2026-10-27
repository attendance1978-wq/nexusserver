"""Standard-library SQLite support."""

from __future__ import annotations

import sqlite3


def connect(path: str) -> sqlite3.Connection:
    """Open a SQLite connection with ``sqlite3.Row`` rows and foreign keys on.

    The connection may be used from worker threads (``check_same_thread=False``);
    guard writes with a ``threading.Lock`` if several requests can write at once.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
