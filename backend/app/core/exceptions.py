"""Domain exceptions and their translation into HTTP responses.

Services raise these exceptions and never know about HTTP. The handlers registered in
`register_exception_handlers` turn them into a single error format:

    {"error": "<machine_readable_code>", "message": "<human readable message>"}
"""

import logging
from http import HTTPStatus
from typing import ClassVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    error: str = "bad_request"
    headers: ClassVar[dict[str, str] | None] = None

    def __init__(self, message: str, *, error: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error is not None:
            self.error = error


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error = "not_found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error = "unauthorized"
    # RFC 6750: 401 responses for bearer-token APIs must say how to authenticate.
    headers: ClassVar[dict[str, str] | None] = {"WWW-Authenticate": "Bearer"}


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error = "permission_denied"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource (e.g. invalid transition)."""

    status_code = status.HTTP_409_CONFLICT
    error = "conflict"


class BusinessRuleError(AppError):
    """The request is well formed but breaks a business rule (e.g. resolution missing)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error = "business_rule_violation"


def error_response(
    status_code: int,
    error: str,
    message: str,
    details: list[dict] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict = {"error": error, "message": message}
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.error, exc.message, headers=exc.headers)


async def _http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    phrase = HTTPStatus(exc.status_code).phrase
    error = phrase.lower().replace(" ", "_").replace("-", "_")
    message = exc.detail if isinstance(exc.detail, str) else phrase
    return error_response(exc.status_code, error, message, headers=exc.headers)


def _field_name(loc: tuple) -> str:
    # Skip the location prefix ("body", "query"...) so clients get the field path.
    if len(loc) > 1 and loc[0] in {"body", "query", "path", "header", "cookie"}:
        loc = loc[1:]
    return ".".join(str(part) for part in loc)


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "field": _field_name(err["loc"]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "Invalid request", details
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback goes to the logs only; the client gets a generic message.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred"
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
