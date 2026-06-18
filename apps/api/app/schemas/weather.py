"""Response schemas for the live weather endpoints (`/weather/*`).

These are the stable contract for the not-persisted lookups: the resolved
location plus the normalized weather payload produced by
:class:`app.services.weather_provider.WeatherProvider`. The field shapes mirror
that service's normalized dicts, so a handler can construct them directly from a
provider response.
"""

from datetime import date

from pydantic import BaseModel

from app.schemas.records import LocationRead


class CurrentWeather(BaseModel):
    """Normalized current weather for a location."""

    conditions: str
    temp: float | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    humidity: int | None = None
    wind_speed: float | None = None


class CurrentWeatherResponse(BaseModel):
    """Live current weather paired with its resolved location."""

    location: LocationRead
    current: CurrentWeather


class ForecastDay(BaseModel):
    """One aggregated forecast day (min/max temperature, midday conditions)."""

    date: date
    temp_min: float | None = None
    temp_max: float | None = None
    conditions: str


class ForecastResponse(BaseModel):
    """Live multi-day forecast paired with its resolved location."""

    location: LocationRead
    days: list[ForecastDay]
