"""Custom application exceptions and their FastAPI handlers.

Per ARCHITECTURE §8, provider and domain failures are surfaced as a small set of
custom exceptions that map to a consistent JSON error shape, rather than letting
raw provider exceptions (httpx errors, SQLAlchemy errors, etc.) leak through the
API. Every exception below carries an HTTP ``status_code`` and a stable, machine
-readable ``code`` alongside its human-readable message.

The serialized shape is::

    {"error": {"code": "location_not_found", "message": "..."}}

which is described by ``app.schemas.error.ErrorResponse``.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.schemas.error import ErrorDetail, ErrorResponse


class AppError(Exception):
    """Base class for application errors mapped to JSON error responses.

    Subclasses set ``status_code`` and ``code``; the message is supplied per
    instance (falling back to ``default_message``).
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class LocationNotFoundError(AppError):
    """No geocoding match, or a fuzzy match below the confidence threshold."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "location_not_found"
    default_message = "No matching location could be found."


class RecordNotFoundError(AppError):
    """No stored weather record exists for the requested id.

    Intrinsic to the records CRUD surface (GET/PATCH/DELETE of a missing id):
    it reuses the shared error envelope rather than FastAPI's default
    ``{"detail": ...}`` shape, keeping every error response consistent.
    """

    status_code = status.HTTP_404_NOT_FOUND
    code = "record_not_found"
    default_message = "No weather record could be found with the given id."


class InvalidDateRangeError(AppError):
    """The requested date range is invalid (end before start, too large, etc.)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_date_range"
    default_message = "The requested date range is invalid."


class WeatherProviderError(AppError):
    """OpenWeatherMap (or another weather provider) failed to respond usefully."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "weather_provider_error"
    default_message = "The weather provider is currently unavailable."


class ExternalAPIQuotaExceededError(AppError):
    """A YouTube or Places quota/billing limit was hit.

    The ``/media`` endpoint degrades gracefully rather than failing (ARCHITECTURE
    §6); this exception exists for the cases where the limit must still surface.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "external_api_quota_exceeded"
    default_message = "An external API quota or billing limit has been reached."


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Render any :class:`AppError` as the consistent JSON error envelope."""
    logger.warning(
        "{} on {} {}: {}",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.message,
    )
    body = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's exception handlers on ``app``.

    A single handler keyed on the :class:`AppError` base covers every subclass,
    so new error types map to the shared shape automatically.
    """
    app.add_exception_handler(AppError, app_error_handler)
