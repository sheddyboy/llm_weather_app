"""The `locations` table: resolved geocoding results, stored permanently.

Per ARCHITECTURE §3/§4, a location string resolving to coordinates essentially
never changes, so resolved locations live here rather than in a TTL cache. This
table doubles as the permanent geocoding cache and as the FK target for records.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_name: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    records: Mapped[list["WeatherRecord"]] = relationship(  # noqa: F821
        back_populates="location",
        cascade="all, delete-orphan",
    )
