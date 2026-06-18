"""Pydantic request/response schemas for the API surface."""

from app.schemas.error import ErrorDetail, ErrorResponse
from app.schemas.media import MediaResponse, PointOfInterest, VideoItem
from app.schemas.records import (
    DailyReadingRead,
    LocationRead,
    RecordCreate,
    RecordUpdate,
    WeatherRecordRead,
)
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastDay,
    ForecastResponse,
)

__all__ = [
    "CurrentWeather",
    "CurrentWeatherResponse",
    "DailyReadingRead",
    "ErrorDetail",
    "ErrorResponse",
    "ForecastDay",
    "ForecastResponse",
    "LocationRead",
    "MediaResponse",
    "PointOfInterest",
    "RecordCreate",
    "RecordUpdate",
    "VideoItem",
    "WeatherRecordRead",
]
