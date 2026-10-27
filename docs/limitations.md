# Limitations and production notes

NexusServer is a small, readable server, best for learning, prototypes, tools and
internal services. Know what it does not do:

- **No TLS.** Put it behind a reverse proxy (nginx, Caddy) for HTTPS.
- **One request per connection.** `Connection: close` on every response; no keep-alive.
- **No chunked or streaming request bodies** (`Transfer-Encoding` gets 501), and responses are fully buffered in memory.
- **No HTTP/2, WebSockets or async.** Concurrency is a thread pool (`max_workers`).
- **`--reload` / `Config.reload` is not implemented.**
- **Sessions are in-memory** and never expire server-side.
- **Only the first value of a repeated query/form key** is exposed (`request.query`, `request.form()`).
- **No multipart/form-data parsing** and no built-in file uploads.
- **No rate limiting or authentication.** Add your own middleware.

If you expose it to the internet, use a reverse proxy, set `secure=True` on session
cookies, keep `debug` off, and pick an explicit CORS allow-list.
