# Changelog

## 26.2.0

Versioning is now CalVer (`YY.minor.patch`). The version lives in one place,
`src/nexusserver/_version.py`; `pyproject.toml` reads it from there. This also
removes the old mismatch (`0.1.0` in `__init__`/`pyproject`, `0.1.2` in a stray
`___init___.py`).

### Fixed
- **Request bodies could be truncated.** The server stopped reading after the
  headers, so a body arriving in a later packet (or a large upload) was cut off.
  It now reads the full body according to `Content-Length`, and answers
  `Expect: 100-continue`.
- **Multiple `Set-Cookie` headers were merged into one comma-joined line**, which
  browsers cannot parse. Headers now keep one entry per value; use
  `Headers.raw_items()` / `get_all()`.
- **Malformed requests returned 500.** They now return the right 4xx (400, 408,
  413, 431, 501).
- **`bytes` return values** were rendered as the string `"b'...'"`.
- **`add_middleware` could not pass options**, so `CORSMiddleware` etc. could
  only run with defaults. Use `app.add_middleware(CORSMiddleware, allow_origins=[...])`.
- **Packaging:** `http`, `routing` and `utils` had no `__init__.py`, so they were
  left out of built wheels.
- **Migrations re-ran every time.** `apply_migrations` now records applied
  migrations and is safe to call on every start-up.
- **The `nexusserver` console script** could not import modules from the working
  directory.
- **405 responses** now include the required `Allow` header.
- Sessions: the store is per-middleware instance (was shared by all apps) and is
  lock-protected.
- Unexpected exceptions in handlers become a clean 500 and no longer leak
  details unless `debug` is on.
- Example `static_site.py` used a string-prefix path check that sibling
  directories could bypass; it now uses `safe_join`.
- Examples and tests used `src.nexusserver` imports (and one a broken relative
  import) and lived outside `examples/`; they now use `from nexusserver import ...`.
- `tests/test_http.py` declared `Content-Length: 13` for a 12-byte body.

### Added
- `Application.on_startup` / `on_shutdown` decorators.
- `add_middleware(cls, **options)`; the middleware chain is cached.
- `HEAD` is served by `GET` routes automatically (no body sent).
- `Response.text()`, `Response.delete_cookie()`; `Conflict` and
  `UnprocessableEntity` exceptions; `HTTPError(headers=...)`; status 431.
- `Config.max_header_size`; CLI flags `--debug`, `--workers`, `--version`.
- `HTTPEngine.ready` and `.address` (handy with `port=0` in tests).
- Header values are rejected if they contain CR/LF (response splitting), and
  cookie values if they contain `;`, CR or LF.
- Request paths are percent-decoded.
- Docs (`docs/`), 8 examples, and a 53-test suite including end-to-end socket tests.

### Changed
- `Headers.__getitem__` still returns values comma-joined, but `get_all()` now
  returns each added value rather than splitting on commas.
- A request with no `Content-Length` has an empty body (it used to keep stray bytes).
- `Transfer-Encoding` request bodies (chunked) are rejected with 501 instead of
  being silently mis-read.
- `Config.keep_alive` now defaults to `False` (connections were always closed
  after one response; the old default was misleading).
- Sessions are configured by constructor options (`cookie_name`, `max_age`,
  `secure`) rather than a class attribute.

### Known limitations
See [docs/limitations.md](docs/limitations.md): `--reload` is accepted but not
implemented, and there is no TLS, keep-alive, or chunked-body support.
