"""Batch 3: the three related models insert and read back through real FKs."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DailyReading, Location, WeatherRecord


async def test_insert_and_read_back_related_rows(db_session: AsyncSession) -> None:
    location = Location(
        query_text="Hatfield, UK",
        resolved_name="Hatfield",
        latitude=Decimal("51.763"),
        longitude=Decimal("-0.228"),
        country="GB",
    )
    record = WeatherRecord(
        location=location,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    record.readings = [
        DailyReading(
            date=date(2026, 6, 1),
            temp_min=Decimal("11.5"),
            temp_max=Decimal("19.0"),
            conditions="Clouds",
            aqi=2,
        ),
        DailyReading(
            date=date(2026, 6, 2),
            temp_min=Decimal("12.0"),
            temp_max=Decimal("21.5"),
            conditions="Clear",
            aqi=None,
        ),
    ]

    db_session.add(record)
    await db_session.commit()

    # Client-side uuid default is available without further IO.
    assert location.id is not None
    record_id = record.id

    db_session.expire_all()

    stmt = (
        select(WeatherRecord)
        .where(WeatherRecord.id == record_id)
        .options(
            selectinload(WeatherRecord.location),
            selectinload(WeatherRecord.readings),
        )
    )
    fetched = (await db_session.execute(stmt)).scalar_one()

    # Server defaults are populated after the round-trip.
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
    assert fetched.location.resolved_name == "Hatfield"
    assert fetched.location.country == "GB"
    assert len(fetched.readings) == 2

    by_date = {r.date: r for r in fetched.readings}
    assert by_date[date(2026, 6, 1)].conditions == "Clouds"
    assert by_date[date(2026, 6, 1)].aqi == 2
    assert by_date[date(2026, 6, 2)].aqi is None
    assert by_date[date(2026, 6, 2)].temp_max == Decimal("21.5")


async def test_cascade_delete_removes_children(db_session: AsyncSession) -> None:
    location = Location(
        query_text="Reading, UK",
        resolved_name="Reading",
        latitude=Decimal("51.454"),
        longitude=Decimal("-0.978"),
        country="GB",
    )
    record = WeatherRecord(
        location=location,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1),
        readings=[
            DailyReading(
                date=date(2026, 6, 1),
                temp_min=Decimal("10"),
                temp_max=Decimal("18"),
                conditions="Rain",
            )
        ],
    )
    db_session.add(record)
    await db_session.commit()
    record_id = record.id

    await db_session.delete(record)
    await db_session.commit()

    remaining = await db_session.execute(
        select(DailyReading).where(DailyReading.record_id == record_id)
    )
    assert remaining.scalars().all() == []
