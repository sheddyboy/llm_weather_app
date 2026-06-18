"""The consistent error envelope returned by every handled :class:`AppError`.

Kept in its own module so both ``app.exceptions`` and any future router that
documents error responses can depend on the shape without a circular import.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """The body of an error response: a stable code plus a human message."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Top-level error envelope: ``{"error": {"code": ..., "message": ...}}``."""

    error: ErrorDetail
