"""HTTP request object."""

from __future__ import annotations

from typing import Any

from .headers import Headers


class Request:
    def __init__(
        self,
        method: str,
        path: str,
        query_string: str = "",
        headers: Headers | None = None,
        body: bytes = b"",
        client: tuple[str, int] | None = None,
        http_version: str = "HTTP/1.1",
        scheme: str = "http",
    ) -> None:
        self.method = method.upper()
        self.path = path
        self.raw_path = path
        self.query_string = query_string
        self.headers = headers or Headers()
        self.body = body
        self.client = client
        self.http_version = http_version
        self.scheme = scheme
        self.path_params: dict[str, Any] = {}
        self.state: dict[str, Any] = {}

    @property
    def query(self) -> dict[str, str]:
        from urllib.parse import parse_qs

        parsed = parse_qs(self.query_string, keep_blank_values=True)
        return {k: v[0] for k, v in parsed.items()}

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", "")

    @property
    def cookies(self) -> dict[str, str]:
        from .cookies import parse_cookie_header

        return parse_cookie_header(self.headers.get("Cookie", ""))

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding)

    def json(self) -> Any:
        import json

        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))

    def form(self) -> dict[str, str]:
        from urllib.parse import parse_qs

        parsed = parse_qs(self.body.decode("utf-8"), keep_blank_values=True)
        return {k: v[0] for k, v in parsed.items()}

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"