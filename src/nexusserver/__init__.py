"""NexusServer: a lightweight, pure-Python web framework and HTTP server."""

from ._version import __version__
from .application import Application, NexusServer
from .config import Config
from .exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    HTTPError,
    InternalServerError,
    MethodNotAllowed,
    NexusServerError,
    NotFound,
    Unauthorized,
    UnprocessableEntity,
)
from .http.headers import Headers
from .http.request import Request
from .http.response import Response
from .routing.router import Router

__all__ = [
    "Application",
    "NexusServer",
    "Config",
    "Headers",
    "Request",
    "Response",
    "Router",
    "NexusServerError",
    "HTTPError",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "MethodNotAllowed",
    "Conflict",
    "UnprocessableEntity",
    "InternalServerError",
    "__version__",
]
