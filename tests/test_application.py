from nexusserver import Application, Config, Response
from nexusserver.http.request import Request
from nexusserver.middleware import GZipMiddleware


def test_basic_route():
    app = Application()

    @app.get("/hello")
    def hello():
        return "world"

    response = app.handle(Request("GET", "/hello"))
    assert response.status_code == 200
    assert response.body == b"world"


def test_404():
    assert Application().handle(Request("GET", "/missing")).status_code == 404


def test_405_has_allow_header():
    app = Application()

    @app.get("/only-get")
    def handler():
        return "ok"

    response = app.handle(Request("POST", "/only-get"))
    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"


def test_head_falls_back_to_get():
    app = Application()

    @app.get("/x")
    def x():
        return "hi"

    assert app.handle(Request("HEAD", "/x")).status_code == 200


def test_return_types():
    app = Application()
    app.get("/json")(lambda: {"a": 1})
    app.get("/list")(lambda: [1, 2])
    app.get("/created")(lambda: ({"ok": True}, 201))
    app.get("/headers")(lambda: ("hi", 200, {"X-Test": "1"}))
    app.get("/bytes")(lambda: b"\x00\x01")
    app.get("/none")(lambda: None)

    assert app.handle(Request("GET", "/json")).body == b'{"a": 1}'
    assert app.handle(Request("GET", "/list")).headers["Content-Type"].startswith("application/json")
    created = app.handle(Request("GET", "/created"))
    assert created.status_code == 201 and created.body == b'{"ok": true}'
    assert app.handle(Request("GET", "/headers")).headers["X-Test"] == "1"
    assert app.handle(Request("GET", "/bytes")).body == b"\x00\x01"  # 0.1.x returned "b'...'"
    assert app.handle(Request("GET", "/none")).body == b""


def test_path_params_are_converted():
    app = Application()

    @app.get("/users/<int:user_id>")
    def user(user_id):
        return {"id": user_id}

    assert app.handle(Request("GET", "/users/42")).body == b'{"id": 42}'


def test_unhandled_exception_is_500_and_hides_details():
    app = Application()

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret")

    response = app.handle(Request("GET", "/boom"))
    assert response.status_code == 500
    assert b"secret" not in response.body


def test_debug_shows_error_details():
    app = Application(Config(debug=True))

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret")

    assert b"RuntimeError: secret" in app.handle(Request("GET", "/boom")).body


def test_add_middleware_accepts_options():
    app = Application()
    app.add_middleware(GZipMiddleware, minimum_size=10)
    app.get("/")(lambda: "x" * 100)
    response = app.handle(Request("GET", "/", headers=_h({"Accept-Encoding": "gzip"})))
    assert response.headers["Content-Encoding"] == "gzip"


def test_middleware_added_after_first_request_still_applies():
    app = Application()
    app.get("/")(lambda: "ok")
    app.handle(Request("GET", "/"))
    app.add_middleware(GZipMiddleware, minimum_size=1)
    response = app.handle(Request("GET", "/", headers=_h({"Accept-Encoding": "gzip"})))
    assert response.headers["Content-Encoding"] == "gzip"


def test_lifecycle_hooks_registered():
    app = Application()
    calls = []
    app.on_startup(lambda: calls.append("up"))
    app.on_shutdown(lambda: calls.append("down"))
    app.lifecycle.startup()
    app.lifecycle.shutdown()
    assert calls == ["up", "down"]


def test_explicit_response_object_passes_through():
    app = Application()
    app.get("/r")(lambda: Response.redirect("/elsewhere"))
    response = app.handle(Request("GET", "/r"))
    assert response.status_code == 302 and response.headers["Location"] == "/elsewhere"


def _h(items):
    from nexusserver import Headers
    return Headers(items.items())
