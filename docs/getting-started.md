# Getting started

## Install

```bash
git clone https://github.com/attendance1978-wq/nexusserver && cd nexusserver
pip install -e .
```

Python 3.9 or newer. There are no runtime dependencies.

## Your first app

```python
# hello.py
from nexusserver import Application

app = Application()

@app.get("/")
def index():
    return "Hello, world!"

@app.get("/greet/<str:name>")
def greet(name):
    return {"hello": name}

if __name__ == "__main__":
    app.run()          # http://127.0.0.1:8000
```

Handlers declare only what they need. Add a `request` parameter to receive the
`Request`; add parameters named after path placeholders to receive them.

## Running

```bash
python hello.py                              # app.run()
python -m nexusserver hello:app --port 8080  # CLI; target is module:attribute
nexusserver hello:app --host 0.0.0.0 --debug # console script (after pip install)
```

The CLI adds the current directory to `sys.path`, so `module:app` works from
your project root. If the attribute is omitted (`hello`), `app` is used.

## Testing without a socket

`Application.handle()` runs a request through middleware and routing:

```python
from nexusserver.http.request import Request

response = app.handle(Request("GET", "/greet/Ada"))
assert response.status_code == 200
assert response.body == b'{"hello": "Ada"}'
```

For a real network test, start `HTTPEngine` on port 0 (see `tests/test_server.py`).

## Running this project's tests

```bash
pip install pytest
pytest
```

## Next

[Routing](routing.md) · [Requests and responses](requests-and-responses.md) ·
[Middleware](middleware.md) · [Database](database.md)
