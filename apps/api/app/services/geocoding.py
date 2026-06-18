"""Geocoding: resolve a free-text location query to coordinates.

Unlike the live weather data (which lives in a TTL cache), resolved locations are
persisted permanently in the `locations` table (ARCHITECTURE §3/§7): a location
string essentially never changes the coordinates it resolves to, and the table
doubles as the FK target for records. So this service is "cache-first" against
the database, not against the ephemeral cache layer: if the query was resolved
before, the stored row is returned and no external call is made.

OpenWeatherMap's Free Access direct-geocoding API is used for the lookup. An empty
result surfaces as :class:`LocationNotFoundError`; any transport/HTTP failure
surfaces as :class:`WeatherProviderError`, never a raw ``httpx`` error.
"""

from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.exceptions import LocationNotFoundError, WeatherProviderError
from app.models import Location
from app.repositories import WeatherRepository

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
_TIMEOUT = 10.0


class GeocodingService:
    """Resolve location queries to persisted :class:`Location` rows."""

    def __init__(
        self,
        repository: WeatherRepository,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._repo = repository
        self._api_key = api_key if api_key is not None else settings.openweather_api_key
        self._client = client

    async def resolve(self, query: str) -> Location:
        """Resolve ``query`` to a :class:`Location`, persisting it on first sight.

        Returns the existing row if the query was resolved before (no external
        call). Raises :class:`LocationNotFoundError` if the provider returns no
        match.
        """
        query = query.strip()
        existing = await self._repo.get_location_by_query(query)
        if existing is not None:
            logger.debug("Geocoding cache hit (locations table) for {!r}", query)
            return existing

        match = await self._geocode(query)
        resolved_name = _format_name(match)
        return await self._repo.get_or_create_location(
            query_text=query,
            resolved_name=resolved_name,
            latitude=Decimal(str(match["lat"])),
            longitude=Decimal(str(match["lon"])),
            country=match.get("country"),
        )

    async def _geocode(self, query: str) -> dict:
        """Call the direct-geocoding API and return the top match."""
        params = {"q": query, "limit": 1, "appid": self._api_key}
        data = await self._get(params)
        if not data:
            raise LocationNotFoundError(
                f"No matching location could be found for {query!r}."
            )
        return data[0]

    async def _get(self, params: dict) -> list:
        try:
            if self._client is not None:
                response = await self._client.get(GEOCODE_URL, params=params)
            else:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.get(GEOCODE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Geocoding request failed: {}", exc)
            raise WeatherProviderError(
                "The geocoding provider is currently unavailable."
            ) from exc


def _format_name(match: dict) -> str:
    """Build a human-readable resolved name from a geocoding match."""
    parts = [match.get("name"), match.get("state"), match.get("country")]
    return ", ".join(part for part in parts if part)


__all__ = ["GeocodingService", "GEOCODE_URL"]
