"""A configurable OpenWeatherMap mock transport shared by the router tests.

External HTTP is mocked at the transport layer (ARCHITECTURE §9): one handler
dispatches by URL path across the geocoding, current-weather, forecast, and
air-pollution endpoints, returns canned payloads, and counts calls per path so
cache hit/miss behavior can be asserted end to end.
"""

from collections import Counter

import httpx

LONDON_MATCH = {
    "name": "London",
    "lat": 51.5073219,
    "lon": -0.1276474,
    "country": "GB",
    "state": "England",
}

CURRENT_RESPONSE = {
    "main": {"temp": 18.2, "temp_min": 15.0, "temp_max": 20.1, "humidity": 60},
    "weather": [{"description": "broken clouds"}],
    "wind": {"speed": 3.5},
}

# Two calendar days; day one spans three slots so aggregation is exercised.
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

GEOCODE_PATH = "/geo/1.0/direct"
WEATHER_PATH = "/data/2.5/weather"
FORECAST_PATH = "/data/2.5/forecast"
AIR_PATH = "/data/2.5/air_pollution"


class OWMMock:
    """MockTransport handler covering every OpenWeatherMap endpoint used."""

    def __init__(
        self,
        *,
        geocode: list | None = None,
        current: dict | None = None,
        forecast: dict | None = None,
        air: dict | None = None,
        geocode_status: int = 200,
        weather_status: int = 200,
    ) -> None:
        self.geocode = geocode if geocode is not None else [LONDON_MATCH]
        self.current = current if current is not None else CURRENT_RESPONSE
        self.forecast = forecast if forecast is not None else FORECAST_RESPONSE
        self.air = air if air is not None else AIR_RESPONSE
        self.geocode_status = geocode_status
        self.weather_status = weather_status
        self.calls: Counter[str] = Counter()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls[path] += 1
        if path == GEOCODE_PATH:
            return httpx.Response(self.geocode_status, json=self.geocode)
        if path.endswith(WEATHER_PATH):
            return httpx.Response(self.weather_status, json=self.current)
        if path.endswith(FORECAST_PATH):
            return httpx.Response(self.weather_status, json=self.forecast)
        if path.endswith(AIR_PATH):
            return httpx.Response(self.weather_status, json=self.air)
        return httpx.Response(404, json={})
