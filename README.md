# NexusServer

A lightweight, pure-Python HTTP server and web framework: routing, middleware,
cookies, sessions, SQLite helpers. No dependencies beyond the standard library.

**Version 26.4.0** · latest LTS line: 26.3.x (see [CHANGELOG](CHANGELOG.md) and the [release policy](docs/release-policy.md)) · Python 3.9+ · MIT

## Install

```bash
pip install -e .
```

## Quick start

```python
from nexusserver import Application

app = Application()

@app.get("/")
def index(request):
    return "Hello, world!"

if __name__ == "__main__":
    app.run()
```

Run it with the CLI (the target is `module:attribute`):

```bash
python -m nexusserver examples.hello_server:app --port 8080
# or, after pip install:
nexusserver examples.hello_server:app --port 8080
```

## Features

- Threaded HTTP/1.1 server with keep-alive, pipelining and chunked request bodies
- **nexuspy**: Python environment manager (create/clone/lock environments, run commands in them, HTTP API)
- Auto-reload for development (`--reload`)
- Decorator routing with `<int:id>`, `<str:name>`, `<path:rest>`
- Handlers return `str`, `bytes`, `dict`/`list` (JSON), `Response`, or `(body, status[, headers])`
- Middleware: CORS, security headers, sessions (in-memory or signed cookies), rate limiting, Basic auth, gzip, request logging (+ your own)
- Custom error handlers: `@app.errorhandler(404)`
- File uploads (`request.multipart()`) and `app.static()` mounts with ETag/304
- Password hashing and signing helpers (`nexusserver.security`)
- Cookies, form and JSON bodies, query strings
- SQLite helper with one-shot, idempotent migrations

## Documentation

| Guide | Covers |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, first app, CLI, running tests |
| [Routing](docs/routing.md) | Paths, converters, methods, HEAD/405 behaviour |
| [Requests and responses](docs/requests-and-responses.md) | Request API, return values, cookies, errors |
| [Middleware](docs/middleware.md) | Built-ins, options, ordering, writing your own |
| [Database](docs/database.md) | SQLite, migrations, threading |
| [Configuration](docs/configuration.md) | `Config` fields and CLI flags |
| [nexuspy](docs/nexuspy.md) | Python environment management: CLI, Python API, HTTP API |
| [Uploads and static files](docs/uploads-and-static.md) | multipart forms, `app.static()` |
| [Security](docs/security.md) | Passwords, signed sessions, Basic auth, rate limiting, checklist |
| [Release policy](docs/release-policy.md) | LTS support window, upgrade notes |
| [Limitations](docs/limitations.md) | What it does not do, production notes |

## Examples

All in [`examples/`](examples/), each runnable with `python -m nexusserver examples.<name>:app`:

| File | Shows |
| --- | --- |
| `hello_server.py` | Minimal app |
| `routes.py` | Path params, query strings, redirects, custom status/headers |
| `json_api.py` | In-memory CRUD with GET/POST/PUT/DELETE and validation |
| `static_site.py` | Safe static file serving |
| `database_app.py` | Basic SQLite usage |
| `sessions_app.py` | Sessions, login/logout |
| `middleware_app.py` | Configured CORS + gzip and a custom middleware |
| `notes_api.py` | Everything together: migrations, lifecycle hooks, CORS, validation |
| `upload_app.py` | multipart file uploads with size and type checks |
| `auth_app.py` | Password hashing, signed sessions, Basic auth for an admin area |
| `error_handlers.py` | Custom JSON errors by status, class, and catch-all |
| `rate_limit_app.py` | Rate limiting with an exempt health check |
| `static_mount.py` | `app.static()` with caching headers |

## nexuspy in 30 seconds

```bash
nexuspy create web flask            # new environment with Flask installed
nexuspy run web -- python -c "import flask; print(flask.__version__)"
nexuspy lock web                    # writes nexuspy.lock
nexuspy clone web web-copy
```

## Tests

```bash
pip install pytest
pytest
```
