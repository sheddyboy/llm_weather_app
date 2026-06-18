"""Export a stored weather record (`GET /records/{id}/export`).

Looks the record up, renders it in the requested format via the export service,
and returns it with the matching media type plus a download-friendly
``Content-Disposition`` filename. The ``format`` query parameter is typed as
:class:`~app.services.export_service.ExportFormat`, so an unsupported value is
rejected by FastAPI as a 422 before any work is done; a missing record raises
:class:`RecordNotFoundError` (the shared error envelope).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import get_repository
from app.exceptions import RecordNotFoundError
from app.repositories import WeatherRepository
from app.schemas import WeatherRecordRead
from app.services import export_service
from app.services.export_service import ExportFormat

router = APIRouter(prefix="/records", tags=["export"])


@router.get("/{record_id}/export")
async def export_record(
    record_id: UUID,
    format: ExportFormat = Query(ExportFormat.JSON),
    repository: WeatherRepository = Depends(get_repository),
) -> Response:
    """Return the record rendered in ``format`` as a downloadable attachment."""
    record = await repository.get_record(record_id)
    if record is None:
        raise RecordNotFoundError()

    schema = WeatherRecordRead.model_validate(record)
    content, media_type, extension = export_service.render(schema, format)
    filename = f"record-{record_id}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
