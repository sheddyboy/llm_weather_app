"""Google Places enrichment: points of interest near a location.

Uses the Places API (New) Nearby Search against the resolved coordinates to
surface points of interest. Per Google's March 2025 pricing change the API needs
a billing account on file, so this service degrades gracefully: any failure
surfaces as :class:`ExternalAPIQuotaExceededError`, which the ``/media`` endpoint
catches so the rest of the response (the YouTube videos) still returns rather than
the whole request failing (ARCHITECTURE §6/§12).

Results are cache-first against the :class:`CacheBackend`, keyed on the rounded
coordinates and stored for :data:`PLACES_TTL` (7 days), since points of interest
are stable. The service is gated by ``ENABLE_PLACES`` (default ``true``); turning
the flag off returns deterministic *stub* results with no HTTP call or cache use,
giving a safe fallback if billing or quota ever becomes a problem.
"""

import httpx

from app.core.cache import CacheBackend
from app.core.config import settings
from app.core.logging import logger
from app.exceptions import ExternalAPIQuotaExceededError

NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
_FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.types,places.rating"
)

PLACES_TTL = 7 * 24 * 3600  # 7 days; billing-driven, points of interest are stable

_TIMEOUT = 10.0
_MAX_RESULTS = 5
_RADIUS_METERS = 5000.0


class PlacesService:
    """Cache-first Places Nearby Search, with a flag-gated stub fallback."""

    def __init__(
        self,
        cache: CacheBackend,
        *,
        api_key: str | None = None,
        enabled: bool | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cache = cache
        self._api_key = (
            api_key if api_key is not None else settings.google_places_api_key
        )
        self._enabled = enabled if enabled is not None else settings.enable_places
        self._client = client

    async def search_nearby(
        self, lat: float, lon: float, *, max_results: int = _MAX_RESULTS
    ) -> list[dict]:
        """Return normalized POIs near the coordinates (cache-first, or stub)."""
        if not self._enabled:
            logger.debug("Places disabled; returning stub results")
            return _stub_places()

        key = f"places:nearby:{lat:.4f}:{lon:.4f}"
        cached = await self._cache.get(key)
        if cached is not None:
            logger.debug("Places cache hit for {}", key)
            return cached
        logger.debug("Places cache miss for {}", key)
        places = _parse_places(await self._post(lat, lon, max_results))
        await self._cache.set(key, places, ttl=PLACES_TTL)
        return places

    async def _post(self, lat: float, lon: float, max_results: int) -> dict:
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }
        body = {
            "maxResultCount": max_results,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lon},
                    "radius": _RADIUS_METERS,
                }
            },
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    NEARBY_URL, headers=headers, json=body
                )
            else:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.post(
                        NEARBY_URL, headers=headers, json=body
                    )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Places nearby search failed: {}", exc)
            raise ExternalAPIQuotaExceededError(
                "The Google Places API is unavailable or its billing limit "
                "has been reached."
            ) from exc


def _parse_places(data: dict) -> list[dict]:
    """Normalize a Nearby Search response to a small list of POI dicts."""
    places: list[dict] = []
    for place in data.get("places", []):
        name = (place.get("displayName") or {}).get("text")
        if not name:
            continue
        places.append(
            {
                "name": name,
                "address": place.get("formattedAddress"),
                "rating": place.get("rating"),
                "types": place.get("types") or [],
            }
        )
    return places


def _stub_places() -> list[dict]:
    """Deterministic placeholder results used when Places is disabled."""
    return [
        {
            "name": "Local Point of Interest (stub)",
            "address": None,
            "rating": None,
            "types": ["point_of_interest"],
        }
    ]


__all__ = ["PlacesService", "NEARBY_URL", "PLACES_TTL"]
