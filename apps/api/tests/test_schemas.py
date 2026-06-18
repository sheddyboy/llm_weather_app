"""The request/response schemas validate input and serialize ORM instances."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import DailyReading, Location, WeatherRecord
from app.schemas import (
    RecordCreate,
    RecordUpdate,
    WeatherRecordRead,
)


def test_record_create_parses_dates() -> None:
    payload = RecordCreate(
        location="Hatfield, UK",
        start_date="2026-06-01",
        end_date="2026-06-05",
    )
    assert payload.location == "Hatfield, UK"
    assert payload.start_date == date(2026, 6, 1)
    assert payload.end_date == date(2026, 6, 5)


def test_record_create_rejects_blank_location() -> None:
    with pytest.raises(ValidationError):
        RecordCreate(location="", start_date="2026-06-01", end_date="2026-06-05")


def test_record_update_defaults_to_none() -> None:
    patch = RecordUpdate()
    assert patch.location is None
    assert patch.start_date is None
    assert patch.end_date is None


def test_weather_record_read_from_orm() -> None:
    now = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)
    location = Location(
        id=uuid.uuid4(),
        query_text="Hatfield, UK",
        resolved_name="Hatfield",
        latitude=Decimal("51.76"),
        longitude=Decimal("-0.23"),
        country="GB",
        created_at=now,
    )
    record = WeatherRecord(
        id=uuid.uuid4(),
        location_id=location.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        created_at=now,
        updated_at=now,
    )
    record.location = location
    record.readings = [
        DailyReading(
            id=uuid.uuid4(),
            record_id=record.id,
            date=date(2026, 6, 1),
            temp_min=Decimal("10.5"),
            temp_max=Decimal("18.2"),
            conditions="Clear",
            aqi=2,
        )
    ]

    schema = WeatherRecordRead.model_validate(record)

    assert schema.location.resolved_name == "Hatfield"
    assert schema.location.country == "GB"
    assert len(schema.readings) == 1
    assert schema.readings[0].conditions == "Clear"
    assert schema.readings[0].aqi == 2
    assert schema.start_date == date(2026, 6, 1)
