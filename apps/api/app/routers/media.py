"""Media enrichment for a stored record (`GET /records/{id}/media`).

Combines two independent providers for the record's resolved location: YouTube
videos (about the location name) and Google Places points of interest (near the
coordinates). Each provider is called independently and degrades gracefully: if
one is over quota or otherwise unavailable it raises
:class:`ExternalAPIQuotaExceededError`, which is caught here so its section comes
back empty while the other still returns, rather than failing the whole request
(ARCHITECTURE §6). A missing record raises :class:`RecordNotFoundError` (the
shared error envelope).
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_places_service,
    get_repository,
    get_youtube_service,
)
from app.exceptions import ExternalAPIQuotaExceededError, RecordNotFoundError
from app.repositories import WeatherRepository
from app.schemas import MediaResponse
from app.services import PlacesService, YouTubeService

router = APIRouter(prefix="/records", tags=["media"])


@router.get("/{record_id}/media", response_model=MediaResponse)
async def get_record_media(
    record_id: UUID,
    repository: WeatherRepository = Depends(get_repository),
    youtube: YouTubeService = Depends(get_youtube_service),
    places: PlacesService = Depends(get_places_service),
) -> MediaResponse:
    """Return YouTube videos + Places POIs for the record's location."""
    record = await repository.get_record(record_id)
    if record is None:
        raise RecordNotFoundError()

    location = record.location
    videos = await _safely(youtube.search_videos(location.resolved_name))
    points_of_interest = await _safely(
        places.search_nearby(float(location.latitude), float(location.longitude))
    )
    return MediaResponse(
        location=location,
        videos=videos,
        points_of_interest=points_of_interest,
    )


async def _safely(coro) -> list:
    """Await ``coro``, returning an empty list if its provider is over quota."""
    try:
        return await coro
    except ExternalAPIQuotaExceededError:
        return []
