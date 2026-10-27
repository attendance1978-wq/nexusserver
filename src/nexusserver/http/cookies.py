"""Cookie parsing and serialization."""

from __future__ import annotations

from http.cookies import SimpleCookie


def parse_cookie_header(header: str) -> dict[str, str]:
    if not header:
        return {}
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(header)
    except Exception:
        return {}
    return {k: morsel.value for k, morsel in jar.items()}


def serialize_cookie(
    name: str,
    value: str,
    max_age: int | None = None,
    path: str = "/",
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str | None = "Lax",
) -> str:
    for text in (name, value):
        if any(ch in text for ch in ";\r\n"):
            raise ValueError("Cookie names and values must not contain ';', CR or LF")
    parts = [f"{name}={value}"]
    if max_age is not None:
        parts.append(f"Max-Age={max_age}")
    if path:
        parts.append(f"Path={path}")
    if domain:
        parts.append(f"Domain={domain}")
    if secure:
        parts.append("Secure")
    if httponly:
        parts.append("HttpOnly")
    if samesite:
        parts.append(f"SameSite={samesite}")
    return "; ".join(parts)