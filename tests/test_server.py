"""End-to-end tests against a real listening socket."""

import http.client
import socket
import threading
import time

import pytest

from nexusserver import Application, Config
from nexusserver.server import HTTPEngine


@pytest.fixture
def server():
    app = Application()

    @app.get("/")
    def index():
        return "hello"

    @app.post("/echo")
    def echo(request):
        return {"length": len(request.body), "text": request.text()}

    engine = HTTPEngine(app.handle, Config(port=0, read_timeout=2))
    thread = threading.Thread(target=engine.start, daemon=True)
    thread.start()
    assert engine.ready.wait(5)
    yield engine.address
    engine.stop()


def test_get(server):
    conn = http.client.HTTPConnection(*server)
    conn.request("GET", "/")
    response = conn.getresponse()
    assert response.status == 200 and response.read() == b"hello"
    assert response.getheader("Server") == "NexusServer"


def test_head_has_no_body(server):
    conn = http.client.HTTPConnection(*server)
    conn.request("HEAD", "/")
    response = conn.getresponse()
    assert response.status == 200 and response.read() == b""
    assert response.getheader("Content-Length") == "5"


def test_large_post_body_arrives_complete(server):
    payload = "x" * 300_000  # needs several recv() calls
    conn = http.client.HTTPConnection(*server)
    conn.request("POST", "/echo", body=payload)
    data = conn.getresponse().read()
    assert b'"length": 300000' in data


def test_body_in_a_later_packet(server):
    with socket.create_connection(server) as sock:
        sock.sendall(b"POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\n\r\n")
        time.sleep(0.2)
        sock.sendall(b"hello")
        assert b'"text": "hello"' in sock.recv(65536)


def test_malformed_request_is_400_not_500(server):
    with socket.create_connection(server) as sock:
        sock.sendall(b"NONSENSE\r\n\r\n")
        assert sock.recv(1024).startswith(b"HTTP/1.1 400")


def test_oversized_headers_are_431():
    app = Application()
    engine = HTTPEngine(app.handle, Config(port=0, max_header_size=256))
    threading.Thread(target=engine.start, daemon=True).start()
    assert engine.ready.wait(5)
    try:
        with socket.create_connection(engine.address) as sock:
            sock.sendall(b"GET / HTTP/1.1\r\nX-Big: " + b"a" * 1000 + b"\r\n\r\n")
            assert sock.recv(1024).startswith(b"HTTP/1.1 431")
    finally:
        engine.stop()


def test_multiple_cookies_sent_as_separate_lines():
    app = Application()

    @app.get("/")
    def index():
        from nexusserver import Response
        r = Response("ok")
        r.set_cookie("a", "1")
        r.set_cookie("b", "2")
        return r

    engine = HTTPEngine(app.handle, Config(port=0))
    threading.Thread(target=engine.start, daemon=True).start()
    assert engine.ready.wait(5)
    try:
        conn = http.client.HTTPConnection(*engine.address)
        conn.request("GET", "/")
        cookies = conn.getresponse().msg.get_all("Set-Cookie")
        assert len(cookies) == 2
    finally:
        engine.stop()
