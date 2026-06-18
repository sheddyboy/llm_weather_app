"""CRUD for stored weather records (`/records`).

A record bundles a resolved location with a date range and the daily readings
fetched for that range. Creating or repatching a record orchestrates the three
collaborators wired in via dependencies: the geocoding service (free-text query
to a persisted :class:`~app.models.Location`), the cache-first weather provider
(forecast + air pollution), and the repository (persistence). The route handlers
own the unit-of-work boundary only indirectly: the repository flushes, and the
session from :func:`app.core.database.get_db` commits when the request succeeds.

Date-range validity is enforced here so it surfaces as
:class:`InvalidDateRangeError` (the shared error envelope) rather than a generic
422 (ARCHITECTURE §8). The forecast only covers a few days ahead, so a record's
stored readings are whatever forecast days fall inside its range; a range outside
that horizon simply yields a record with no readings.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import (
    get_geocoding_service,
    get_repository,
    get_weather_provider,
)
from app.exceptions import InvalidDateRangeError, RecordNotFoundError
from app.models import Location
from app.repositories import WeatherRepository
from app.schemas import RecordCreate, RecordUpdate, WeatherRecordRead
from app.services import GeocodingService, WeatherProvider

router = APIRouter(prefix="/records", tags=["records"])

# A record's stored range is capped so an accidental multi-year span can't be
# requested; the forecast horizon is only a few days regardless (ARCHITECTURE §8).
MAX_RANGE_DAYS = 30


def _validate_range(start: date, end: date) -> None:
    """Reject an inverted or excessively large date range."""
    if end < start:
        raise InvalidDateRangeError("end_date must not be before start_date.")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise InvalidDateRangeError(
            f"The date range must not exceed {MAX_RANGE_DAYS} days."
        )


async def _build_readings(
    provider: WeatherProvider,
    location: Location,
    start: date,
    end: date,
) -> list[dict]:
    """Fetch the forecast + AQI and assemble the readings inside [start, end].

    Only forecast days that carry both temperatures are kept (the model requires
    them); the single current AQI is attached to each day.
    """
    lat = float(location.latitude)
    lon = float(location.longitude)
    forecast = await provider.get_forecast(lat, lon)
    air = await provider.get_air_pollution(lat, lon)
    aqi = air.get("aqi")

    readings: list[dict] = []
    for day in forecast.get("days", []):
        day_date = date.fromisoformat(day["date"])
        if not (start <= day_date <= end):
            continue
        temp_min = day.get("temp_min")
        temp_max = day.get("temp_max")
        if temp_min is None or temp_max is None:
            continue
        readings.append(
            {
                "date": day_date,
                "temp_min": Decimal(str(temp_min)),
                "temp_max": Decimal(str(temp_max)),
                "conditions": day.get("conditions") or "",
                "aqi": aqi,
            }
        )
    return readings


@router.post("", response_model=WeatherRecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    payload: RecordCreate,
    repository: WeatherRepository = Depends(get_repository),
    geocoding: GeocodingService = Depends(get_geocoding_service),
    provider: WeatherProvider = Depends(get_weather_provider),
) -> WeatherRecordRead:
    """Resolve the location, fetch readings for the range, and store the record."""
    _validate_range(payload.start_date, payload.end_date)
    location = await geocoding.resolve(payload.location)
    readings = await _build_readings(
        provider, location, payload.start_date, payload.end_date
    )
    record = await repository.create_record(
        location_id=location.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    if readings:
        await repository.bulk_insert_readings(record.id, readings)
    stored = await repository.get_record(record.id)
    return WeatherRecordRead.model_validate(stored)


@router.get("", response_model=list[WeatherRecordRead])
async def list_records(
    location_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    repository: WeatherRepository = Depends(get_repository),
) -> list[WeatherRecordRead]:
    """List stored records (newest first), with optional location/date filters."""
    records = await repository.list_records(
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    return [WeatherRecordRead.model_validate(record) for record in records]


@router.get("/{record_id}", response_model=WeatherRecordRead)
async def get_record(
    record_id: UUID,
    repository: WeatherRepository = Depends(get_repository),
) -> WeatherRecordRead:
    """Read one record with its location and readings."""
    record = await repository.get_record(record_id)
    if record is None:
        raise RecordNotFoundError()
    return WeatherRecordRead.model_validate(record)


@router.patch("/{record_id}", response_model=WeatherRecordRead)
async def update_record(
    record_id: UUID,
    payload: RecordUpdate,
    repository: WeatherRepository = Depends(get_repository),
    geocoding: GeocodingService = Depends(get_geocoding_service),
    provider: WeatherProvider = Depends(get_weather_provider),
) -> WeatherRecordRead:
    """Update the location and/or date range, re-fetching affected readings.

    If anything that affects the readings changes (location or either date), the
    old readings are cleared and rebuilt for the new location/range.
    """
    record = await repository.get_record(record_id)
    if record is None:
        raise RecordNotFoundError()

    new_start = payload.start_date or record.start_date
    new_end = payload.end_date or record.end_date
    _validate_range(new_start, new_end)

    location = record.location
    new_location_id = None
    if payload.location is not None:
        location = await geocoding.resolve(payload.location)
        new_location_id = location.id

    await repository.update_record(
        record_id,
        location_id=new_location_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    affects_readings = (
        payload.location is not None
        or payload.start_date is not None
        or payload.end_date is not None
    )
    if affects_readings:
        await repository.delete_readings(record_id)
        readings = await _build_readings(provider, location, new_start, new_end)
        if readings:
            await repository.bulk_insert_readings(record_id, readings)

    stored = await repository.get_record(record_id)
    return WeatherRecordRead.model_validate(stored)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    repository: WeatherRepository = Depends(get_repository),
) -> Response:
    """Delete a record and (via cascade) its readings."""
    deleted = await repository.delete_record(record_id)
    if not deleted:
        raise RecordNotFoundError()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
