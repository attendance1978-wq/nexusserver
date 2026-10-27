# Requests and responses

## Request

| Member | Description |
| --- | --- |
| `method`, `path`, `query_string`, `http_version`, `scheme` | Parsed request line (`path` is percent-decoded) |
| `query` | `dict` of the first value of each query parameter |
| `headers` | Case-insensitive `Headers` |
| `cookies` | `dict` parsed from `Cookie` |
| `body` / `text()` | Raw bytes / decoded text |
| `json()` | Parsed JSON body, or `None` if the body is empty (raises `ValueError` on bad JSON) |
| `form()` | `dict` from an `application/x-www-form-urlencoded` body |
| `path_params` | Converted route parameters |
| `client` | `(ip, port)` |
| `state` | Per-request `dict` for middleware to share data (sessions use it) |

## Return values

A handler may return any of these:

| Return | Result |
| --- | --- |
| `Response` | Used as is |
| `dict` / `list` | JSON, `application/json` |
| `str` | `text/plain; charset=utf-8` |
| `bytes` | `application/octet-stream` |
| `None` | Empty body |
| `(body, status)` | Any of the above with a status code |
| `(body, status, headers)` | ...and extra headers (`dict`) |

```python
return {"ok": True}, 201
return "Teapot", 418, {"X-Brew": "tea"}
return None, 204
```

## Building a Response

```python
from nexusserver import Response

Response("plain text")
Response.text("plain text", status_code=200)
Response.html("<h1>Hi</h1>")
Response.json({"a": 1}, status_code=201)
Response.redirect("/login", status_code=303)
Response(png_bytes, content_type="image/png")
```

### Cookies

```python
response = Response("ok")
response.set_cookie("theme", "dark", max_age=86400, httponly=True, samesite="Lax")
response.delete_cookie("theme")
```

Each `Set-Cookie` is sent as its own header line. Cookie names and values may not
contain `;`, CR or LF; header values may not contain CR or LF (`ValueError`).

## Errors

Raise an `HTTPError` subclass anywhere in a handler:

```python
from nexusserver import NotFound, BadRequest

raise NotFound("No such note")      # 404 with body "404 No such note"
```

Available: `BadRequest` 400, `Unauthorized` 401, `Forbidden` 403, `NotFound` 404,
`MethodNotAllowed` 405, `Conflict` 409, `UnprocessableEntity` 422,
`InternalServerError` 500, or `HTTPError(message, status_code=...)` for any code.
Pass `headers={...}` to attach response headers.

Any other exception becomes `500 Internal Server Error` and is logged with a
traceback. The message is only included in the response when `Config.debug` is on.

For input checks, `nexusserver.utils.validation` provides `require_fields(data, [...])`
and `as_int(value, default=None)`, both raising `BadRequest`.
