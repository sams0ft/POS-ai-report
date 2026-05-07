"""Endpoints de reportes IA."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.schemas.reports import (
    ReportRequest,
    ReportResponse,
    ReportType,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """Genera un reporte IA bajo demanda.

    El reporte se encola como tarea async y retorna un ID para consultar el estado.
    """
    service = ReportService()
    result = await service.enqueue_report(request)
    return result


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Consulta el estado y resultado de un reporte generado."""
    service = ReportService()
    return await service.get_report(report_id)


@router.get("/empresa/{empresa_id}")
async def list_reports(
    empresa_id: int,
    report_type: ReportType | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(default=20, le=100),
):
    """Lista reportes generados para una empresa."""
    service = ReportService()
    return await service.list_reports(
        empresa_id=empresa_id,
        report_type=report_type,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
