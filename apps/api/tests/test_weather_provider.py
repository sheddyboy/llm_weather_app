"""Batch 7: the cache-first OpenWeatherMap weather provider.

External HTTP is mocked at the transport layer (ARCHITECTURE §9), so no real
quota is spent and runs stay deterministic. The recorder counts requests per
endpoint, which is how cache hit/miss behavior is asserted.
"""

import httpx
import pytest

from app.core.cache import InMemoryCache
from app.exceptions import WeatherProviderError
from app.services.weather_provider import (
    AIR_POLLUTION_TTL,
    CURRENT_TTL,
    FORECAST_TTL,
    WeatherProvider,
)

CURRENT_RESPONSE = {
    "main": {"temp": 18.2, "temp_min": 15.0, "temp_max": 20.1, "humidity": 60},
    "weather": [{"description": "broken clouds"}],
    "wind": {"speed": 3.5},
}

# Two calendar days of 3-hourly entries; day one spans three slots so the
# min/max aggregation and midday-conditions pick are both exercised.
FORECAST_RESPONSE = {
    "list": [
        {
            "dt_txt": "2026-06-18 09:00:00",
            "main": {"temp_min": 12.0, "temp_max": 16.0},
            "weather": [{"description": "light rain"}],
        },
        {
            "dt_txt": "2026-06-18 12:00:00",
            "main": {"temp_min": 14.0, "temp_max": 19.0},
            "weather": [{"description": "clear sky"}],
        },
        {
            "dt_txt": "2026-06-18 18:00:00",
            "main": {"temp_min": 13.0, "temp_max": 17.0},
            "weather": [{"description": "few clouds"}],
        },
        {
            "dt_txt": "2026-06-19 12:00:00",
            "main": {"temp_min": 11.0, "temp_max": 21.0},
            "weather": [{"description": "scattered clouds"}],
        },
    ]
}

AIR_RESPONSE = {"list": [{"main": {"aqi": 3}}]}


class Recorder:
    """A MockTransport handler that counts requests per endpoint path."""

    def __init__(self, *, status: int = 200) -> None:
        self.status = status
        self.calls: dict[str, int] = {}
        self.last_params: dict[str, str] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls[path] = self.calls.get(path, 0) + 1
        self.last_params = dict(request.url.params)
        if self.status != 200:
            return httpx.Response(self.status, json={"message": "boom"})
        if path.endswith("/weather"):
            body = CURRENT_RESPONSE
        elif path.endswith("/forecast"):
            body = FORECAST_RESPONSE
        elif path.endswith("/air_pollution"):
            body = AIR_RESPONSE
        else:  # pragma: no cover - defensive
            return httpx.Response(404, json={})
        return httpx.Response(200, json=body)


def make_provider(recorder: Recorder, cache: InMemoryCache | None = None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    provider = WeatherProvider(
        cache or InMemoryCache(), api_key="test-key", client=client
    )
    return provider, client


async def test_current_weather_is_normalized() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        result = await provider.get_current_weather(51.5, -0.12)
    assert result == {
        "conditions": "broken clouds",
        "temp": 18.2,
        "temp_min": 15.0,
        "temp_max": 20.1,
        "humidity": 60,
        "wind_speed": 3.5,
    }
    assert recorder.last_params["appid"] == "test-key"
    assert recorder.last_params["units"] == "metric"


async def test_current_weather_cache_hit_skips_second_call() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        first = await provider.get_current_weather(51.5, -0.12)
        second = await provider.get_current_weather(51.5, -0.12)
    assert first == second
    assert recorder.calls["/data/2.5/weather"] == 1  # second served from cache


async def test_distinct_coordinates_miss_separately() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        await provider.get_current_weather(51.5, -0.12)
        await provider.get_current_weather(40.7, -74.0)
    assert recorder.calls["/data/2.5/weather"] == 2


async def test_forecast_aggregates_to_one_entry_per_day() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        result = await provider.get_forecast(51.5, -0.12)
    assert result == {
        "days": [
            {
                "date": "2026-06-18",
                "temp_min": 12.0,
                "temp_max": 19.0,
                "conditions": "clear sky",  # midday slot
            },
            {
                "date": "2026-06-19",
                "temp_min": 11.0,
                "temp_max": 21.0,
                "conditions": "scattered clouds",
            },
        ]
    }


async def test_forecast_is_cached() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        await provider.get_forecast(51.5, -0.12)
        await provider.get_forecast(51.5, -0.12)
    assert recorder.calls["/data/2.5/forecast"] == 1


async def test_air_pollution_returns_aqi() -> None:
    recorder = Recorder()
    provider, client = make_provider(recorder)
    async with client:
        result = await provider.get_air_pollution(51.5, -0.12)
        await provider.get_air_pollution(51.5, -0.12)
    assert result == {"aqi": 3}
    assert recorder.calls["/data/2.5/air_pollution"] == 1
    assert "units" not in recorder.last_params  # air pollution has no units param


async def test_provider_error_on_http_failure() -> None:
    recorder = Recorder(status=500)
    provider, client = make_provider(recorder)
    async with client:
        with pytest.raises(WeatherProviderError):
            await provider.get_current_weather(51.5, -0.12)


async def test_failed_call_is_not_cached() -> None:
    recorder = Recorder(status=500)
    provider, client = make_provider(recorder)
    async with client:
        with pytest.raises(WeatherProviderError):
            await provider.get_current_weather(51.5, -0.12)
        with pytest.raises(WeatherProviderError):
            await provider.get_current_weather(51.5, -0.12)
    assert recorder.calls["/data/2.5/weather"] == 2


async def test_cache_entries_use_the_configured_ttls() -> None:
    # Guard against the TTL constants drifting out of the architecture's ranges.
    assert CURRENT_TTL == 900
    assert FORECAST_TTL == 1800
    assert AIR_POLLUTION_TTL == 1800
