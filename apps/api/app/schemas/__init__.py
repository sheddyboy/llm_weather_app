"""Pydantic request/response schemas for the API surface."""

from app.schemas.briefing import BriefingResponse
from app.schemas.error import ErrorDetail, ErrorResponse
from app.schemas.media import MediaResponse, PointOfInterest, VideoItem
from app.schemas.meta import MetaResponse
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
    "BriefingResponse",
    "CurrentWeather",
    "CurrentWeatherResponse",
    "DailyReadingRead",
    "ErrorDetail",
    "ErrorResponse",
    "ForecastDay",
    "ForecastResponse",
    "LocationRead",
    "MediaResponse",
    "MetaResponse",
    "PointOfInterest",
    "RecordCreate",
    "RecordUpdate",
    "VideoItem",
    "WeatherRecordRead",
]
