"""Batch 7: geocoding, resolving queries to persisted ``locations`` rows.

The OpenWeatherMap direct-geocoding HTTP layer is mocked (ARCHITECTURE §9); the
repository runs against the real test schema, so the "permanent geocoding cache"
behavior (a resolved query is reused without a second external call) is verified
end to end.
"""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import LocationNotFoundError, WeatherProviderError
from app.repositories import WeatherRepository
from app.services.geocoding import GeocodingService

LONDON_MATCH = {
    "name": "London",
    "lat": 51.5073219,
    "lon": -0.1276474,
    "country": "GB",
    "state": "England",
}


class Recorder:
    """MockTransport handler returning a canned geocoding result, counting calls."""

    def __init__(self, body: list | None = None, *, status: int = 200) -> None:
        self.body = body if body is not None else [LONDON_MATCH]
        self.status = status
        self.calls = 0
        self.last_params: dict[str, str] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.last_params = dict(request.url.params)
        return httpx.Response(self.status, json=self.body)


def make_service(repo: WeatherRepository, recorder: Recorder):
    client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    return GeocodingService(repo, api_key="test-key", client=client), client


async def test_resolve_persists_a_new_location(db_session: AsyncSession) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder()
    service, client = make_service(repo, recorder)
    async with client:
        location = await service.resolve("London")

    assert location.id is not None
    assert location.query_text == "London"
    assert location.resolved_name == "London, England, GB"
    assert location.country == "GB"
    assert float(location.latitude) == pytest.approx(51.5073219)
    assert float(location.longitude) == pytest.approx(-0.1276474)
    assert recorder.last_params["q"] == "London"
    assert recorder.last_params["appid"] == "test-key"

    stored = await repo.get_location_by_query("London")
    assert stored is not None and stored.id == location.id


async def test_resolve_reuses_existing_without_calling_provider(
    db_session: AsyncSession,
) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder()
    service, client = make_service(repo, recorder)
    async with client:
        first = await service.resolve("London")
        second = await service.resolve("London")

    assert first.id == second.id
    assert recorder.calls == 1  # second resolve served from the locations table


async def test_query_is_stripped_before_lookup(db_session: AsyncSession) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder()
    service, client = make_service(repo, recorder)
    async with client:
        first = await service.resolve("London")
        second = await service.resolve("  London  ")

    assert first.id == second.id
    assert recorder.calls == 1


async def test_no_match_raises_location_not_found(db_session: AsyncSession) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder(body=[])
    service, client = make_service(repo, recorder)
    async with client:
        with pytest.raises(LocationNotFoundError):
            await service.resolve("Nowheresville")


async def test_http_failure_raises_weather_provider_error(
    db_session: AsyncSession,
) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder(status=502)
    service, client = make_service(repo, recorder)
    async with client:
        with pytest.raises(WeatherProviderError):
            await service.resolve("London")


async def test_resolved_name_omits_missing_parts(db_session: AsyncSession) -> None:
    repo = WeatherRepository(db_session)
    recorder = Recorder(body=[{"name": "Atlantis", "lat": 0.0, "lon": 0.0}])
    service, client = make_service(repo, recorder)
    async with client:
        location = await service.resolve("Atlantis")
    assert location.resolved_name == "Atlantis"
    assert location.country is None
