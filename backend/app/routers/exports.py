from fastapi import APIRouter, HTTPException

from ..models.schemas import ExportRequest, ExportResponse
from ..services.export_service import export_zip, export_excel, export_txt

router = APIRouter(tags=["exports"])


@router.post(
    "/projects/{project_id}/export",
    response_model=ExportResponse,
)
async def api_export(project_id: int, data: ExportRequest):
    if data.format == "zip":
        path = await export_zip(project_id)
    elif data.format == "excel":
        path = await export_excel(project_id)
    elif data.format == "txt":
        path = await export_txt(project_id)
    else:
        raise HTTPException(400, "Invalid format")
    return ExportResponse(file_path=path)
