"""Response schemas for the media-enrichment endpoint (`/records/{id}/media`).

The endpoint combines two independent providers, YouTube videos and Google Places
points of interest, for a record's resolved location. Either list may be empty if
its provider is disabled, unavailable, or over quota: the endpoint degrades
gracefully rather than failing (ARCHITECTURE §6). The field shapes mirror the
normalized dicts produced by the YouTube and Places services.
"""

from pydantic import BaseModel

from app.schemas.records import LocationRead


class VideoItem(BaseModel):
    """One YouTube video about the location."""

    video_id: str
    title: str
    channel: str | None = None
    url: str
    thumbnail: str | None = None


class PointOfInterest(BaseModel):
    """One Google Places point of interest near the location."""

    name: str
    address: str | None = None
    rating: float | None = None
    types: list[str] = []


class MediaResponse(BaseModel):
    """Combined media enrichment for a record's location."""

    location: LocationRead
    videos: list[VideoItem]
    points_of_interest: list[PointOfInterest]
