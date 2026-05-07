"""Servicio de reportes — lógica de negocio."""

import uuid
from datetime import date, datetime

from app.schemas.reports import (
    ReportRequest,
    ReportResponse,
    ReportStatus,
    ReportType,
)


class ReportService:
    """Orquesta la generación de reportes IA."""

    async def enqueue_report(self, request: ReportRequest) -> ReportResponse:
        """Encola un reporte para generación async.

        Retorna inmediatamente con status PENDING y un report_id
        para que el cliente haga polling.
        """
        report_id = str(uuid.uuid4())

        # TODO: guardar en DB analítica
        # TODO: encolar tarea Celery → report_tasks.generate_report.delay(report_id)

        return ReportResponse(
            report_id=report_id,
            empresa_id=request.empresa_id,
            report_type=request.report_type,
            status=ReportStatus.PENDING,
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
            created_at=datetime.now(),
        )

    async def get_report(self, report_id: str) -> ReportResponse:
        """Consulta estado de un reporte.

        Primero revisa caché Redis, luego DB analítica.
        """
        # TODO: buscar en Redis (caché)
        # TODO: buscar en DB analítica
        raise NotImplementedError("Pendiente: implementar consulta de reportes")

    async def list_reports(
        self,
        empresa_id: int,
        report_type: ReportType | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        limit: int = 20,
    ) -> list[ReportResponse]:
        """Lista reportes de una empresa con filtros opcionales."""
        # TODO: query a DB analítica con filtros
        raise NotImplementedError("Pendiente: implementar listado de reportes")
