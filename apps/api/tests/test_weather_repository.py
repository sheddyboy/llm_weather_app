"""Batch 4: the repository layer exercised against the real test schema."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyReading, WeatherRecord
from app.repositories import WeatherRepository


def _location_kwargs(**overrides) -> dict:
    base = dict(
        query_text="Hatfield, UK",
        resolved_name="Hatfield",
        latitude=Decimal("51.763"),
        longitude=Decimal("-0.228"),
        country="GB",
    )
    base.update(overrides)
    return base


def _readings() -> list[dict]:
    return [
        dict(
            date=date(2026, 6, 1),
            temp_min=Decimal("11.5"),
            temp_max=Decimal("19.0"),
            conditions="Clouds",
            aqi=2,
        ),
        dict(
            date=date(2026, 6, 2),
            temp_min=Decimal("12.0"),
            temp_max=Decimal("21.5"),
            conditions="Clear",
            aqi=None,
        ),
    ]


@pytest.fixture
def repo(db_session: AsyncSession) -> WeatherRepository:
    return WeatherRepository(db_session)


async def test_get_or_create_location_creates_then_reuses(
    repo: WeatherRepository,
) -> None:
    created = await repo.get_or_create_location(**_location_kwargs())
    assert created.id is not None

    again = await repo.get_or_create_location(
        **_location_kwargs(resolved_name="ignored on reuse")
    )
    # Same query_text resolves to the existing row, not a second insert.
    assert again.id == created.id
    assert again.resolved_name == "Hatfield"


async def test_create_and_get_record_with_readings(
    repo: WeatherRepository, db_session: AsyncSession
) -> None:
    location = await repo.get_or_create_location(**_location_kwargs())
    record = await repo.create_record(
        location_id=location.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    inserted = await repo.bulk_insert_readings(record.id, _readings())
    assert len(inserted) == 2

    fetched = await repo.get_record(record.id)
    assert fetched is not None
    assert fetched.location.resolved_name == "Hatfield"
    assert len(fetched.readings) == 2
    by_date = {r.date: r for r in fetched.readings}
    assert by_date[date(2026, 6, 1)].aqi == 2
    assert by_date[date(2026, 6, 2)].aqi is None


async def test_get_record_missing_returns_none(repo: WeatherRepository) -> None:
    import uuid

    assert await repo.get_record(uuid.uuid4()) is None


async def test_list_records_filters_and_ordering(repo: WeatherRepository) -> None:
    hatfield = await repo.get_or_create_location(**_location_kwargs())
    reading_loc = await repo.get_or_create_location(
        **_location_kwargs(query_text="Reading, UK", resolved_name="Reading")
    )

    older = await repo.create_record(
        location_id=hatfield.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    newer = await repo.create_record(
        location_id=hatfield.id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
    )
    other = await repo.create_record(
        location_id=reading_loc.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )

    all_records = await repo.list_records()
    ids = [r.id for r in all_records]
    assert {older.id, newer.id, other.id} <= set(ids)

    by_location = await repo.list_records(location_id=hatfield.id)
    assert {r.id for r in by_location} == {older.id, newer.id}
    # Ordering is created_at-desc in production; within a single test
    # transaction now() is constant, so the relative order can't be asserted
    # here. The query shape (newest-first) is covered by the order_by clause.

    by_range = await repo.list_records(
        location_id=hatfield.id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    assert [r.id for r in by_range] == [newer.id]


async def test_update_record_changes_only_given_fields(
    repo: WeatherRepository,
) -> None:
    location = await repo.get_or_create_location(**_location_kwargs())
    record = await repo.create_record(
        location_id=location.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )

    updated = await repo.update_record(record.id, end_date=date(2026, 6, 10))
    assert updated is not None
    assert updated.start_date == date(2026, 6, 1)
    assert updated.end_date == date(2026, 6, 10)


async def test_update_record_missing_returns_none(
    repo: WeatherRepository,
) -> None:
    import uuid

    assert await repo.update_record(uuid.uuid4(), end_date=date(2026, 6, 10)) is None


async def test_delete_record_cascades_to_readings(
    repo: WeatherRepository, db_session: AsyncSession
) -> None:
    location = await repo.get_or_create_location(**_location_kwargs())
    record = await repo.create_record(
        location_id=location.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    await repo.bulk_insert_readings(record.id, _readings())

    deleted = await repo.delete_record(record.id)
    assert deleted is True

    assert await repo.get_record(record.id) is None
    remaining = await db_session.scalars(
        select(DailyReading).where(DailyReading.record_id == record.id)
    )
    assert remaining.all() == []


async def test_delete_record_missing_returns_false(
    repo: WeatherRepository,
) -> None:
    import uuid

    assert await repo.delete_record(uuid.uuid4()) is False


async def test_delete_readings_clears_set(
    repo: WeatherRepository, db_session: AsyncSession
) -> None:
    location = await repo.get_or_create_location(**_location_kwargs())
    record = await repo.create_record(
        location_id=location.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    await repo.bulk_insert_readings(record.id, _readings())

    removed = await repo.delete_readings(record.id)
    assert removed == 2

    count = await db_session.scalar(
        select(WeatherRecord).where(WeatherRecord.id == record.id)
    )
    # The record itself survives; only its readings were cleared.
    assert count is not None
    remaining = await db_session.scalars(
        select(DailyReading).where(DailyReading.record_id == record.id)
    )
    assert remaining.all() == []
