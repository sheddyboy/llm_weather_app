"""Application metadata endpoint (`GET /meta`).

Returns the configured application name and description (the PM Accelerator
attribution), consumed by the frontend footer. Values come from settings, so they
are static per process and need no database or external call.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas import MetaResponse

router = APIRouter(tags=["meta"])


@router.get("/meta")
async def get_meta() -> MetaResponse:
    """Return the application name and description for the frontend footer."""
    return MetaResponse(name=settings.meta_name, description=settings.meta_description)
