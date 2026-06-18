"""Persistence for locations, weather records, and their daily readings.

Per ARCHITECTURE §2, repositories are the only layer that touches the SQLAlchemy
session directly; services orchestrate and own the transaction boundary. These
methods therefore `flush` (to assign PKs and make rows visible within the active
session) but never `commit`, leaving the unit-of-work decision to the caller.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DailyReading, Location, WeatherRecord


class WeatherRepository:
    """Data-access layer for the weather domain, bound to one session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_location_by_query(self, query_text: str) -> Location | None:
        """Return the location previously resolved for ``query_text``, if any.

        Lets the geocoding service short-circuit before calling the external
        provider, since the `locations` table is the permanent geocoding cache
        (ARCHITECTURE §7).
        """
        return await self.session.scalar(
            select(Location).where(Location.query_text == query_text)
        )

    async def get_or_create_location(
        self,
        *,
        query_text: str,
        resolved_name: str,
        latitude: Decimal,
        longitude: Decimal,
        country: str | None = None,
    ) -> Location:
        """Return the existing location for ``query_text`` or create it.

        The `locations` table doubles as the permanent geocoding cache
        (ARCHITECTURE §7), so an already-resolved query is reused rather than
        re-inserted.
        """
        existing = await self.get_location_by_query(query_text)
        if existing is not None:
            return existing

        location = Location(
            query_text=query_text,
            resolved_name=resolved_name,
            latitude=latitude,
            longitude=longitude,
            country=country,
        )
        self.session.add(location)
        await self.session.flush()
        return location

    async def create_record(
        self,
        *,
        location_id: UUID,
        start_date: date,
        end_date: date,
    ) -> WeatherRecord:
        """Create a weather record for a location and date range."""
        record = WeatherRecord(
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_record(self, record_id: UUID) -> WeatherRecord | None:
        """Read one record with its location and readings eagerly loaded.

        ``populate_existing`` refreshes an instance already in the session's
        identity map, so a re-fetch after a PATCH (which clears and rebuilds the
        readings via Core statements) reflects the new rows rather than a stale
        collection loaded earlier in the same session.
        """
        stmt = (
            select(WeatherRecord)
            .where(WeatherRecord.id == record_id)
            .options(
                selectinload(WeatherRecord.location),
                selectinload(WeatherRecord.readings),
            )
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def list_records(
        self,
        *,
        location_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[WeatherRecord]:
        """List records newest-first, with optional location/date filters.

        ``start_date``/``end_date`` bound the stored range: only records whose
        range falls at or after ``start_date`` and at or before ``end_date`` are
        returned.
        """
        stmt = (
            select(WeatherRecord)
            .options(
                selectinload(WeatherRecord.location),
                selectinload(WeatherRecord.readings),
            )
            .order_by(WeatherRecord.created_at.desc())
        )
        if location_id is not None:
            stmt = stmt.where(WeatherRecord.location_id == location_id)
        if start_date is not None:
            stmt = stmt.where(WeatherRecord.start_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(WeatherRecord.end_date <= end_date)

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def update_record(
        self,
        record_id: UUID,
        *,
        location_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> WeatherRecord | None:
        """Update a record's location and/or date range.

        Only fields passed explicitly are changed. Returns the refreshed record,
        or ``None`` if no record with ``record_id`` exists.
        """
        record = await self.get_record(record_id)
        if record is None:
            return None

        if location_id is not None:
            record.location_id = location_id
        if start_date is not None:
            record.start_date = start_date
        if end_date is not None:
            record.end_date = end_date

        await self.session.flush()
        return record

    async def delete_record(self, record_id: UUID) -> bool:
        """Delete a record (and, via cascade, its readings).

        Returns ``True`` if a row was deleted, ``False`` if none matched.
        """
        result = await self.session.execute(
            delete(WeatherRecord).where(WeatherRecord.id == record_id)
        )
        return result.rowcount > 0

    async def bulk_insert_readings(
        self,
        record_id: UUID,
        readings: list[dict],
    ) -> list[DailyReading]:
        """Bulk-insert daily readings for a record.

        Each dict carries ``date``, ``temp_min``, ``temp_max``, ``conditions``,
        and optional ``aqi``. The readings for a record are written in one batch
        (ARCHITECTURE §2): a ``POST /records`` resolves the range and stores all
        days at once.
        """
        rows = [
            DailyReading(record_id=record_id, **reading) for reading in readings
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def delete_readings(self, record_id: UUID) -> int:
        """Delete all readings for a record; returns how many were removed.

        Used when a PATCH re-fetches a record's range and the old readings must
        be cleared before the new set is bulk-inserted.
        """
        result = await self.session.execute(
            delete(DailyReading).where(DailyReading.record_id == record_id)
        )
        return result.rowcount
