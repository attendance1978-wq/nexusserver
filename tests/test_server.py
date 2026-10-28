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


# ----- keep-alive and chunked requests (26.3) -----
def start(app, **config):
    engine = HTTPEngine(app.handle, Config(port=0, **config))
    threading.Thread(target=engine.start, daemon=True).start()
    assert engine.ready.wait(5)
    return engine


class Reader:
    """Reads Content-Length framed responses from a socket, keeping leftover bytes between calls."""

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""

    def _fill(self):
        chunk = self.sock.recv(65536)
        if not chunk:
            raise EOFError("connection closed")
        self.buffer += chunk

    def response(self):
        while b"\r\n\r\n" not in self.buffer:
            self._fill()
        head, _, rest = self.buffer.partition(b"\r\n\r\n")
        length = int([l for l in head.split(b"\r\n") if l.lower().startswith(b"content-length")][0].split(b":")[1])
        while len(rest) < length:
            self._fill()
            head, _, rest = self.buffer.partition(b"\r\n\r\n")
        self.buffer = rest[length:]
        return head, rest[:length]


def test_keep_alive_serves_many_requests_on_one_connection():
    app = Application()
    app.get("/")(lambda: "hi")
    engine = start(app)
    try:
        conn = http.client.HTTPConnection(*engine.address)
        for _ in range(5):
            conn.request("GET", "/")
            response = conn.getresponse()
            assert response.read() == b"hi"
            assert response.getheader("Connection") == "keep-alive"
        conn.close()
    finally:
        engine.stop()


def test_pipelined_requests_are_answered_in_order():
    app = Application()
    app.get("/<str:n>")(lambda n: n)
    engine = start(app)
    try:
        with socket.create_connection(engine.address) as sock:
            sock.sendall(b"GET /one HTTP/1.1\r\nHost: x\r\n\r\nGET /two HTTP/1.1\r\nHost: x\r\n\r\n")
            reader = Reader(sock)
            _, first = reader.response()
            _, second = reader.response()
            assert (first, second) == (b"one", b"two")
    finally:
        engine.stop()


def test_connection_close_is_honoured():
    app = Application()
    app.get("/")(lambda: "hi")
    engine = start(app)
    try:
        conn = http.client.HTTPConnection(*engine.address)
        conn.request("GET", "/", headers={"Connection": "close"})
        response = conn.getresponse()
        response.read()
        assert response.getheader("Connection") == "close"
    finally:
        engine.stop()


def test_keep_alive_can_be_disabled_and_is_capped():
    app = Application()
    app.get("/")(lambda: "hi")
    engine = start(app, keep_alive=False)
    try:
        conn = http.client.HTTPConnection(*engine.address)
        conn.request("GET", "/")
        assert conn.getresponse().getheader("Connection") == "close"
    finally:
        engine.stop()

    engine = start(app, max_keepalive_requests=2)
    try:
        conn = http.client.HTTPConnection(*engine.address)
        conn.request("GET", "/")
        first = conn.getresponse(); first.read()
        conn.request("GET", "/")
        second = conn.getresponse(); second.read()
        assert first.getheader("Connection") == "keep-alive"
        assert second.getheader("Connection") == "close"
    finally:
        engine.stop()


def test_idle_keep_alive_connection_is_closed_quietly():
    app = Application()
    app.get("/")(lambda: "hi")
    engine = start(app, keep_alive_timeout=0.3)
    try:
        with socket.create_connection(engine.address) as sock:
            sock.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
            Reader(sock).response()
            time.sleep(0.8)
            assert sock.recv(1024) == b""  # server closed it, no 408 noise
    finally:
        engine.stop()


def test_chunked_request_body_over_the_wire():
    app = Application()
    app.post("/echo")(lambda request: {"text": request.text()})
    engine = start(app)
    try:
        with socket.create_connection(engine.address) as sock:
            sock.sendall(b"POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n")
            time.sleep(0.1)
            sock.sendall(b"7\r\n, world\r\n0\r\n\r\n")
            reader = Reader(sock)
            assert reader.response()[1] == b'{"text": "hello, world"}'
            # the connection is still usable afterwards
            sock.sendall(b"POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\n\r\nok")
            assert reader.response()[1] == b'{"text": "ok"}'
    finally:
        engine.stop()


def test_stop_wakes_idle_keep_alive_workers():
    app = Application()
    app.get("/")(lambda: "hi")
    engine = start(app, keep_alive_timeout=30)
    with socket.create_connection(engine.address) as sock:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        Reader(sock).response()
        started = time.time()
        engine.stop()
        assert sock.recv(1024) == b""
        assert time.time() - started < 5
