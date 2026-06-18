"""Batch 10: the cache-first, flag-gated Google Places enrichment service.

External HTTP is mocked at the transport layer (ARCHITECTURE §9). The recorder
counts requests so cache hit/miss is observable, and the ``enabled`` flag is
exercised in both modes to prove the safety toggle works: live mode parses real
Nearby Search responses, stub mode returns canned data without any HTTP call.
"""

import httpx
import pytest

from app.core.cache import InMemoryCache
from app.exceptions import ExternalAPIQuotaExceededError
from app.services.places import PLACES_TTL, PlacesService
from tests.media_mock import PLACES_RESPONSE

LAT = 51.5073
LON = -0.1276


class Recorder:
    """A MockTransport handler that counts requests and can fail on demand."""

    def __init__(self, *, status: int = 200, response: dict | None = None) -> None:
        self.status = status
        self.response = response if response is not None else PLACES_RESPONSE
        self.count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.count += 1
        return httpx.Response(self.status, json=self.response)


def _service(recorder: Recorder, *, enabled: bool = True) -> PlacesService:
    client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    return PlacesService(
        InMemoryCache(), api_key="test-key", enabled=enabled, client=client
    )


async def test_live_mode_parses_places() -> None:
    service = _service(Recorder())

    places = await service.search_nearby(LAT, LON)

    assert len(places) == 2
    first = places[0]
    assert first["name"] == "British Museum"
    assert first["address"] == "Great Russell St, London"
    assert first["rating"] == 4.7
    assert first["types"] == ["museum", "tourist_attraction"]


async def test_cache_hit_skips_second_call() -> None:
    recorder = Recorder()
    service = _service(recorder)

    await service.search_nearby(LAT, LON)
    await service.search_nearby(LAT, LON)

    assert recorder.count == 1


async def test_distinct_coordinates_miss_separately() -> None:
    recorder = Recorder()
    service = _service(recorder)

    await service.search_nearby(LAT, LON)
    await service.search_nearby(40.7128, -74.0060)

    assert recorder.count == 2


async def test_stub_mode_returns_data_without_http() -> None:
    recorder = Recorder()
    service = _service(recorder, enabled=False)

    places = await service.search_nearby(LAT, LON)

    assert recorder.count == 0
    assert len(places) == 1
    assert "stub" in places[0]["name"].lower()


async def test_http_failure_raises_quota_error() -> None:
    service = _service(Recorder(status=403))

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_nearby(LAT, LON)


async def test_failed_call_is_not_cached() -> None:
    recorder = Recorder(status=403)
    service = _service(recorder)

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_nearby(LAT, LON)
    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_nearby(LAT, LON)

    assert recorder.count == 2


def test_ttl_is_multi_day() -> None:
    assert PLACES_TTL >= 24 * 3600
