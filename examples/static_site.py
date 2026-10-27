"""Serve files from ./public safely (no path traversal).

Run (from the project root):  python -m nexusserver examples.static_site:app
Then open http://127.0.0.1:8000/
"""

from pathlib import Path

from nexusserver import Application, NotFound, Response
from nexusserver.utils.mime import guess_mime
from nexusserver.utils.paths import safe_join

app = Application()
ROOT = Path(__file__).resolve().parent / "public"


def _serve(relative: str) -> Response:
    try:
        target = safe_join(ROOT, relative)
    except ValueError:  # tried to escape ROOT, e.g. ../../etc/passwd
        raise NotFound()
    if not target.is_file():
        raise NotFound()
    return Response(target.read_bytes(), content_type=guess_mime(target.name))


@app.get("/")
def index():
    return _serve("index.html")


@app.get("/static/<path:rel>")
def static_file(rel: str):
    return _serve(rel)


if __name__ == "__main__":
    app.run()
