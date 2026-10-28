import base64
import json

import pytest

from nexusserver import Application, Headers
from nexusserver.http.request import Request
from nexusserver.middleware import BasicAuthMiddleware, RateLimitMiddleware, SignedSessionMiddleware
from nexusserver.security import hash_password, sign, unsign, verify_password


def req(path="/", headers=None, client=("1.2.3.4", 1)):
    r = Request("GET", path, headers=Headers((headers or {}).items()))
    r.client = client
    return r


# ----- signing / passwords -----
def test_sign_roundtrip_and_tamper():
    token = sign(b"hello", "x" * 32)
    assert unsign(token, "x" * 32) == b"hello"
    assert unsign(token, "y" * 32) is None
    payload, stamp, sig = token.split(".")
    assert unsign(f"{payload}A.{stamp}.{sig}", "x" * 32) is None
    assert unsign("garbage", "x" * 32) is None


def test_unsign_expiry():
    token = sign(b"hello", "x" * 32)
    assert unsign(token, "x" * 32, max_age=60) == b"hello"
    assert unsign(token, "x" * 32, max_age=-1) is None


def test_short_secret_rejected():
    with pytest.raises(ValueError):
        sign(b"x", "short")


def test_password_hashing():
    stored = hash_password("s3cret")
    assert stored != hash_password("s3cret")  # random salt
    assert verify_password("s3cret", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("s3cret", "not-a-hash")


# ----- rate limiting -----
def test_rate_limit_blocks_then_resets():
    now = [0.0]
    app = Application()
    app.add_middleware(RateLimitMiddleware, limit=2, window=10, clock=lambda: now[0])
    app.get("/")(lambda: "ok")

    assert app.handle(req()).status_code == 200
    second = app.handle(req())
    assert second.status_code == 200 and second.headers["X-RateLimit-Remaining"] == "0"
    blocked = app.handle(req())
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) >= 1
    assert app.handle(req(client=("9.9.9.9", 1))).status_code == 200  # other client unaffected
    now[0] = 11.0
    assert app.handle(req()).status_code == 200


def test_rate_limit_ignores_forwarded_for_and_supports_key_func():
    app = Application()
    app.add_middleware(RateLimitMiddleware, limit=1, window=60)
    app.get("/")(lambda: "ok")
    app.handle(req(headers={"X-Forwarded-For": "1.1.1.1"}))
    assert app.handle(req(headers={"X-Forwarded-For": "2.2.2.2"})).status_code == 429

    app2 = Application()
    app2.add_middleware(RateLimitMiddleware, limit=1, window=60,
                        key_func=lambda r: r.headers.get("X-Api-Key", "-"))
    app2.get("/")(lambda: "ok")
    assert app2.handle(req(headers={"X-Api-Key": "a"})).status_code == 200
    assert app2.handle(req(headers={"X-Api-Key": "b"})).status_code == 200
    assert app2.handle(req(headers={"X-Api-Key": "a"})).status_code == 429


def test_rate_limit_exempt_path():
    app = Application()
    app.add_middleware(RateLimitMiddleware, limit=1, window=60, exempt_paths=("/health",))
    app.get("/health")(lambda: "ok")
    for _ in range(5):
        assert app.handle(req("/health")).status_code == 200


# ----- signed sessions -----
def make_session_app():
    app = Application()
    app.add_middleware(SignedSessionMiddleware, secret_key="k" * 32)

    @app.get("/inc")
    def inc(request):
        s = request.state["session"]
        s["n"] = s.get("n", 0) + 1
        return {"n": s["n"]}

    @app.get("/peek")
    def peek(request):
        return dict(request.state["session"])

    @app.get("/clear")
    def clear(request):
        request.state["session"].clear()
        return "ok"

    return app


def cookie_of(response):
    return response.headers["Set-Cookie"].split(";")[0]


def test_signed_session_roundtrip_and_no_resend_when_unchanged():
    app = make_session_app()
    first = app.handle(req("/inc"))
    cookie = cookie_of(first)
    second = app.handle(req("/inc", {"Cookie": cookie}))
    assert json.loads(second.body) == {"n": 2}
    peek = app.handle(req("/peek", {"Cookie": cookie_of(second)}))
    assert "Set-Cookie" not in peek.headers and json.loads(peek.body) == {"n": 2}


def test_signed_session_tamper_and_wrong_key():
    app = make_session_app()
    cookie = cookie_of(app.handle(req("/inc")))
    name, _, token = cookie.partition("=")
    payload, stamp, sig = token.split(".")
    forged_payload = base64.urlsafe_b64encode(b'{"n": 999}').rstrip(b"=").decode()
    forged = f"{name}={forged_payload}.{stamp}.{sig}"
    assert json.loads(app.handle(req("/peek", {"Cookie": forged})).body) == {}

    other = Application()
    other.add_middleware(SignedSessionMiddleware, secret_key="z" * 32)
    other.get("/peek")(lambda request: dict(request.state["session"]))
    assert json.loads(other.handle(req("/peek", {"Cookie": cookie})).body) == {}


def test_signed_session_clear_deletes_cookie():
    app = make_session_app()
    cookie = cookie_of(app.handle(req("/inc")))
    cleared = app.handle(req("/clear", {"Cookie": cookie}))
    assert "Max-Age=0" in cleared.headers["Set-Cookie"]


def test_signed_session_requires_strong_secret():
    app = Application()
    app.add_middleware(SignedSessionMiddleware, secret_key="short")
    with pytest.raises(ValueError):
        app.handle(req())


# ----- basic auth -----
def auth_header(user, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def make_auth_app():
    app = Application()
    app.add_middleware(BasicAuthMiddleware, users={"ada": hash_password("pw")}, exempt_paths=("/public",))
    app.get("/public")(lambda: "open")
    app.get("/me")(lambda request: request.state["user"])
    return app


def test_basic_auth():
    app = make_auth_app()
    assert app.handle(req("/public")).status_code == 200
    denied = app.handle(req("/me"))
    assert denied.status_code == 401 and "Basic" in denied.headers["WWW-Authenticate"]
    assert app.handle(req("/me", auth_header("ada", "bad"))).status_code == 401
    assert app.handle(req("/me", auth_header("nobody", "pw"))).status_code == 401
    ok = app.handle(req("/me", auth_header("ada", "pw")))
    assert ok.status_code == 200 and ok.body == b"ada"


def test_basic_auth_garbage_and_custom_verifier():
    app = make_auth_app()
    assert app.handle(req("/me", {"Authorization": "Basic !!!notbase64"})).status_code == 401
    assert app.handle(req("/me", {"Authorization": "Bearer abc"})).status_code == 401

    app2 = Application()
    app2.add_middleware(BasicAuthMiddleware, verify=lambda u, p: (u, p) == ("a", "b"))
    app2.get("/")(lambda: "in")
    assert app2.handle(req("/", auth_header("a", "b"))).status_code == 200


def test_basic_auth_needs_exactly_one_source():
    with pytest.raises(ValueError):
        BasicAuthMiddleware(lambda r: None)
