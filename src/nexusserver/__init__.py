"""NexusServer: a lightweight, pure-Python web framework and HTTP server."""

from ._version import LTS, RELEASE_CHANNEL, __version__, __version_info__
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
from .http.multipart import MultipartForm, UploadedFile
from .routing.router import Router
from .staticfiles import StaticFiles

__all__ = [
    "Application",
    "NexusServer",
    "Config",
    "Headers",
    "Request",
    "Response",
    "Router",
    "StaticFiles",
    "MultipartForm",
    "UploadedFile",
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
    "__version_info__",
    "LTS",
    "RELEASE_CHANNEL",
]
