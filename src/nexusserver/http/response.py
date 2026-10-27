"""HTTP response object."""

from __future__ import annotations

import json as _json
from typing import Any

from .headers import Headers
from .status import HTTPStatus


class Response:
    def __init__(
        self,
        body: bytes | str | None = b"",
        status_code: int = 200,
        headers: Headers | dict[str, str] | None = None,
        content_type: str | None = "text/plain; charset=utf-8",
    ) -> None:
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.body: bytes = body or b""
        self.status_code = int(status_code)
        self.headers = headers if isinstance(headers, Headers) else Headers((headers or {}).items())
        if content_type and "content-type" not in self.headers:
            self.headers["Content-Type"] = content_type

    @property
    def status_phrase(self) -> str:
        return HTTPStatus.phrase_for(self.status_code)

    def set_cookie(
        self,
        name: str,
        value: str,
        max_age: int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = "Lax",
    ) -> None:
        from .cookies import serialize_cookie

        cookie = serialize_cookie(
            name, value, max_age=max_age, path=path, domain=domain,
            secure=secure, httponly=httponly, samesite=samesite,
        )
        self.headers.add("Set-Cookie", cookie)

    def delete_cookie(self, name: str, path: str = "/", domain: str | None = None) -> None:
        """Ask the client to drop a cookie."""
        self.set_cookie(name, "", max_age=0, path=path, domain=domain)

    @classmethod
    def text(cls, text: str, status_code: int = 200, headers: dict[str, str] | None = None) -> "Response":
        return cls(body=text, status_code=status_code, headers=headers)

    @classmethod
    def json(cls, data: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> "Response":
        body = _json.dumps(data).encode("utf-8")
        merged = {"Content-Type": "application/json; charset=utf-8"}
        if headers:
            merged.update(headers)
        return cls(body=body, status_code=status_code, headers=merged)

    @classmethod
    def html(cls, text: str, status_code: int = 200, headers: dict[str, str] | None = None) -> "Response":
        return cls(
            body=text.encode("utf-8"),
            status_code=status_code,
            headers=headers,
            content_type="text/html; charset=utf-8",
        )

    @classmethod
    def redirect(cls, location: str, status_code: int = 302) -> "Response":
        return cls(body=b"", status_code=status_code, headers={"Location": location})

    def __repr__(self) -> str:
        return f"<Response {self.status_code} {self.status_phrase}>"