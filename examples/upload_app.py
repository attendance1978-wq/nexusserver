"""File uploads with multipart/form-data.

Run:  python -m nexusserver examples.upload_app:app
Try:  curl -F "title=Holiday" -F "photo=@picture.png" localhost:8000/upload
      curl localhost:8000/files
Files are written to ./uploads (created on first upload).
"""

from pathlib import Path

from nexusserver import Application, BadRequest, Config, Response

UPLOAD_DIR = Path("uploads")
ALLOWED = {"image/png", "image/jpeg", "text/plain", "application/pdf"}

# Cap the whole request body at 5 MiB; larger uploads get 413.
app = Application(Config(max_request_size=5 * 1024 * 1024))


@app.get("/")
def form():
    return Response.html(
        '<form method="post" action="/upload" enctype="multipart/form-data">'
        '<input name="title"><input type="file" name="photo"><button>Upload</button></form>'
    )


@app.post("/upload")
def upload(request):
    form = request.multipart()
    upload = form.files.get("photo")
    if upload is None or not upload.filename:
        raise BadRequest("Send a file in the 'photo' field")
    if upload.content_type not in ALLOWED:
        raise BadRequest(f"Content type {upload.content_type!r} is not allowed")
    saved = upload.save(UPLOAD_DIR)  # the name is sanitised, so '../../x' stays inside UPLOAD_DIR
    return {"title": form.fields.get("title", ""), "saved_as": saved.name, "bytes": upload.size}, 201


@app.get("/files")
def list_files():
    names = sorted(p.name for p in UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else []
    return {"files": names}


if __name__ == "__main__":
    app.run()
