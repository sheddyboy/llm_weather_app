"""Batch 11: end-to-end tests for the briefing endpoint.

A record is created through the real app (OpenWeatherMap mocked at the transport
layer), then `/records/{id}/briefing` is exercised with the OpenAI call replaced
by a fake structured runnable. The behaviors proven here are the structured
response shape, that a second request for the unchanged record is served from
cache without re-invoking the model, and the missing-record 404.
"""

from collections.abc import Callable

import httpx

from tests.briefing_mock import FakeBriefingLLM
from tests.owm_mock import OWMMock

START = "2026-06-18"
END = "2026-06-19"


async def _create_record(client: httpx.AsyncClient) -> dict:
    payload = {"location": "London", "start_date": START, "end_date": END}
    response = await client.post("/records", json=payload)
    assert response.status_code == 201
    return response.json()


async def test_briefing_returns_structured_response(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    llm = FakeBriefingLLM()
    client = api_client(OWMMock(), briefing_llm=llm)
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/briefing")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "summary": llm.response.summary,
        "clothing_suggestion": llm.response.clothing_suggestion,
        "aqi_note": llm.response.aqi_note,
    }
    assert len(llm.calls) == 1


async def test_briefing_is_cached_across_requests(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    llm = FakeBriefingLLM()
    client = api_client(OWMMock(), briefing_llm=llm)
    created = await _create_record(client)

    first = await client.get(f"/records/{created['id']}/briefing")
    second = await client.get(f"/records/{created['id']}/briefing")

    assert first.status_code == 200
    assert second.json() == first.json()
    assert len(llm.calls) == 1  # second request served from cache


async def test_briefing_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(), briefing_llm=FakeBriefingLLM())

    response = await client.get(
        "/records/00000000-0000-0000-0000-000000000000/briefing"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"
