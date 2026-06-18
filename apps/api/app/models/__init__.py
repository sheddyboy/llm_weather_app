"""SQLAlchemy models.

Importing them here registers their tables on `Base.metadata`, which Alembic's
`env.py` relies on for autogenerate (it does `import app.models`).
"""

from app.models.daily_reading import DailyReading
from app.models.location import Location
from app.models.weather_record import WeatherRecord

__all__ = ["DailyReading", "Location", "WeatherRecord"]
