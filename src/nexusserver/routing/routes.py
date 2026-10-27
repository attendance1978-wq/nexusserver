"""Route definitions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from .parameters import compile_path


Handler = Callable[..., object]


@dataclass
class Route:
    path: str
    endpoint: Handler
    methods: set[str] = field(default_factory=lambda: {"GET"})
    name: str | None = None
    regex: re.Pattern[str] = field(init=False, repr=False)
    params: list[tuple[str, str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.regex, self.params = compile_path(self.path)
        self.methods = {m.upper() for m in self.methods}

    def matches(self, path: str) -> bool:
        return self.regex.match(path) is not None