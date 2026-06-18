"""API routers."""

from app.routers.briefing import router as briefing_router
from app.routers.export import router as export_router
from app.routers.media import router as media_router
from app.routers.meta import router as meta_router
from app.routers.records import router as records_router
from app.routers.weather import router as weather_router

__all__ = [
    "briefing_router",
    "export_router",
    "media_router",
    "meta_router",
    "records_router",
    "weather_router",
]
