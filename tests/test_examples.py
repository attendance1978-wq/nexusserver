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
