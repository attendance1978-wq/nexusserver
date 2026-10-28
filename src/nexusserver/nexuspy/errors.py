"""nexuspy exceptions."""

from __future__ import annotations


class NexusPyError(Exception):
    """Base class for every nexuspy error."""


class InvalidName(NexusPyError):
    """An environment name or package spec is not acceptable."""


class EnvNotFound(NexusPyError):
    """No environment with that name exists."""


class EnvExists(NexusPyError):
    """An environment with that name already exists."""


class InterpreterNotFound(NexusPyError):
    """No matching Python interpreter was found."""


class CommandFailed(NexusPyError):
    """A subprocess (venv creation, pip, ...) exited with an error."""

    def __init__(self, message: str, returncode: int = 1, output: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.output = output
