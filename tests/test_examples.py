"""Smoke tests so the documented examples keep working."""

import importlib
import os

import pytest

from nexusserver import Headers
from nexusserver.http.request import Request


def load(name):
    return importlib.import_module(f"examples.{name}").app


def req(method, path, body=b"", headers=None):
    h = Headers((headers or {}).items())
    if body:
        h["Content-Length"] = str(len(body))
    return Request(method, path, headers=h, body=body)


def test_hello():
    assert load("hello_server").handle(req("GET", "/")).body == b"Hello from NexusServer!"


def test_routes():
    app = load("routes")
    assert app.handle(req("GET", "/users/7")).body == b'{"user_id": 7, "name": "User 7"}'
    assert app.handle(req("GET", "/teapot")).status_code == 418
    assert app.handle(req("GET", "/old-home")).status_code == 301


def test_json_api_crud():
    app = load("json_api")
    created = app.handle(req("POST", "/items", b'{"name": "Gadget"}'))
    assert created.status_code == 201
    assert app.handle(req("POST", "/items", b'{"nope": 1}')).status_code == 400
    assert app.handle(req("PUT", "/items/1", b'{"name": "New"}')).status_code == 200
    assert app.handle(req("DELETE", "/items/1")).status_code == 204
    assert app.handle(req("GET", "/items/1")).status_code == 404


def test_static_site_blocks_traversal():
    app = load("static_site")
    assert app.handle(req("GET", "/")).status_code == 200
    assert app.handle(req("GET", "/static/index.html")).headers["Content-Type"].startswith("text/html")
    assert app.handle(req("GET", "/static/../static_site.py")).status_code == 404
    assert app.handle(req("GET", "/static/%2e%2e/static_site.py")).status_code == 404


def test_database_app():
    app = load("database_app")
    assert app.handle(req("POST", "/notes", b'{"body": "milk"}')).status_code == 201
    assert app.handle(req("POST", "/notes", b'{"body": ""}')).status_code == 400
    assert b"milk" in app.handle(req("GET", "/notes")).body


def test_sessions_app():
    app = load("sessions_app")
    first = app.handle(req("GET", "/"))
    cookie = first.headers["Set-Cookie"].split(";")[0]
    assert app.handle(req("GET", "/me", headers={"Cookie": cookie})).status_code == 401
    login = req("POST", "/login", b"name=Ada", {"Cookie": cookie})
    assert app.handle(login).status_code == 200
    assert b"Ada" in app.handle(req("GET", "/me", headers={"Cookie": cookie})).body


def test_middleware_app():
    app = load("middleware_app")
    response = app.handle(req("GET", "/data", headers={"Accept-Encoding": "gzip", "Origin": "https://app.example"}))
    assert response.headers["Content-Encoding"] == "gzip"
    assert "X-Request-Time" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "https://app.example"


def test_notes_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = load("notes_api")
    app.lifecycle.startup()
    try:
        created = app.handle(req("POST", "/notes", b'{"title": "Hi", "body": "First"}'))
        assert created.status_code == 201
        assert app.handle(req("POST", "/notes", b'{"body": "no title"}')).status_code == 400
        assert app.handle(req("GET", "/notes/1")).status_code == 200
        assert app.handle(req("DELETE", "/notes/1")).status_code == 204
        assert app.handle(req("DELETE", "/notes/1")).status_code == 404
    finally:
        app.lifecycle.shutdown()


# ----- 26.3 examples -----
def test_upload_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = load("upload_app")
    boundary = "B"
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\nHoliday\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="../../pic.png"\r\n'
            f"Content-Type: image/png\r\n\r\nPNGDATA\r\n--{boundary}--\r\n").encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    created = app.handle(req("POST", "/upload", body, headers))
    assert created.status_code == 201 and b'"saved_as": "pic.png"' in created.body
    assert (tmp_path / "uploads" / "pic.png").read_bytes() == b"PNGDATA"
    assert b"pic.png" in app.handle(req("GET", "/files")).body

    bad = body.replace(b"image/png", b"application/x-sh")
    assert app.handle(req("POST", "/upload", bad, headers)).status_code == 400
    assert app.handle(req("POST", "/upload", b"x", {"Content-Type": "text/plain"})).status_code == 400


def test_auth_app():
    import base64
    app = load("auth_app")
    assert app.handle(req("GET", "/profile")).status_code == 401
    bad = app.handle(req("POST", "/login", b"username=ada&password=nope"))
    assert bad.status_code == 401
    good = app.handle(req("POST", "/login", b"username=ada&password=lovelace"))
    assert good.status_code == 200
    cookie = good.headers["Set-Cookie"].split(";")[0]
    assert b"ada" in app.handle(req("GET", "/profile", headers={"Cookie": cookie})).body

    assert app.handle(req("GET", "/admin/stats")).status_code == 401
    creds = "Basic " + base64.b64encode(b"admin:admin-pass").decode()
    ok = app.handle(req("GET", "/admin/stats", headers={"Authorization": creds}))
    assert ok.status_code == 200 and b"admin" in ok.body


def test_error_handlers_example():
    app = load("error_handlers")
    assert app.handle(req("GET", "/missing")).body == b'{"error": "not_found", "path": "/missing"}'
    assert app.handle(req("GET", "/boom")).body == b'{"error": "internal_error"}'
    sold_out = app.handle(req("GET", "/orders/13"))
    assert sold_out.status_code == 409
    unprocessable = app.handle(req("GET", "/orders/0"))
    assert unprocessable.status_code == 422 and b"Order ids start at 1" in unprocessable.body
    assert app.handle(req("GET", "/orders/101")).status_code == 404


def test_rate_limit_example():
    app = load("rate_limit_app")
    codes = [app.handle(req("GET", "/api")).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    assert all(app.handle(req("GET", "/health")).status_code == 200 for _ in range(10))


def test_static_mount_example():
    app = load("static_mount")
    first = app.handle(req("GET", "/assets/"))
    assert first.status_code == 200 and b"NexusServer" in first.body
    again = app.handle(req("GET", "/assets/", headers={"If-None-Match": first.headers["ETag"]}))
    assert again.status_code == 304
