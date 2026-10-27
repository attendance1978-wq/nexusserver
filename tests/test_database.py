from nexusserver.database import connect
from nexusserver.database.migrations import apply_migrations
from nexusserver.database.query import to_dicts

MIGRATIONS = [
    "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)",
    "ALTER TABLE notes ADD COLUMN pinned INTEGER DEFAULT 0",
]


def test_migrations_apply_once():
    db = connect(":memory:")
    assert apply_migrations(db, MIGRATIONS) == 2
    assert apply_migrations(db, MIGRATIONS) == 0  # re-running is a no-op


def test_new_migrations_are_picked_up():
    db = connect(":memory:")
    apply_migrations(db, MIGRATIONS[:1])
    assert apply_migrations(db, MIGRATIONS) == 1


def test_rows_to_dicts():
    db = connect(":memory:")
    apply_migrations(db, MIGRATIONS)
    db.execute("INSERT INTO notes (body) VALUES ('hi')")
    assert to_dicts(db.execute("SELECT id, body FROM notes").fetchall()) == [{"id": 1, "body": "hi"}]
