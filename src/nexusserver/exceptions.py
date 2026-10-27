"""Framework-specific exceptions."""

from __future__ import annotations

from .http.status import HTTPStatus


class NexusServerError(Exception):
    """Base exception for all NexusServer errors."""


class HTTPError(NexusServerError):
    """An exception that maps to an HTTP response."""

    status_code: int = 500
    default_message: str = "Internal Server Error"

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.headers = dict(headers or {})
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class BadRequest(HTTPError):
    status_code = 400
    default_message = "Bad Request"


class Unauthorized(HTTPError):
    status_code = 401
    default_message = "Unauthorized"


class Forbidden(HTTPError):
    status_code = 403
    default_message = "Forbidden"


class NotFound(HTTPError):
    status_code = 404
    default_message = "Not Found"


class MethodNotAllowed(HTTPError):
    status_code = 405
    default_message = "Method Not Allowed"


class RequestTimeout(HTTPError):
    status_code = 408
    default_message = "Request Timeout"


class Conflict(HTTPError):
    status_code = 409
    default_message = "Conflict"


class PayloadTooLarge(HTTPError):
    status_code = 413
    default_message = "Payload Too Large"


class UnprocessableEntity(HTTPError):
    status_code = 422
    default_message = "Unprocessable Entity"


class InternalServerError(HTTPError):
    status_code = 500
    default_message = "Internal Server Error"


class NotImplementedError_(HTTPError):
    status_code = 501
    default_message = "Not Implemented"