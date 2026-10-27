"""SQLite-backed notes, the simple version.

Run:  python -m nexusserver examples.database_app:app
Try:  curl -X POST localhost:8000/notes -d '{"body": "remember the milk"}'
      curl localhost:8000/notes
"""

import threading

from nexusserver import Application, BadRequest
from nexusserver.database import connect
from nexusserver.database.query import to_dicts

app = Application()
db = connect(":memory:")
db.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
db.commit()
db_lock = threading.Lock()


@app.get("/notes")
def list_notes():
    with db_lock:
        rows = db.execute("SELECT id, body FROM notes ORDER BY id").fetchall()
    return {"notes": to_dicts(rows)}


@app.post("/notes")
def create_note(request):
    body = (request.json() or {}).get("body", "").strip()
    if not body:
        raise BadRequest("'body' must not be empty")
    with db_lock:
        cur = db.execute("INSERT INTO notes (body) VALUES (?)", (body,))
        db.commit()
    return {"id": cur.lastrowid, "body": body}, 201


if __name__ == "__main__":
    app.run()
