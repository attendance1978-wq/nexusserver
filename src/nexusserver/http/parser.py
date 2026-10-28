"""HTTP/1.1 request parsing."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from ..exceptions import BadRequest, NotImplementedError_, PayloadTooLarge
from .chunked import dechunk
from .headers import Headers
from .request import Request

_REQUEST_LINE_RE = re.compile(r"^([A-Z]+)\s+(\S+)\s+(HTTP/\d\.\d)$")


def parse_request_line(line: str) -> tuple[str, str, str]:
    match = _REQUEST_LINE_RE.match(line.strip())
    if not match:
        raise BadRequest("Malformed request line")
    method, target, version = match.groups()
    return method, target, version


def parse_headers(lines: list[str]) -> Headers:
    headers = Headers()
    for line in lines:
        if not line:
            continue
        if ":" not in line:
            raise BadRequest("Malformed header line")
        name, _, value = line.partition(":")
        headers.add(name.strip(), value.strip())
    return headers


def parse_request(
    raw: bytes,
    client: tuple[str, int] | None = None,
    max_body_size: int = 16 * 1024 * 1024,
) -> Request:
    header_end = raw.find(b"\r\n\r\n")
    if header_end == -1:
        raise BadRequest("Incomplete headers")
    head = raw[:header_end].decode("iso-8859-1")
    body = raw[header_end + 4:]

    lines = head.split("\r\n")
    method, target, version = parse_request_line(lines[0])
    headers = parse_headers(lines[1:])

    transfer_encoding = headers.get("Transfer-Encoding", "").strip().lower()
    if transfer_encoding:
        if transfer_encoding != "chunked":
            raise NotImplementedError_("Only 'chunked' Transfer-Encoding is supported")
        if "Content-Length" in headers:
            raise BadRequest("Both Transfer-Encoding and Content-Length were sent")
        decoded = dechunk(body, max_body_size)
        if decoded is None:
            raise BadRequest("Incomplete chunked body")
        body = decoded[0]
    else:
        try:
            content_length = int(headers.get("Content-Length", "0") or 0)
        except ValueError:
            raise BadRequest("Invalid Content-Length") from None
        if content_length < 0:
            raise BadRequest("Invalid Content-Length")
        if content_length > max_body_size:
            raise PayloadTooLarge("Request body too large")
        if len(body) < content_length:
            raise BadRequest("Incomplete request body")
        body = body[:content_length]  # no Content-Length => no body

    parts = urlsplit(target)
    return Request(
        method=method,
        path=unquote(parts.path) or "/",
        query_string=parts.query,
        headers=headers,
        body=body,
        client=client,
        http_version=version,
        scheme="http",
    )
