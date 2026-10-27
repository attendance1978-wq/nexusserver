# NexusServer

A lightweight, pure-Python HTTP server and web framework: routing, middleware,
cookies, sessions, SQLite helpers. No dependencies beyond the standard library.

**Version 26.2.0** (see [CHANGELOG](CHANGELOG.md)) · Python 3.9+ · MIT

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

- Threaded HTTP/1.1 server (one request per connection)
- Decorator routing with `<int:id>`, `<str:name>`, `<path:rest>`
- Handlers return `str`, `bytes`, `dict`/`list` (JSON), `Response`, or `(body, status[, headers])`
- Middleware: CORS, security headers, sessions, gzip, request logging (+ your own)
- Cookies, form and JSON bodies, query strings
- SQLite helper with one-shot, idempotent migrations
- Static file helpers with path-traversal protection

## Documentation

| Guide | Covers |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, first app, CLI, running tests |
| [Routing](docs/routing.md) | Paths, converters, methods, HEAD/405 behaviour |
| [Requests and responses](docs/requests-and-responses.md) | Request API, return values, cookies, errors |
| [Middleware](docs/middleware.md) | Built-ins, options, ordering, writing your own |
| [Database](docs/database.md) | SQLite, migrations, threading |
| [Configuration](docs/configuration.md) | `Config` fields and CLI flags |
| [Limitations](docs/limitations.md) | What it does not do yet, production notes |

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

## Tests

```bash
pip install pytest
pytest
```