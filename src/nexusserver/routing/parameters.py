"""URL parameter extraction."""

from __future__ import annotations

import re

from .converters import CONVERTERS

_PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")


def compile_path(path: str) -> tuple[re.Pattern[str], list[tuple[str, str]]]:
    """Compile a route path with `<converter:name>` placeholders."""
    parts: list[str] = ["^"]
    params: list[tuple[str, str]] = []
    last = 0
    for match in _PARAM_RE.finditer(path):
        parts.append(re.escape(path[last:match.start()]))
        converter_name = match.group(1) or "str"
        param_name = match.group(2)
        converter = CONVERTERS.get(converter_name)
        if converter is None:
            raise ValueError(f"Unknown converter: {converter_name!r}")
        parts.append(f"(?P<{param_name}>{converter.regex})")
        params.append((param_name, converter_name))
        last = match.end()
    parts.append(re.escape(path[last:]))
    parts.append("$")
    return re.compile("".join(parts)), params


def extract_params(regex: re.Pattern[str], params: list[tuple[str, str]], path: str) -> dict:
    match = regex.match(path)
    if not match:
        return {}
    result = {}
    for name, converter_name in params:
        converter = CONVERTERS[converter_name]
        result[name] = converter.to_python(match.group(name))
    return result