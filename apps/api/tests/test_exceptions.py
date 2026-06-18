"""Each custom exception maps to the right status code and JSON error shape.

A throwaway app mounts a route per exception so the handler can be exercised
end-to-end (ARCHITECTURE §8 definition of done), and we assert the real app has
the handler registered.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.exceptions import (
    AppError,
    ExternalAPIQuotaExceededError,
    InvalidDateRangeError,
    LocationNotFoundError,
    WeatherProviderError,
    register_exception_handlers,
)
from app.main import app as main_app


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/location")
    async def _location() -> None:
        raise LocationNotFoundError("No match for 'Narnia'.")

    @app.get("/raise/date")
    async def _date() -> None:
        raise InvalidDateRangeError()

    @app.get("/raise/provider")
    async def _provider() -> None:
        raise WeatherProviderError()

    @app.get("/raise/quota")
    async def _quota() -> None:
        raise ExternalAPIQuotaExceededError()

    return app


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_code"),
    [
        ("/raise/location", 404, "location_not_found"),
        ("/raise/date", 400, "invalid_date_range"),
        ("/raise/provider", 502, "weather_provider_error"),
        ("/raise/quota", 503, "external_api_quota_exceeded"),
    ],
)
@pytest.mark.asyncio
async def test_exception_returns_status_and_shape(
    path: str, expected_status: int, expected_code: str
) -> None:
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)

    assert response.status_code == expected_status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == expected_code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]


@pytest.mark.asyncio
async def test_custom_message_is_used() -> None:
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/raise/location")

    assert response.json()["error"]["message"] == "No match for 'Narnia'."


def test_default_message_used_when_none_given() -> None:
    assert InvalidDateRangeError().message == InvalidDateRangeError.default_message
    assert WeatherProviderError("boom").message == "boom"


def test_handler_registered_on_main_app() -> None:
    assert AppError in main_app.exception_handlers
