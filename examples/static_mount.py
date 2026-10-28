"""Mount a directory with app.static(): ETag / Last-Modified, 304 responses, directory index.

Run (from the project root):  python -m nexusserver examples.static_mount:app
Try:  curl -i localhost:8000/assets/                 (serves public/index.html)
      curl -i -H 'If-None-Match: <etag from above>' localhost:8000/assets/
"""

from pathlib import Path

from nexusserver import Application

app = Application()
app.static("/assets", Path(__file__).parent / "public", max_age=600)


@app.get("/")
def home():
    return "Static files live under /assets/"


if __name__ == "__main__":
    app.run()
