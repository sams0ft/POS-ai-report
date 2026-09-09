"""Endpoints de reportes IA."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.reports import ReportRequest, ReportResponse, ReportType
from app.services.report_service import ReportService

router = APIRouter()
_service = ReportService()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """Genera un reporte completo de forma síncrona: ETL → JSON → LM Studio → respuesta.

    Body: empresa_id, fecha_desde, fecha_hasta (report_type ignorado).
    El ETL corre dentro de la misma petición con el rango de fechas recibido;
    no hace falta ejecutarlo antes por CLI.
    """
    return await _service.generate_sync(request)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Consulta el estado de un reporte por ID."""
    raise HTTPException(status_code=501, detail="Pendiente de implementar.")


@router.get("/empresa/{empresa_id}")
async def list_reports(
    empresa_id: int,
    report_type: ReportType | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(default=20, le=100),
):
    """Lista reportes generados de una empresa."""
    raise HTTPException(status_code=501, detail="Pendiente de implementar.")
