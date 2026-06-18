"""Batch 12: unit tests for the export service's PDF renderer.

The other formats are covered end to end in ``test_export_router.py``. PDF is the
one binary format, so it is exercised directly here against a hand-built
``WeatherRecordRead`` (including the no-readings path, which the router cannot
produce since created records always carry forecast readings).
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.schemas import (
    DailyReadingRead,
    LocationRead,
    WeatherRecordRead,
)
from app.services.export_service import ExportFormat, render


def _record(*, with_readings: bool) -> WeatherRecordRead:
    now = datetime(2026, 6, 18, tzinfo=UTC)
    readings = []
    if with_readings:
        readings = [
            DailyReadingRead(
                id=uuid.uuid4(),
                date=date(2026, 6, 18),
                temp_min=Decimal("12.0"),
                temp_max=Decimal("19.0"),
                conditions="clear sky",
                aqi=3,
            )
        ]
    return WeatherRecordRead(
        id=uuid.uuid4(),
        location=LocationRead(
            id=uuid.uuid4(),
            query_text="London",
            resolved_name="London, England, GB",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            country="GB",
            created_at=now,
        ),
        start_date=date(2026, 6, 18),
        end_date=date(2026, 6, 19),
        created_at=now,
        updated_at=now,
        readings=readings,
    )


def test_render_pdf_returns_pdf_bytes() -> None:
    content, media_type, extension = render(
        _record(with_readings=True), ExportFormat.PDF
    )

    assert media_type == "application/pdf"
    assert extension == "pdf"
    assert isinstance(content, bytes)
    assert content.startswith(b"%PDF")


def test_render_pdf_with_no_readings_still_renders() -> None:
    content, _media_type, _extension = render(
        _record(with_readings=False), ExportFormat.PDF
    )

    assert isinstance(content, bytes)
    assert content.startswith(b"%PDF")
