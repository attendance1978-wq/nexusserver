"""MIME type utilities."""

from __future__ import annotations

import mimetypes

mimetypes.init()


def guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"