"""Schema migration utilities."""

from __future__ import annotations

from collections.abc import Iterable


def apply_migrations(conn, migrations: Iterable[str]) -> int:
    """Apply each migration (one SQL statement each) exactly once.

    Migrations are numbered by position (1, 2, 3, ...) and recorded in the
    ``_migrations`` table, so calling this on every start-up is safe. Only ever
    *append* to the list. Returns how many migrations were newly applied.
    """
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (id INTEGER PRIMARY KEY)")
    applied = {row[0] for row in conn.execute("SELECT id FROM _migrations")}
    count = 0
    for index, sql in enumerate(migrations, start=1):
        if index in applied:
            continue
        conn.execute(sql)
        conn.execute("INSERT INTO _migrations (id) VALUES (?)", (index,))
        count += 1
    conn.commit()
    return count
