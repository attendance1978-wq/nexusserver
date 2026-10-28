"""Security helpers: signing and password hashing (standard library only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key(secret: str | bytes) -> bytes:
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    if len(key) < 16:
        raise ValueError("secret key must be at least 16 bytes long")
    return key


def sign(value: bytes, secret: str | bytes) -> str:
    """Return ``<value>.<timestamp>.<signature>`` (all URL-safe)."""
    body = f"{_b64e(value)}.{int(time.time())}"
    mac = hmac.new(_key(secret), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64e(mac)}"


def unsign(token: str, secret: str | bytes, max_age: float | None = None) -> bytes | None:
    """Verify ``token``; return the original bytes, or ``None`` if invalid, tampered or expired."""
    try:
        payload, stamp, signature = token.split(".")
        expected = hmac.new(_key(secret), f"{payload}.{stamp}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(signature)):
            return None
        if max_age is not None and time.time() - int(stamp) > max_age:
            return None
        return _b64d(payload)
    except (ValueError, TypeError):
        return None


_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a random salt. Store the returned string."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Check ``password`` against a :func:`hash_password` string in constant time."""
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=_b64d(salt), n=int(n), r=int(r), p=int(p),
        )
        return hmac.compare_digest(candidate, _b64d(digest))
    except (ValueError, TypeError):
        return False
