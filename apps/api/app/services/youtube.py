"""YouTube Data API v3 enrichment: videos about a location.

`search.list` is the tightest external quota in the whole system (a single search
costs 100 of the default 10,000 daily units, ARCHITECTURE §6/§12), so this service
is aggressively cache-first against the :class:`CacheBackend`: results key on the
search query and are stored for :data:`YOUTUBE_TTL` (7 days), since videos about a
place barely change.

The service is gated by ``ENABLE_YOUTUBE`` (default ``true``). When the flag is
turned off, it returns deterministic *stub* results without making any HTTP call
or touching the cache, so the integration can be switched to a safe fallback if
real quota ever becomes a problem. Any transport/HTTP failure (including a 403
quota rejection) surfaces as :class:`ExternalAPIQuotaExceededError`, which the
``/media`` endpoint catches to degrade gracefully rather than fail.
"""

import httpx

from app.core.cache import CacheBackend
from app.core.config import settings
from app.core.logging import logger
from app.exceptions import ExternalAPIQuotaExceededError

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
WATCH_URL = "https://www.youtube.com/watch?v="

YOUTUBE_TTL = 7 * 24 * 3600  # 7 days; quota-driven, results barely change

_TIMEOUT = 10.0
_MAX_RESULTS = 5


class YouTubeService:
    """Cache-first YouTube search, with a flag-gated stub fallback."""

    def __init__(
        self,
        cache: CacheBackend,
        *,
        api_key: str | None = None,
        enabled: bool | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cache = cache
        self._api_key = api_key if api_key is not None else settings.youtube_api_key
        self._enabled = enabled if enabled is not None else settings.enable_youtube
        self._client = client

    async def search_videos(
        self, query: str, *, max_results: int = _MAX_RESULTS
    ) -> list[dict]:
        """Return normalized videos for ``query`` (cache-first, or stub if disabled)."""
        query = query.strip()
        if not self._enabled:
            logger.debug("YouTube disabled; returning stub results for {!r}", query)
            return _stub_videos(query)

        key = f"youtube:search:{query.lower()}"
        cached = await self._cache.get(key)
        if cached is not None:
            logger.debug("YouTube cache hit for {!r}", query)
            return cached
        logger.debug("YouTube cache miss for {!r}", query)
        videos = _parse_videos(await self._get(query, max_results))
        await self._cache.set(key, videos, ttl=YOUTUBE_TTL)
        return videos

    async def _get(self, query: str, max_results: int) -> dict:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self._api_key,
        }
        try:
            if self._client is not None:
                response = await self._client.get(SEARCH_URL, params=params)
            else:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("YouTube search failed: {}", exc)
            raise ExternalAPIQuotaExceededError(
                "The YouTube API is unavailable or its quota has been reached."
            ) from exc


def _parse_videos(data: dict) -> list[dict]:
    """Normalize a `search.list` response to a small list of video dicts."""
    videos: list[dict] = []
    for item in data.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet") or {}
        thumbnails = snippet.get("thumbnails") or {}
        medium = thumbnails.get("medium") or thumbnails.get("default") or {}
        videos.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle"),
                "url": f"{WATCH_URL}{video_id}",
                "thumbnail": medium.get("url"),
            }
        )
    return videos


def _stub_videos(query: str) -> list[dict]:
    """Deterministic placeholder results used when YouTube is disabled."""
    return [
        {
            "video_id": "stub-youtube",
            "title": f"{query} weather and travel guide",
            "channel": "Weather App (stub)",
            "url": f"{WATCH_URL}stub-youtube",
            "thumbnail": None,
        }
    ]


__all__ = ["YouTubeService", "SEARCH_URL", "YOUTUBE_TTL"]
