# Database

NexusServer ships a thin helper over the standard-library `sqlite3`.

```python
from nexusserver.database import connect

db = connect("app.db")          # or ":memory:"
db.execute("INSERT INTO notes (body) VALUES (?)", ("hello",))
db.commit()
rows = db.execute("SELECT id, body FROM notes").fetchall()
```

`connect()` returns a `sqlite3.Connection` with `row_factory = sqlite3.Row`
(`row["body"]`, `dict(row)`) and foreign keys enabled. Always use `?`
placeholders, never string formatting.

```python
from nexusserver.database.query import to_dicts
to_dicts(rows)                  # [{"id": 1, "body": "hello"}]
```

## Migrations

```python
from nexusserver.database.migrations import apply_migrations

MIGRATIONS = [
    "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)",
    "ALTER TABLE notes ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",
]

@app.on_startup
def setup():
    apply_migrations(db, MIGRATIONS)
```

Each entry is one SQL statement, numbered by position and recorded in the
`_migrations` table, so it is safe to call on every start. **Only append** to the
list: never edit or reorder entries that have already been applied.
`apply_migrations` returns the number of newly applied migrations.

## Threading

Requests run on a thread pool and the connection is shared
(`check_same_thread=False`). Guard use with a `threading.Lock` (as `examples/notes_api.py`
does), or open a connection per request for heavier workloads.

## Lifecycle

Open the connection in `@app.on_startup` and close it in `@app.on_shutdown`.
