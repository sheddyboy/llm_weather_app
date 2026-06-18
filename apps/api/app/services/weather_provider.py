"""OpenWeatherMap weather provider: current weather, forecast, air pollution.

This service is cache-first against the :class:`CacheBackend` (ARCHITECTURE §7):
each lookup keys on the rounded coordinates and returns the cached value on a hit,
otherwise calls OpenWeatherMap's Free Access APIs, stores the normalized result
under the data type's TTL, and returns it. Raw provider JSON never leaves this
module; callers receive small normalized dicts. Any transport/HTTP failure
surfaces as :class:`WeatherProviderError`.

TTLs follow the architecture's table: current weather ~15 min, forecast and air
pollution ~30 min. The forecast endpoint returns 3-hourly entries; they are
aggregated into one entry per day (min/max temperature, midday conditions) so the
shape matches the `daily_readings` a record stores.
"""

import httpx

from app.core.cache import CacheBackend
from app.core.config import settings
from app.core.logging import logger
from app.exceptions import WeatherProviderError

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

CURRENT_TTL = 900  # 15 min
FORECAST_TTL = 1800  # 30 min
AIR_POLLUTION_TTL = 1800  # 30 min

_TIMEOUT = 10.0
_UNITS = "metric"


class WeatherProvider:
    """Cache-first access to OpenWeatherMap weather, forecast, and air data."""

    def __init__(
        self,
        cache: CacheBackend,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cache = cache
        self._api_key = api_key if api_key is not None else settings.openweather_api_key
        self._client = client

    async def get_current_weather(self, lat: float, lon: float) -> dict:
        """Return normalized current weather for the coordinates (cache-first)."""
        key = f"weather:current:{lat:.4f}:{lon:.4f}"
        return await self._cached(
            key,
            CURRENT_TTL,
            WEATHER_URL,
            {"lat": lat, "lon": lon, "units": _UNITS},
            _parse_current,
        )

    async def get_forecast(self, lat: float, lon: float) -> dict:
        """Return a normalized daily forecast for the coordinates (cache-first)."""
        key = f"weather:forecast:{lat:.4f}:{lon:.4f}"
        return await self._cached(
            key,
            FORECAST_TTL,
            FORECAST_URL,
            {"lat": lat, "lon": lon, "units": _UNITS},
            _parse_forecast,
        )

    async def get_air_pollution(self, lat: float, lon: float) -> dict:
        """Return the normalized air-quality index for the coordinates."""
        key = f"weather:air:{lat:.4f}:{lon:.4f}"
        return await self._cached(
            key,
            AIR_POLLUTION_TTL,
            AIR_POLLUTION_URL,
            {"lat": lat, "lon": lon},
            _parse_air_pollution,
        )

    async def _cached(self, key, ttl, url, params, parse):
        """Return the cached value for ``key`` or fetch, normalize, and store it."""
        cached = await self._cache.get(key)
        if cached is not None:
            logger.debug("Weather cache hit for {}", key)
            return cached
        logger.debug("Weather cache miss for {}", key)
        result = parse(await self._get(url, params))
        await self._cache.set(key, result, ttl=ttl)
        return result

    async def _get(self, url: str, params: dict) -> dict:
        params = {**params, "appid": self._api_key}
        try:
            if self._client is not None:
                response = await self._client.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Weather request to {} failed: {}", url, exc)
            raise WeatherProviderError(
                "The weather provider is currently unavailable."
            ) from exc


def _parse_current(data: dict) -> dict:
    """Normalize an OpenWeatherMap current-weather response."""
    main = data.get("main", {})
    weather = data.get("weather") or [{}]
    wind = data.get("wind", {})
    return {
        "conditions": weather[0].get("description", ""),
        "temp": main.get("temp"),
        "temp_min": main.get("temp_min"),
        "temp_max": main.get("temp_max"),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
    }


def _parse_forecast(data: dict) -> dict:
    """Aggregate the 3-hourly forecast list into one entry per day.

    For each calendar day, ``temp_min``/``temp_max`` span all of that day's
    entries, and ``conditions`` is taken from the entry closest to midday (a
    reasonable single descriptor for the day).
    """
    buckets: dict[str, dict] = {}
    for entry in data.get("list", []):
        dt_txt = entry.get("dt_txt", "")
        day, _, clock = dt_txt.partition(" ")
        if not day:
            continue
        main = entry.get("main", {})
        temp_min = main.get("temp_min")
        temp_max = main.get("temp_max")
        weather = entry.get("weather") or [{}]
        conditions = weather[0].get("description", "")
        hour = int(clock[:2]) if clock[:2].isdigit() else 0
        hour_diff = abs(hour - 12)

        bucket = buckets.get(day)
        if bucket is None:
            buckets[day] = {
                "date": day,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "conditions": conditions,
                "_hour_diff": hour_diff,
            }
            continue
        if temp_min is not None and (
            bucket["temp_min"] is None or temp_min < bucket["temp_min"]
        ):
            bucket["temp_min"] = temp_min
        if temp_max is not None and (
            bucket["temp_max"] is None or temp_max > bucket["temp_max"]
        ):
            bucket["temp_max"] = temp_max
        if hour_diff < bucket["_hour_diff"]:
            bucket["conditions"] = conditions
            bucket["_hour_diff"] = hour_diff

    days = [
        {k: v for k, v in bucket.items() if k != "_hour_diff"}
        for bucket in sorted(buckets.values(), key=lambda b: b["date"])
    ]
    return {"days": days}


def _parse_air_pollution(data: dict) -> dict:
    """Normalize an OpenWeatherMap air-pollution response to its AQI (1-5)."""
    entries = data.get("list") or [{}]
    return {"aqi": entries[0].get("main", {}).get("aqi")}


__all__ = [
    "WeatherProvider",
    "WEATHER_URL",
    "FORECAST_URL",
    "AIR_POLLUTION_URL",
    "CURRENT_TTL",
    "FORECAST_TTL",
    "AIR_POLLUTION_TTL",
]
