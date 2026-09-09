"""Servicio de reportes — lógica de negocio."""

import uuid
from datetime import date, datetime

import structlog
from fastapi import HTTPException

from app.ai.report_generator import generate_report_content
from app.etl.etl_runner import run_etl
from app.etl.json_loader import load_etl_json
from app.schemas.reports import (
    ReportRequest,
    ReportResponse,
    ReportStatus,
    ReportType,
)

logger = structlog.get_logger(__name__)

_MESES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def _formato_periodo(fecha_desde: date, fecha_hasta: date) -> str:
    def _fmt(d: date) -> str:
        return f"{d.day} {_MESES[d.month]} {d.year}"
    return f"{_fmt(fecha_desde)} – {_fmt(fecha_hasta)}"


class ReportService:
    """Orquesta la generación de reportes IA."""

    async def generate_sync(self, request: ReportRequest) -> ReportResponse:
        """Genera el reporte de forma síncrona: ETL → JSON → LM Studio → respuesta.

        El ETL corre en cada request usando el rango de fechas recibido, así que
        no hace falta ejecutarlo antes por CLI. El JSON queda igual en
        `app/etl/output/` y se sobrescribe si ya existía para ese mismo período.

        Args:
            request: Solicitud con empresa_id, fecha_desde y fecha_hasta.

        Returns:
            ReportResponse con status COMPLETED, resumen, sugerencias y datos.

        Raises:
            HTTPException 422: Si el rango de fechas está invertido.
            HTTPException 502: Si el ETL falla, o si LM Studio no responde.
        """
        if request.fecha_desde > request.fecha_hasta:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Rango inválido: fecha_desde ({request.fecha_desde}) es posterior "
                    f"a fecha_hasta ({request.fecha_hasta})."
                ),
            )

        log = logger.bind(
            empresa_id=request.empresa_id,
            fecha_desde=str(request.fecha_desde),
            fecha_hasta=str(request.fecha_hasta),
        )

        # 1. Correr el ETL con el rango pedido en la petición
        log.info("reporte.etl.inicio")
        try:
            await run_etl(request.empresa_id, request.fecha_desde, request.fecha_hasta)
        except Exception as exc:
            log.error("reporte.etl.fallido", error=f"{type(exc).__name__}: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"El ETL falló para el período solicitado: {type(exc).__name__}: {exc}",
            ) from exc

        # 2. Leer el JSON que el ETL acaba de dejar en disco
        try:
            etl_data = load_etl_json(
                request.empresa_id, request.fecha_desde, request.fecha_hasta
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"El ETL terminó sin dejar el archivo esperado: {exc}",
            ) from exc

        log.info("reporte.etl.completado", claves=len(etl_data))

        empresa_nombre: str = (
            etl_data.get("meta", {}).get("empresa_nombre", f"Empresa {request.empresa_id}")
        )
        periodo = _formato_periodo(request.fecha_desde, request.fecha_hasta)

        try:
            result = await generate_report_content(
                analytics_data=etl_data,
                empresa_nombre=empresa_nombre,
                periodo=periodo,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"LM Studio no respondió correctamente: {type(exc).__name__}: {exc}",
            ) from exc

        return ReportResponse(
            report_id=str(uuid.uuid4()),
            empresa_id=request.empresa_id,
            report_type=request.report_type,
            status=ReportStatus.COMPLETED,
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            resumen=result["resumen"],
            sugerencias=result["sugerencias"],
            datos=result["datos"],
        )

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
        """Consulta estado de un reporte."""
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
        raise NotImplementedError("Pendiente: implementar listado de reportes")
