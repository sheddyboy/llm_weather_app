"""Live weather lookups (`/weather/*`), not persisted.

Each endpoint resolves the free-text ``location`` to coordinates (persisting the
location in the permanent geocoding cache as a side effect) and returns the
cache-first provider payload. Nothing here is written to the records tables; for
a stored, range-bounded record use ``POST /records`` instead.
"""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_geocoding_service, get_weather_provider
from app.schemas import LocationRead
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastDay,
    ForecastResponse,
)
from app.services import GeocodingService, WeatherProvider

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current", response_model=CurrentWeatherResponse)
async def current_weather(
    location: str = Query(min_length=1, description="Free-text location query."),
    geocoding: GeocodingService = Depends(get_geocoding_service),
    provider: WeatherProvider = Depends(get_weather_provider),
) -> CurrentWeatherResponse:
    """Live current weather for a location."""
    resolved = await geocoding.resolve(location)
    current = await provider.get_current_weather(
        float(resolved.latitude), float(resolved.longitude)
    )
    return CurrentWeatherResponse(
        location=LocationRead.model_validate(resolved),
        current=CurrentWeather(**current),
    )


@router.get("/forecast", response_model=ForecastResponse)
async def forecast(
    location: str = Query(min_length=1, description="Free-text location query."),
    geocoding: GeocodingService = Depends(get_geocoding_service),
    provider: WeatherProvider = Depends(get_weather_provider),
) -> ForecastResponse:
    """Live multi-day forecast for a location."""
    resolved = await geocoding.resolve(location)
    result = await provider.get_forecast(
        float(resolved.latitude), float(resolved.longitude)
    )
    return ForecastResponse(
        location=LocationRead.model_validate(resolved),
        days=[ForecastDay(**day) for day in result.get("days", [])],
    )
