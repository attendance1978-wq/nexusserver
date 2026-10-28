# Security

All features here use only the standard library.

## Checklist for going live

- Put NexusServer behind a TLS-terminating reverse proxy (nginx, Caddy); it has no TLS itself.
- Keep `debug` off (500 responses then never include exception details).
- Use `secure=True` on session cookies and an explicit CORS allow-list.
- Use a long random secret key from the environment (`python -c "import secrets; print(secrets.token_hex(32))"`).
- Limit request sizes (`max_request_size`, `max_header_size`) to what you need.
- Add rate limiting and put a proxy in front for slow-client (slowloris) protection.

## Password hashing

```python
from nexusserver.security import hash_password, verify_password

stored = hash_password("correct horse")        # "scrypt$16384$8$1$<salt>$<hash>", store this
verify_password("correct horse", stored)       # True (constant-time)
```

scrypt with a random 16-byte salt. Never store or log plain passwords.

## Signing

```python
from nexusserver.security import sign, unsign

token = sign(b"user:42", SECRET)               # "<payload>.<timestamp>.<signature>"
unsign(token, SECRET, max_age=3600)            # b"user:42", or None if forged/expired
```

HMAC-SHA256. The payload is **signed, not encrypted**, so do not put secrets in it.
Secrets must be at least 16 bytes.

## Signed sessions

`SignedSessionMiddleware(secret_key=...)` keeps the session in the cookie itself.
Pros: survives restarts, works across several processes, no server memory. Cons:
readable by the client (not encrypted), limited to about 4 KB, and cannot be revoked
server-side before `max_age`. For revocable sessions use `SessionMiddleware`.

```python
app.add_middleware(SignedSessionMiddleware, secret_key=SECRET, max_age=3600, secure=True)

@app.get("/")
def index(request):
    request.state["session"]["visits"] = request.state["session"].get("visits", 0) + 1
```

The cookie is only re-sent when the session changed; clearing the session deletes it.

## Basic auth

```python
app.add_middleware(BasicAuthMiddleware, users={"ada": hash_password("pw")}, realm="Admin")
# or: verify=lambda username, password: check_my_database(username, password)
```

Guards every path except `exempt_paths`. The username is in `request.state["user"]`.
Unknown users cost the same time as wrong passwords. To protect only part of an app,
wrap a separate `Application` and dispatch to it (`examples/auth_app.py`).

## Bearer tokens

```python
app.add_middleware(BearerTokenMiddleware, token="a-long-random-token", exempt_paths=("/health",))
```

`Authorization: Bearer <token>`, compared in constant time; pass a list of tokens to rotate
them. Tokens must be at least 16 characters. The nexuspy API uses this middleware.

## Rate limiting

```python
app.add_middleware(RateLimitMiddleware, limit=100, window=60, exempt_paths=("/health",))
```

Fixed window per client IP; over the limit gives `429` with `Retry-After`. Every
response carries `X-RateLimit-Limit/Remaining/Reset`. `X-Forwarded-For` is **not**
trusted by default (clients can forge it); behind a proxy, supply a `key_func`
that reads a header only your proxy sets. State is per process and in memory.

## Built-in protections

- Header values with CR/LF are rejected (response splitting); cookie values with `;`, CR or LF too.
- Static files and uploads are path-sandboxed (`safe_join`, `secure_filename`).
- Request size, header size and read-timeout limits; 431/413/408 responses.
- Default `SecurityHeadersMiddleware` (`nosniff`, `X-Frame-Options`, `Referrer-Policy`).
