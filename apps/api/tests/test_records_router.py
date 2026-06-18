"""Batch 8: end-to-end integration tests for the records CRUD router.

The real FastAPI app is driven through an ASGI client against the rolled-back
test database, with OpenWeatherMap mocked at the transport layer (ARCHITECTURE
§9). The forecast fixture covers 2026-06-18 and 2026-06-19, so a record over that
range stores two daily readings.
"""

from collections.abc import Callable

import httpx

from tests.owm_mock import GEOCODE_PATH, OWMMock

START = "2026-06-18"
END = "2026-06-19"


async def _create(client: httpx.AsyncClient, **overrides) -> httpx.Response:
    payload = {"location": "London", "start_date": START, "end_date": END}
    payload.update(overrides)
    return await client.post("/records", json=payload)


async def test_create_record_persists_with_readings(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    mock = OWMMock()
    client = api_client(mock)

    response = await _create(client)

    assert response.status_code == 201
    body = response.json()
    assert body["location"]["resolved_name"] == "London, England, GB"
    assert body["start_date"] == START
    assert body["end_date"] == END

    readings = sorted(body["readings"], key=lambda r: r["date"])
    assert [r["date"] for r in readings] == [START, END]
    assert float(readings[0]["temp_min"]) == 12.0
    assert float(readings[0]["temp_max"]) == 19.0
    assert readings[0]["conditions"] == "clear sky"
    assert all(r["aqi"] == 3 for r in readings)


async def test_create_then_get_returns_same_record(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = (await _create(client)).json()

    response = await client.get(f"/records/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert len(response.json()["readings"]) == 2


async def test_list_records_includes_created_and_filters_by_location(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = (await _create(client)).json()
    location_id = created["location"]["id"]

    listed = await client.get("/records")
    assert listed.status_code == 200
    assert [r["id"] for r in listed.json()] == [created["id"]]

    filtered = await client.get("/records", params={"location_id": location_id})
    assert [r["id"] for r in filtered.json()] == [created["id"]]


async def test_create_invalid_date_range_returns_400(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    mock = OWMMock()
    client = api_client(mock)

    response = await _create(client, start_date=END, end_date=START)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_date_range"
    # Validation happens before any external call.
    assert mock.calls[GEOCODE_PATH] == 0


async def test_create_unknown_location_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(geocode=[]))

    response = await _create(client, location="Nowheresville")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "location_not_found"


async def test_create_provider_failure_returns_502(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock(weather_status=502))

    response = await _create(client)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "weather_provider_error"


async def test_get_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.get("/records/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"


async def test_patch_narrowing_range_refetches_readings(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = (await _create(client)).json()
    assert len(created["readings"]) == 2

    response = await client.patch(
        f"/records/{created['id']}", json={"end_date": START}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["end_date"] == START
    # Re-fetched: only the day inside the narrowed range survives.
    assert [r["date"] for r in body["readings"]] == [START]


async def test_patch_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.patch(
        "/records/00000000-0000-0000-0000-000000000000", json={"end_date": START}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"


async def test_patch_invalid_resulting_range_returns_400(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = (await _create(client)).json()

    # New start after the existing end inverts the range.
    response = await client.patch(
        f"/records/{created['id']}", json={"start_date": "2026-06-20"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_date_range"


async def test_delete_record_removes_it(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = (await _create(client)).json()

    deleted = await client.delete(f"/records/{created['id']}")
    assert deleted.status_code == 204

    follow_up = await client.get(f"/records/{created['id']}")
    assert follow_up.status_code == 404


async def test_delete_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.delete("/records/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"
