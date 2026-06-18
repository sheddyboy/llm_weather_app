"""The `weather_records` table: a stored query of a location over a date range.

Each record belongs to one location and owns a set of `daily_readings`
(ARCHITECTURE §3/§4).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    location: Mapped["Location"] = relationship(  # noqa: F821
        back_populates="records"
    )
    readings: Mapped[list["DailyReading"]] = relationship(  # noqa: F821
        back_populates="record",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_weather_records_location_id", "location_id"),)
