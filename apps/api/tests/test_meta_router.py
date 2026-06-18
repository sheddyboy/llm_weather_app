"""Batch 12: tests for the application metadata endpoint (`GET /meta`).

The endpoint returns the configured name and description (consumed by the
frontend footer) with no database or external call, so it drives the app directly.
"""

from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


async def test_meta_returns_name_and_description() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/meta")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "name": settings.meta_name,
        "description": settings.meta_description,
    }
    # The PM Accelerator attribution must be present for the footer.
    assert "PM Accelerator" in body["description"]
