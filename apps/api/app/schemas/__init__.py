"""Pydantic request/response schemas for the API surface."""

from app.schemas.error import ErrorDetail, ErrorResponse
from app.schemas.records import (
    DailyReadingRead,
    LocationRead,
    RecordCreate,
    RecordUpdate,
    WeatherRecordRead,
)

__all__ = [
    "DailyReadingRead",
    "ErrorDetail",
    "ErrorResponse",
    "LocationRead",
    "RecordCreate",
    "RecordUpdate",
    "WeatherRecordRead",
]
