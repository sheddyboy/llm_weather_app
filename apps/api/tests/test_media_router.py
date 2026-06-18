"""Batch 10: end-to-end tests for the media-enrichment endpoint.

A record is created through the real app (OpenWeatherMap mocked at the transport
layer), then `/records/{id}/media` is exercised with the YouTube and Places
providers mocked too. The key behaviors proven here are the combined response,
graceful degradation when one provider is over quota (the other still returns),
the flag-gated stub fallback, and the missing-record 404.
"""

from collections.abc import Callable

import httpx

from tests.media_mock import PlacesMock, YouTubeMock
from tests.owm_mock import OWMMock

START = "2026-06-18"
END = "2026-06-19"


async def _create_record(client: httpx.AsyncClient) -> dict:
    payload = {"location": "London", "start_date": START, "end_date": END}
    response = await client.post("/records", json=payload)
    assert response.status_code == 201
    return response.json()


async def test_media_combines_videos_and_places(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(), youtube=YouTubeMock(), places=PlacesMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/media")

    assert response.status_code == 200
    body = response.json()
    assert body["location"]["resolved_name"] == "London, England, GB"
    assert [v["video_id"] for v in body["videos"]] == ["abc123", "def456"]
    assert [p["name"] for p in body["points_of_interest"]] == [
        "British Museum",
        "Hyde Park",
    ]


async def test_media_degrades_when_youtube_over_quota(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(
        OWMMock(), youtube=YouTubeMock(status=403), places=PlacesMock()
    )
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/media")

    assert response.status_code == 200
    body = response.json()
    assert body["videos"] == []
    assert len(body["points_of_interest"]) == 2


async def test_media_degrades_when_places_unavailable(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(
        OWMMock(), youtube=YouTubeMock(), places=PlacesMock(status=500)
    )
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/media")

    assert response.status_code == 200
    body = response.json()
    assert len(body["videos"]) == 2
    assert body["points_of_interest"] == []


async def test_media_stub_mode_when_providers_disabled(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(), enable_youtube=False, enable_places=False)
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/media")

    assert response.status_code == 200
    body = response.json()
    assert body["videos"][0]["video_id"] == "stub-youtube"
    assert "stub" in body["points_of_interest"][0]["name"].lower()


async def test_media_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(), youtube=YouTubeMock(), places=PlacesMock())

    response = await client.get(
        "/records/00000000-0000-0000-0000-000000000000/media"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"
