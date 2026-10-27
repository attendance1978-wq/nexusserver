from nexusserver import Application, Headers
from nexusserver.http.request import Request
from nexusserver.middleware import CORSMiddleware, GZipMiddleware, SessionMiddleware


def test_cors_headers():
    app = Application()
    app.add_middleware(CORSMiddleware)
    app.get("/")(lambda: "ok")
    req = Request("GET", "/", headers=Headers([("Origin", "https://example.com")]))
    assert app.handle(req).headers["Access-Control-Allow-Origin"] in ("*", "https://example.com")


def test_cors_preflight_and_allowlist():
    app = Application()
    app.add_middleware(CORSMiddleware, allow_origins=["https://good.example"])
    app.get("/")(lambda: "ok")
    good = app.handle(Request("OPTIONS", "/", headers=Headers([("Origin", "https://good.example")])))
    bad = app.handle(Request("OPTIONS", "/", headers=Headers([("Origin", "https://evil.example")])))
    assert good.status_code == 204 and good.headers["Access-Control-Allow-Origin"] == "https://good.example"
    assert "Access-Control-Allow-Origin" not in bad.headers


def test_security_headers_default():
    app = Application()
    app.get("/")(lambda: "ok")
    assert app.handle(Request("GET", "/")).headers["X-Content-Type-Options"] == "nosniff"


def test_gzip_skips_small_bodies():
    app = Application()
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.get("/")(lambda: "tiny")
    response = app.handle(Request("GET", "/", headers=Headers([("Accept-Encoding", "gzip")])))
    assert "Content-Encoding" not in response.headers


def test_sessions_persist_across_requests():
    app = Application()
    app.add_middleware(SessionMiddleware)

    @app.get("/count")
    def count(request):
        session = request.state["session"]
        session["n"] = session.get("n", 0) + 1
        return {"n": session["n"]}

    first = app.handle(Request("GET", "/count"))
    cookie = first.headers["Set-Cookie"].split(";")[0]
    second = app.handle(Request("GET", "/count", headers=Headers([("Cookie", cookie)])))
    assert first.body == b'{"n": 1}' and second.body == b'{"n": 2}'
    assert "Set-Cookie" not in second.headers


def test_session_stores_are_per_application():
    a, b = Application(), Application()
    a.add_middleware(SessionMiddleware)
    b.add_middleware(SessionMiddleware)
    a.get("/")(lambda request: request.state["session"].setdefault("x", 1) and "ok")
    b.get("/")(lambda request: str(len(request.state["session"])))
    cookie = a.handle(Request("GET", "/")).headers["Set-Cookie"].split(";")[0]
    assert b.handle(Request("GET", "/", headers=Headers([("Cookie", cookie)]))).body == b"0"
