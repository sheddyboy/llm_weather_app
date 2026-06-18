"""Request/response schemas for the records and weather domain.

These mirror the persisted models (``app.models``) but are the API's stable
contract: requests carry a free-text location *query* that the service resolves,
while responses expose the resolved location and its readings. Read models set
``from_attributes=True`` so they can be built directly from ORM instances.

Cross-field validity (end before start, range too large, etc.) is enforced in
the service layer so it surfaces as ``InvalidDateRangeError`` with the shared
error shape, rather than as a generic 422 validation error here.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LocationRead(BaseModel):
    """A resolved location as stored in the ``locations`` table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    query_text: str
    resolved_name: str
    latitude: Decimal
    longitude: Decimal
    country: str | None = None
    created_at: datetime


class DailyReadingRead(BaseModel):
    """One day's weather within a record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date
    temp_min: Decimal
    temp_max: Decimal
    conditions: str
    aqi: int | None = None


class WeatherRecordRead(BaseModel):
    """A stored weather record with its resolved location and daily readings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location: LocationRead
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime
    readings: list[DailyReadingRead] = Field(default_factory=list)


class RecordCreate(BaseModel):
    """Create a record: a free-text location query plus a date range."""

    location: str = Field(min_length=1, description="Free-text location query.")
    start_date: date
    end_date: date


class RecordUpdate(BaseModel):
    """Patch a record's location and/or date range; all fields optional."""

    location: str | None = Field(default=None, min_length=1)
    start_date: date | None = None
    end_date: date | None = None
