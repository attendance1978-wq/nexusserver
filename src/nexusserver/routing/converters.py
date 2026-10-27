"""URL parameter converters."""

from __future__ import annotations

from typing import Any


class Converter:
    regex: str = "[^/]+"

    def to_python(self, value: str) -> Any:
        return value

    def to_string(self, value: Any) -> str:
        return str(value)


class StringConverter(Converter):
    regex = "[^/]+"


class IntegerConverter(Converter):
    regex = r"\d+"

    def to_python(self, value: str) -> int:
        return int(value)


class PathConverter(Converter):
    regex = ".+"

    def to_python(self, value: str) -> str:
        return value


CONVERTERS: dict[str, Converter] = {
    "str": StringConverter(),
    "int": IntegerConverter(),
    "path": PathConverter(),
}