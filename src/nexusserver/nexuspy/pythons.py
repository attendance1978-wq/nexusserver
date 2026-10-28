"""Discover and select Python interpreters."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from .errors import InterpreterNotFound

_PROBE = "import sys; print('.'.join(map(str, sys.version_info[:3])))"


@dataclass(frozen=True)
class PythonInfo:
    path: str
    version: str

    @property
    def version_info(self) -> tuple[int, ...]:
        return tuple(int(part) for part in self.version.split("."))

    def to_dict(self) -> dict:
        return asdict(self)


def probe(path: str | os.PathLike) -> PythonInfo | None:
    """Run ``path`` and report its version, or ``None`` if it is not a working Python 3."""
    try:
        out = subprocess.run([str(path), "-c", _PROBE], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    version = out.stdout.strip()
    if out.returncode != 0 or not version.startswith("3."):
        return None
    try:
        tuple(int(p) for p in version.split("."))
    except ValueError:
        return None
    return PythonInfo(path=str(path), version=version)


def _candidate_names() -> list[str]:
    suffix = ".exe" if os.name == "nt" else ""
    names = ["python", "python3"] + [f"python3.{minor}" for minor in range(8, 21)]
    return [n + suffix for n in names]


def discover_pythons(extra_dirs: tuple[str, ...] = ()) -> list[PythonInfo]:
    """Find Python 3 interpreters on ``PATH`` (plus ``extra_dirs`` and the running one).

    Results are de-duplicated by real path and sorted newest first.
    """
    seen: set[str] = set()
    found: list[PythonInfo] = []

    def consider(path: str) -> None:
        real = os.path.realpath(path)
        if real in seen or not os.path.isfile(path) or not os.access(path, os.X_OK):
            return
        seen.add(real)
        info = probe(path)
        if info:
            found.append(info)

    dirs = list(extra_dirs) + os.environ.get("PATH", "").split(os.pathsep)
    for directory in dirs:
        if not directory:
            continue
        for name in _candidate_names():
            consider(str(Path(directory) / name))
    for own in (getattr(sys, "_base_executable", None), sys.executable):
        if own:
            consider(own)
    return sorted(found, key=lambda info: info.version_info, reverse=True)


def current_python() -> PythonInfo:
    """The interpreter running nexuspy (its base interpreter if inside a venv)."""
    path = getattr(sys, "_base_executable", None) or sys.executable
    info = probe(path) or probe(sys.executable)
    if info is None:  # pragma: no cover - extremely unusual
        raise InterpreterNotFound("Could not run the current Python interpreter")
    return info


def find_python(spec: str | None) -> PythonInfo:
    """Resolve ``spec`` to an interpreter.

    ``spec`` may be ``None`` (the running Python), a path to an executable, or a
    version prefix such as ``"3.11"`` or ``"3.12.3"`` (an optional leading
    ``python`` is ignored).
    """
    if not spec:
        return current_python()
    if os.path.sep in spec or (os.altsep and os.altsep in spec) or os.path.isfile(spec):
        info = probe(spec)
        if info is None:
            raise InterpreterNotFound(f"{spec!r} is not a working Python 3 interpreter")
        return info
    wanted = spec.lower().removeprefix("python")
    for info in discover_pythons():
        if info.version == wanted or info.version.startswith(wanted + "."):
            return info
    raise InterpreterNotFound(f"No Python matching {spec!r} found. Run 'nexuspy pythons' to see what is available.")
