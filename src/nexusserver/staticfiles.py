"""Static file serving with caching headers."""

from __future__ import annotations

import time
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path

from .exceptions import NotFound
from .http.request import Request
from .http.response import Response
from .utils.mime import guess_mime
from .utils.paths import safe_join


class StaticFiles:
    """Serve a directory. Sends ``ETag`` / ``Last-Modified`` and answers 304 to conditional requests."""

    def __init__(self, directory: str | Path, index: str | None = "index.html",
                 max_age: int = 3600) -> None:
        self.root = Path(directory).resolve()
        self.index = index
        self.max_age = max_age

    def serve(self, request: Request, relative: str = "") -> Response:
        try:
            target = safe_join(self.root, relative)
        except ValueError:
            raise NotFound() from None
        if target.is_dir() and self.index:
            target = target / self.index
        if not target.is_file():
            raise NotFound()

        stat = target.stat()
        etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        headers = {
            "ETag": etag,
            "Last-Modified": formatdate(stat.st_mtime, usegmt=True),
            "Cache-Control": f"public, max-age={self.max_age}",
        }
        if self._not_modified(request, etag, stat.st_mtime):
            return Response(b"", status_code=304, headers=headers, content_type=None)
        return Response(target.read_bytes(), headers=headers, content_type=guess_mime(target.name))

    @staticmethod
    def _not_modified(request: Request, etag: str, mtime: float) -> bool:
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match:
            candidates = {t.strip().removeprefix("W/") for t in if_none_match.split(",")}
            return "*" in candidates or etag in candidates
        since = request.headers.get("If-Modified-Since")
        if since:
            try:
                return int(mtime) <= parsedate_to_datetime(since).timestamp()
            except (TypeError, ValueError):
                return False
        return False
