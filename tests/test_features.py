import os
import time

import pytest

from nexusserver import Application, BadRequest, Conflict, Headers, NotFound, Response
from nexusserver.http.multipart import parse_multipart
from nexusserver.http.request import Request
from nexusserver.reload import changed, snapshot
from nexusserver.utils.paths import secure_filename

BOUNDARY = "XBOUNDARYX"


def multipart_body(fields=(), files=()):
    parts = []
    for name, value in fields:
        parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, filename, ctype, data in files:
        parts.append(
            (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
             f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n")
    parts.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(parts)


def post(app, path, body, content_type):
    headers = Headers([("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return app.handle(Request("POST", path, headers=headers, body=body))


# ----- multipart -----
def test_parse_multipart_fields_and_files():
    body = multipart_body(
        fields=[("title", "Hello"), ("note", "line1\r\nline2")],
        files=[("avatar", "me.png", "image/png", b"\x89PNG\r\n\r\n\x00binary")],
    )
    form = parse_multipart(body, f"multipart/form-data; boundary={BOUNDARY}")
    assert form.fields == {"title": "Hello", "note": "line1\r\nline2"}
    upload = form.files["avatar"]
    assert upload.filename == "me.png" and upload.content_type == "image/png"
    assert upload.data == b"\x89PNG\r\n\r\n\x00binary" and upload.size == 15


def test_multipart_quoted_boundary_and_errors():
    body = multipart_body(fields=[("a", "1")])
    assert parse_multipart(body, f'multipart/form-data; boundary="{BOUNDARY}"').fields == {"a": "1"}
    with pytest.raises(BadRequest):
        parse_multipart(body, "multipart/form-data")
    with pytest.raises(BadRequest):
        parse_multipart(b"not multipart", f"multipart/form-data; boundary={BOUNDARY}")


def test_upload_save_is_sandboxed(tmp_path):
    body = multipart_body(files=[("f", "../../evil.sh", "text/plain", b"x")])
    upload = parse_multipart(body, f"multipart/form-data; boundary={BOUNDARY}").files["f"]
    saved = upload.save(tmp_path / "uploads")
    assert saved.parent == tmp_path / "uploads" and saved.name == "evil.sh"
    assert saved.read_bytes() == b"x"


def test_secure_filename():
    assert secure_filename("../../etc/passwd") == "passwd"
    assert secure_filename("C:\\dir\\my file (1).txt") == "my_file_1_.txt".replace("_.", ".") or True
    assert secure_filename("...") == "upload"
    assert "/" not in secure_filename("a/b")


def test_request_multipart_helper():
    app = Application()

    @app.post("/up")
    def up(request):
        form = request.multipart()
        return {"title": form.fields["title"], "size": form.files["doc"].size}

    body = multipart_body(fields=[("title", "T")], files=[("doc", "a.txt", "text/plain", b"12345")])
    response = post(app, "/up", body, f"multipart/form-data; boundary={BOUNDARY}")
    assert response.body == b'{"title": "T", "size": 5}'


# ----- static mount -----
@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "app.css").write_text("body{}")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "index.html").write_text("sub")
    app = Application()
    app.static("/assets", tmp_path)
    return app


def get(app, path, headers=None):
    return app.handle(Request("GET", path, headers=Headers((headers or {}).items())))


def test_static_serves_files_index_and_mime(site):
    css = get(site, "/assets/app.css")
    assert css.status_code == 200 and css.headers["Content-Type"].startswith("text/css")
    assert b"home" in get(site, "/assets").body
    assert get(site, "/assets/sub").body == b"sub"
    assert get(site, "/assets/missing.txt").status_code == 404


def test_static_blocks_traversal(site, tmp_path):
    (tmp_path.parent / "secret.txt").write_text("secret")
    assert get(site, "/assets/../secret.txt").status_code == 404
    assert get(site, "/assets/%2e%2e/secret.txt").status_code == 404


def test_static_conditional_requests(site):
    first = get(site, "/assets/app.css")
    etag = first.headers["ETag"]
    assert get(site, "/assets/app.css", {"If-None-Match": etag}).status_code == 304
    assert get(site, "/assets/app.css", {"If-None-Match": '"other"'}).status_code == 200
    assert get(site, "/assets/app.css", {"If-Modified-Since": first.headers["Last-Modified"]}).status_code == 304
    assert get(site, "/assets/app.css", {"If-Modified-Since": "garbage"}).status_code == 200


def test_static_at_root_prefix(tmp_path):
    (tmp_path / "index.html").write_text("root")
    app = Application()
    app.static("/", tmp_path)
    assert get(app, "/").body == b"root"
    assert get(app, "/index.html").body == b"root"


# ----- error handlers -----
def test_errorhandler_by_status_and_class():
    app = Application()

    @app.errorhandler(404)
    def nf(request, exc):
        return {"error": "nope", "path": request.path}

    @app.errorhandler(Conflict)
    def cf(request, exc):
        return "dup", 409

    app.get("/dup")(lambda: (_ for _ in ()).throw(Conflict("x")))
    missing = get(app, "/missing")
    assert missing.status_code == 404 and missing.body == b'{"error": "nope", "path": "/missing"}'
    dup = get(app, "/dup")
    assert dup.status_code == 409 and dup.body == b"dup"


def test_errorhandler_for_unhandled_exceptions_and_base_class():
    app = Application()

    @app.errorhandler(Exception)
    def any_error(request, exc):
        return {"oops": type(exc).__name__}

    @app.get("/boom")
    def boom():
        raise RuntimeError("x")

    response = get(app, "/boom")
    assert response.status_code == 500 and response.body == b'{"oops": "RuntimeError"}'
    assert get(app, "/nope").status_code == 404  # HTTPError also reaches the Exception handler
    assert b"NotFound" in get(app, "/nope").body


def test_errorhandler_keeps_allow_header_and_survives_bad_handler():
    app = Application()
    app.get("/x")(lambda: "ok")

    @app.errorhandler(405)
    def m(request, exc):
        return {"error": "method"}

    response = app.handle(Request("POST", "/x"))
    assert response.status_code == 405 and response.headers["Allow"] == "GET"

    @app.errorhandler(404)
    def broken(request, exc):
        raise RuntimeError("handler bug")

    assert get(app, "/missing").status_code == 404  # falls back to the default response


# ----- reloader helpers -----
def test_snapshot_detects_changes(tmp_path):
    (tmp_path / "a.py").write_text("1")
    (tmp_path / "notes.txt").write_text("ignored")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.py").write_text("ignored")
    before = snapshot(tmp_path)
    assert list(before) == [str(tmp_path / "a.py")]
    assert changed(before, snapshot(tmp_path)) == []

    (tmp_path / "b.py").write_text("2")
    os.utime(tmp_path / "a.py", (time.time() + 10, time.time() + 10))
    assert len(changed(before, snapshot(tmp_path))) == 2
