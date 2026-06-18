"""Batch 9: end-to-end tests for the record export endpoint.

A record is created through the real app (OpenWeatherMap mocked at the transport
layer, ARCHITECTURE §9), then exported in each format and the rendered output is
validated for correctness: JSON parses back to the record, CSV has a header plus
one row per reading, XML parses into the expected tree, and markdown carries the
title and a table row per reading.
"""

import csv
import io
import json
from collections.abc import Callable
from xml.etree import ElementTree as ET

import httpx

from tests.owm_mock import OWMMock

START = "2026-06-18"
END = "2026-06-19"


async def _create_record(client: httpx.AsyncClient) -> dict:
    payload = {"location": "London", "start_date": START, "end_date": END}
    response = await client.post("/records", json=payload)
    assert response.status_code == 201
    return response.json()


async def test_export_json_round_trips(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "record-" in response.headers["content-disposition"]
    body = json.loads(response.text)
    assert body["id"] == created["id"]
    assert body["location"]["resolved_name"] == "London, England, GB"
    assert len(body["readings"]) == 2


async def test_export_defaults_to_json(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert json.loads(response.text)["id"] == created["id"]


async def test_export_csv_has_header_and_one_row_per_reading(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].endswith('.csv"')
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 2
    dates = sorted(row["date"] for row in rows)
    assert dates == [START, END]
    first = next(row for row in rows if row["date"] == START)
    assert first["record_id"] == created["id"]
    assert first["location"] == "London, England, GB"
    assert float(first["temp_min"]) == 12.0
    assert float(first["temp_max"]) == 19.0
    assert first["conditions"] == "clear sky"
    assert first["aqi"] == "3"


async def test_export_xml_parses_into_expected_tree(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ET.fromstring(response.text)
    assert root.tag == "record"
    assert root.attrib["id"] == created["id"]
    assert root.findtext("start_date") == START
    assert root.findtext("location/resolved_name") == "London, England, GB"
    readings = root.findall("readings/reading")
    assert len(readings) == 2
    assert {r.findtext("date") for r in readings} == {START, END}


async def test_export_markdown_has_title_and_table(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=markdown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"].endswith('.md"')
    text = response.text
    assert text.startswith("# Weather Record: London, England, GB")
    assert "| Date | Min (°C) | Max (°C) | Conditions | AQI |" in text
    # One table row per reading.
    assert text.count(f"| {START} |") == 1
    assert text.count(f"| {END} |") == 1


async def test_export_pdf_returns_pdf_document(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].endswith('.pdf"')
    # A valid PDF starts with the %PDF magic bytes and is non-trivially sized.
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500


async def test_export_unknown_format_returns_422(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())
    created = await _create_record(client)

    response = await client.get(f"/records/{created['id']}/export?format=yaml")

    assert response.status_code == 422


async def test_export_missing_record_returns_404(
    api_client: Callable[..., httpx.AsyncClient],
) -> None:
    client = api_client(OWMMock())

    response = await client.get(
        "/records/00000000-0000-0000-0000-000000000000/export?format=json"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"
