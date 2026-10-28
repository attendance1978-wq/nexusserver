"""multipart/form-data parsing (file uploads)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..exceptions import BadRequest
from ..utils.paths import secure_filename

_BOUNDARY_RE = re.compile(r'boundary=(?:"([^"]+)"|([^;\s]+))', re.IGNORECASE)
_PARAM_RE = re.compile(r'([\w*-]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^;]*))')
MAX_PARTS = 1000


@dataclass
class UploadedFile:
    """A file sent in a multipart form."""

    filename: str
    content_type: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def safe_filename(self) -> str:
        """The client-supplied name reduced to a harmless basename."""
        return secure_filename(self.filename)

    def save(self, directory: str | Path, filename: str | None = None) -> Path:
        """Write the file into ``directory`` and return its path.

        The name is sanitised, so a client cannot write outside ``directory``.
        """
        name = secure_filename(filename) if filename else self.safe_filename
        target = Path(directory) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.data)
        return target


@dataclass
class MultipartForm:
    fields: dict[str, str] = field(default_factory=dict)
    files: dict[str, UploadedFile] = field(default_factory=dict)
    all_files: list[tuple[str, UploadedFile]] = field(default_factory=list)  # every file, repeated names included


def _params(header_value: str) -> dict[str, str]:
    out = {}
    for name, quoted, bare in _PARAM_RE.findall(header_value):
        out[name.lower()] = (quoted.replace('\\"', '"').replace("\\\\", "\\") if quoted else bare.strip())
    return out


def parse_multipart(body: bytes, content_type: str) -> MultipartForm:
    match = _BOUNDARY_RE.search(content_type or "")
    if not match:
        raise BadRequest("multipart/form-data request without a boundary")
    boundary = (match.group(1) or match.group(2)).encode("latin-1")
    delimiter = b"--" + boundary

    segments = body.split(delimiter)
    if len(segments) < 2:
        raise BadRequest("Malformed multipart body")
    form = MultipartForm()
    count = 0
    for segment in segments[1:]:
        if segment.startswith(b"--"):  # closing delimiter
            break
        count += 1
        if count > MAX_PARTS:
            raise BadRequest("Too many multipart parts")
        if segment.startswith(b"\r\n"):
            segment = segment[2:]
        if segment.endswith(b"\r\n"):
            segment = segment[:-2]
        head, sep, data = segment.partition(b"\r\n\r\n")
        if not sep:
            if segment.startswith(b"\r\n"):  # part with no headers at all
                continue
            raise BadRequest("Malformed multipart part")
        headers = {}
        for line in head.decode("utf-8", "replace").split("\r\n"):
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
        disposition = _params(headers.get("content-disposition", ""))
        name = disposition.get("name")
        if name is None:
            raise BadRequest("Multipart part without a name")
        if "filename" in disposition:
            upload = UploadedFile(
                filename=disposition["filename"],
                content_type=headers.get("content-type", "application/octet-stream"),
                data=data,
            )
            form.files[name] = upload
            form.all_files.append((name, upload))
        else:
            form.fields[name] = data.decode("utf-8", "replace")
    return form
