"""Flagship example: SQLite + migrations + lifecycle hooks + validation + CORS.

Run:  python -m nexusserver examples.notes_api:app --port 8080
Try:  curl -X POST localhost:8080/notes -d '{"title": "Hi", "body": "First note"}'
      curl localhost:8080/notes?limit=10
      curl -X DELETE localhost:8080/notes/1
The database file notes.db is created in the working directory.
"""

import threading

from nexusserver import Application, BadRequest, NotFound
from nexusserver.database import connect
from nexusserver.database.migrations import apply_migrations
from nexusserver.database.query import to_dicts
from nexusserver.middleware import CORSMiddleware
from nexusserver.utils.validation import as_int, require_fields

# Append-only: never edit or reorder old entries.
MIGRATIONS = [
    "CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '')",
    "ALTER TABLE notes ADD COLUMN created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
]

app = Application()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])

db = None
db_lock = threading.Lock()


@app.on_startup
def open_database():
    global db
    db = connect("notes.db")
    apply_migrations(db, MIGRATIONS)


@app.on_shutdown
def close_database():
    if db is not None:
        db.close()


@app.get("/notes")
def list_notes(request):
    limit = max(1, min(as_int(request.query.get("limit"), default=20), 100))
    with db_lock:
        rows = db.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"notes": to_dicts(rows)}


@app.get("/notes/<int:note_id>")
def get_note(note_id: int):
    with db_lock:
        row = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if row is None:
        raise NotFound(f"Note {note_id} does not exist")
    return dict(row)


@app.post("/notes")
def create_note(request):
    data = request.json()
    if not isinstance(data, dict):
        raise BadRequest("Expected a JSON object body")
    require_fields(data, ["title"])
    with db_lock:
        cur = db.execute(
            "INSERT INTO notes (title, body) VALUES (?, ?)", (data["title"], data.get("body", ""))
        )
        db.commit()
        row = db.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row), 201


@app.delete("/notes/<int:note_id>")
def delete_note(note_id: int):
    with db_lock:
        cur = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
    if cur.rowcount == 0:
        raise NotFound(f"Note {note_id} does not exist")
    return None, 204


if __name__ == "__main__":
    app.run()
