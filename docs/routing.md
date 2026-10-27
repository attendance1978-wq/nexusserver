# Routing

```python
@app.get("/users/<int:user_id>")
def user(user_id):          # user_id is an int
    ...

@app.route("/submit", methods=["POST", "PUT"], name="submit")
def submit(request):
    ...
```

Shortcuts: `app.get`, `app.post`, `app.put`, `app.delete`. `app.route(path, methods=[...])`
handles any set of methods (default `GET`). `Router` can also be used on its own.

## Converters

| Syntax | Matches | Python type |
| --- | --- | --- |
| `<name>` or `<str:name>` | one segment (no `/`) | `str` |
| `<int:name>` | digits | `int` |
| `<path:name>` | the rest of the path, slashes included | `str` |

An unknown converter (e.g. `<uuid:id>`) raises `ValueError` when the route is
registered.

## Matching rules

- Routes are tried **in registration order**; the first match wins. Register
  specific routes before catch-alls such as `<path:rest>`.
- If the path matches but the method does not, the response is `405 Method Not
  Allowed` with an `Allow` header. If nothing matches, `404`.
- `HEAD` is answered by the matching `GET` route (headers only, no body), unless
  you register an explicit `HEAD` route.
- The request path is percent-decoded before matching (`/a%20b` matches `/a b`).
- Trailing slashes are significant: `/items` and `/items/` are different routes.

## Handler arguments

The framework inspects the signature: `request` is passed if present, and path
parameters are passed by name. Anything else in the signature must have a default.

```python
@app.get("/a/<int:x>")
def one(x): ...                    # ok
@app.get("/b/<int:x>")
def two(request, x): ...           # ok
@app.get("/c/<int:x>")
def three(): ...                   # ok, simply ignores x
```
