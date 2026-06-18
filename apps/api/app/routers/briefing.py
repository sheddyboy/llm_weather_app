"""LLM briefing for a stored record (`GET /records/{id}/briefing`).

Looks the record up, converts it to the :class:`WeatherRecordRead` contract, and
asks the briefing service for a structured OpenAI-generated summary. The service
is cache-first on a fingerprint of the record's data, so repeated requests for an
unchanged record don't re-pay for the LLM call. A missing record raises
:class:`RecordNotFoundError` (the shared error envelope).
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_briefing_service, get_repository
from app.exceptions import RecordNotFoundError
from app.repositories import WeatherRepository
from app.schemas import BriefingResponse, WeatherRecordRead
from app.services import BriefingService

router = APIRouter(prefix="/records", tags=["briefing"])


@router.get("/{record_id}/briefing", response_model=BriefingResponse)
async def get_record_briefing(
    record_id: UUID,
    repository: WeatherRepository = Depends(get_repository),
    briefing: BriefingService = Depends(get_briefing_service),
) -> BriefingResponse:
    """Return an OpenAI-generated briefing for the record's weather."""
    record = await repository.get_record(record_id)
    if record is None:
        raise RecordNotFoundError()

    schema = WeatherRecordRead.model_validate(record)
    return await briefing.generate_briefing(schema)
