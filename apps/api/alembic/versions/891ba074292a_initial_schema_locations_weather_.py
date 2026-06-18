"""initial schema: locations, weather_records, daily_readings

Revision ID: 891ba074292a
Revises:
Create Date: 2026-06-18 07:21:05.297376

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "891ba074292a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("resolved_name", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(), nullable=False),
        sa.Column("longitude", sa.Numeric(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "weather_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weather_records_location_id",
        "weather_records",
        ["location_id"],
        unique=False,
    )
    op.create_table(
        "daily_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("temp_min", sa.Numeric(), nullable=False),
        sa.Column("temp_max", sa.Numeric(), nullable=False),
        sa.Column("conditions", sa.Text(), nullable=False),
        sa.Column("aqi", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["record_id"], ["weather_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_readings_record_id",
        "daily_readings",
        ["record_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_readings_record_id_date",
        "daily_readings",
        ["record_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_daily_readings_record_id_date", table_name="daily_readings"
    )
    op.drop_index("ix_daily_readings_record_id", table_name="daily_readings")
    op.drop_table("daily_readings")
    op.drop_index(
        "ix_weather_records_location_id", table_name="weather_records"
    )
    op.drop_table("weather_records")
    op.drop_table("locations")
