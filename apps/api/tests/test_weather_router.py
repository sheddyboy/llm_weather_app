"""Batch 8: integration tests for the live weather lookup router.

The endpoints resolve a location and return cache-first provider data without
persisting a record. OpenWeatherMap is mocked at the transport layer; the shared
provider cache lets the cache-hit behavior be asserted across two requests.
"""

from collections.abc import Callable

import httpx

from tests.owm_mock import WEATHER_PATH, OWMMock


async def test_current_weather_returns_location_and_conditions(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.get("/weather/current", params={"location": "London"})

    assert response.status_code == 200
    body = response.json()
    assert body["location"]["resolved_name"] == "London, England, GB"
    assert body["current"]["conditions"] == "broken clouds"
    assert body["current"]["temp"] == 18.2
    assert body["current"]["humidity"] == 60


async def test_forecast_returns_aggregated_days(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.get("/weather/forecast", params={"location": "London"})

    assert response.status_code == 200
    body = response.json()
    days = body["days"]
    assert [d["date"] for d in days] == ["2026-06-18", "2026-06-19"]
    assert days[0]["temp_min"] == 12.0
    assert days[0]["temp_max"] == 19.0
    assert days[0]["conditions"] == "clear sky"


async def test_current_weather_is_cached_across_requests(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    mock = OWMMock()
    client = api_client(mock)

    await client.get("/weather/current", params={"location": "London"})
    await client.get("/weather/current", params={"location": "London"})

    # Second lookup is served from the provider cache, not a second HTTP call.
    assert mock.calls[WEATHER_PATH] == 1


async def test_missing_location_param_returns_422(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.get("/weather/current")

    assert response.status_code == 422


async def test_unknown_location_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(geocode=[]))

    response = await client.get(
        "/weather/current", params={"location": "Nowheresville"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "location_not_found"
