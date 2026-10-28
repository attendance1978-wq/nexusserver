# Limitations and production notes

NexusServer is a small, readable server, best for learning, prototypes, tools and
internal services. Know what it does not do:

- **No TLS.** Put it behind a reverse proxy (nginx, Caddy) for HTTPS.
- **Threaded, not async.** Concurrency is a thread pool (`max_workers`), and idle
  keep-alive connections hold a worker (see [configuration](configuration.md)).
- **Responses are fully buffered** in memory; request bodies too (uploads included).
- **No HTTP/2 or WebSockets.**
- **`Content-Encoding` on request bodies** is not decoded; only `Transfer-Encoding: chunked` is.
- **`--reload` is polling-based** and watches `.py` files only.
- **`SessionMiddleware` is in-memory** and never expires entries server-side;
  `SignedSessionMiddleware` cannot revoke a session before it expires.
- **Rate limiting is per process** and in memory.
- **Only the first value of a repeated query/form key** is exposed (`request.query`, `request.form()`).
- **No range requests** for static files.
- **No built-in user database or CSRF protection.**

See [security](security.md) before exposing it to the internet.
