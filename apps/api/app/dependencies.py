"""FastAPI dependency providers wiring the routers to the data and service layers.

Routers declare these via ``Depends`` so the wiring (which session, which cache,
which provider) lives in one place and can be swapped wholesale in tests through
``app.dependency_overrides``. The repository is bound to the request-scoped
session from :func:`app.core.database.get_db`; the geocoding service shares that
same repository so a location it resolves is visible to the record it backs.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, get_cache
from app.core.database import get_db
from app.repositories import WeatherRepository
from app.services import (
    GeocodingService,
    PlacesService,
    WeatherProvider,
    YouTubeService,
)


def get_repository(session: AsyncSession = Depends(get_db)) -> WeatherRepository:
    """Repository bound to the request-scoped database session."""
    return WeatherRepository(session)


def get_cache_backend() -> CacheBackend:
    """The process-wide cache backend selected by settings."""
    return get_cache()


def get_geocoding_service(
    repository: WeatherRepository = Depends(get_repository),
) -> GeocodingService:
    """Geocoding service sharing the request's repository/session."""
    return GeocodingService(repository)


def get_weather_provider(
    cache: CacheBackend = Depends(get_cache_backend),
) -> WeatherProvider:
    """Cache-first OpenWeatherMap provider."""
    return WeatherProvider(cache)


def get_youtube_service(
    cache: CacheBackend = Depends(get_cache_backend),
) -> YouTubeService:
    """Cache-first YouTube enrichment service (flag-gated by ENABLE_YOUTUBE)."""
    return YouTubeService(cache)


def get_places_service(
    cache: CacheBackend = Depends(get_cache_backend),
) -> PlacesService:
    """Cache-first Google Places enrichment service (flag-gated by ENABLE_PLACES)."""
    return PlacesService(cache)
