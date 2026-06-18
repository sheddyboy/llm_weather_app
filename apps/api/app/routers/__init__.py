"""API routers."""

from app.routers.records import router as records_router
from app.routers.weather import router as weather_router

__all__ = ["records_router", "weather_router"]
