# Middleware

A middleware wraps the next handler: it receives the `Request`, may call
`self.app(request)`, and returns a `Response`.

```python
from nexusserver.middleware import BaseMiddleware

class TimingMiddleware(BaseMiddleware):
    def __call__(self, request):
        response = self.app(request)
        response.headers["X-Seen"] = request.path
        return response

app.add_middleware(TimingMiddleware)
```

## Options

Keyword arguments to `add_middleware` go to the constructor:

```python
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example"])
```

## Ordering

The first middleware added is the **outermost**. Every `Application` starts with
`SecurityHeadersMiddleware` then `RequestLogMiddleware`, so yours run inside
those. Errors raised by handlers are turned into responses *before* they reach
middleware, so middleware always sees a `Response` (including 404/405/500).

## Built-in middleware

| Class | Options | Notes |
| --- | --- | --- |
| `SecurityHeadersMiddleware` | `extra` (dict) | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `X-XSS-Protection`. Default; never overwrites a header you set. |
| `RequestLogMiddleware` | none | One log line per request on `nexusserver.access`. Default. |
| `CORSMiddleware` | `allow_origins`, `allow_methods`, `allow_headers`, `allow_credentials`, `max_age` | Answers `OPTIONS` preflight with 204. With credentials and `"*"`, the request's origin is echoed back, so prefer an explicit allow-list. |
| `GZipMiddleware` | `minimum_size=500` | Compresses when the client sends `Accept-Encoding: gzip`. |
| `SignedSessionMiddleware` | `secret_key` (required), `cookie_name`, `max_age=14d`, `secure`, `samesite` | Session stored in a signed (not encrypted) cookie. See [security](security.md). |
| `RateLimitMiddleware` | `limit=100`, `window=60`, `key_func`, `exempt_paths`, `clock` | 429 + `Retry-After` over the limit; `X-RateLimit-*` headers. See [security](security.md). |
| `BasicAuthMiddleware` | `users` or `verify`, `realm`, `exempt_paths` | HTTP Basic auth; `request.state["user"]`. See [security](security.md). |
| `SessionMiddleware` | `cookie_name="nexussession"`, `max_age=None`, `secure=False` | In-memory sessions at `request.state["session"]`. |

## Sessions

```python
app.add_middleware(SessionMiddleware, max_age=3600, secure=True)

@app.get("/")
def index(request):
    session = request.state["session"]
    session["visits"] = session.get("visits", 0) + 1
    return {"visits": session["visits"]}
```

The cookie holds a random 256-bit token; data stays on the server. Sessions are
lost on restart, are not shared between processes, and expired sessions are not
purged, so this suits development and small single-process apps. Set `secure=True`
when serving over HTTPS.
