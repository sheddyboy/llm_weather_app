"""The `daily_readings` table: one row per day within a weather record.

The composite `(record_id, date)` index serves the export and briefing queries
that pull a record's full reading set in date order (ARCHITECTURE §4).
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyReading(Base):
    __tablename__ = "daily_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("weather_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_min: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    temp_max: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    conditions: Mapped[str] = mapped_column(Text, nullable=False)
    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True)

    record: Mapped["WeatherRecord"] = relationship(  # noqa: F821
        back_populates="readings"
    )

    __table_args__ = (
        Index("ix_daily_readings_record_id", "record_id"),
        Index("ix_daily_readings_record_id_date", "record_id", "date"),
    )
