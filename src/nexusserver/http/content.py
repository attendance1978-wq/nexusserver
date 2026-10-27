"""Content types and body handling."""

from __future__ import annotations

import json
from typing import Any


JSON = "application/json"
HTML = "text/html; charset=utf-8"
TEXT = "text/plain; charset=utf-8"
FORM = "application/x-www-form-urlencoded"
MULTIPART = "multipart/form-data"


def json_body(data: Any) -> bytes:
    return json.dumps(data).encode("utf-8")