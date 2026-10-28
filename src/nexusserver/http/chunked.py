"""Chunked transfer-coding decoder (request bodies)."""

from __future__ import annotations

from ..exceptions import BadRequest, PayloadTooLarge


def dechunk(data: bytes, max_size: int | None = None) -> tuple[bytes, int] | None:
    """Decode a chunked body from the start of ``data``.

    Returns ``(body, consumed_bytes)`` when the terminating chunk (and trailers)
    are present, or ``None`` if more data is needed. Raises ``BadRequest`` on
    malformed input and ``PayloadTooLarge`` past ``max_size``.
    """
    pos = 0
    parts: list[bytes] = []
    total = 0
    while True:
        line_end = data.find(b"\r\n", pos)
        if line_end == -1:
            if len(data) - pos > 1024:
                raise BadRequest("Malformed chunk header")
            return None
        size_text = data[pos:line_end].split(b";", 1)[0].strip()
        try:
            size = int(size_text, 16)
        except ValueError:
            raise BadRequest("Malformed chunk size") from None
        if size < 0:
            raise BadRequest("Malformed chunk size")
        pos = line_end + 2
        if size == 0:
            # optional trailers, ended by an empty line
            while True:
                end = data.find(b"\r\n", pos)
                if end == -1:
                    return None
                if end == pos:
                    return b"".join(parts), end + 2
                pos = end + 2
        total += size
        if max_size is not None and total > max_size:
            raise PayloadTooLarge("Request body too large")
        if len(data) < pos + size + 2:
            return None
        if data[pos + size:pos + size + 2] != b"\r\n":
            raise BadRequest("Malformed chunk terminator")
        parts.append(data[pos:pos + size])
        pos += size + 2
