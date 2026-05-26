"""Endpoints de reportes IA."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.report_generator import generate_report_content
from app.analytics.product_ranking import calcular_ranking_productos
from app.core.database import get_pos_db
from app.schemas.reports import (
    ReportRequest,
    ReportResponse,
    ReportStatus,
    ReportType,
)

router = APIRouter()


# Dispatch: tipo de reporte → motor analítico
# Cuando agregues más motores (revenue, peak_hours, etc.), regístralos aquí.
ANALYTICS_DISPATCH = {
    ReportType.TOP_BOTTOM_PRODUCTOS: calcular_ranking_productos,
}


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    pos_db: AsyncSession = Depends(get_pos_db),
):
    """Genera un reporte IA de forma SÍNCRONA (modo dev).

    Flujo: analytics → LLM → respuesta inmediata.
    No persiste, no encola, no cachea. Devuelve el reporte completo
    en la misma respuesta HTTP.
    """
    if request.report_type not in ANALYTICS_DISPATCH:
        raise HTTPException(
            status_code=501,
            detail=f"El reporte '{request.report_type}' aún no está implementado.",
        )

    # 1. Obtener nombre de la empresa
    result = await pos_db.execute(
        text("SELECT nombre FROM system_pos.empresa WHERE id_empresa = :id"),
        {"id": request.empresa_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(404, f"Empresa {request.empresa_id} no encontrada.")
    empresa_nombre = row[0]

    # 2. Ejecutar motor analítico
    analytics_fn = ANALYTICS_DISPATCH[request.report_type]
    analytics_data = await analytics_fn(
        pos_db=pos_db,
        empresa_id=request.empresa_id,
        fecha_desde=request.fecha_desde.isoformat(),
        fecha_hasta=request.fecha_hasta.isoformat(),
    )

    # 3. Pasar al LLM
    periodo_str = f"{request.fecha_desde} → {request.fecha_hasta}"
    try:
        contenido = await generate_report_content(
            report_type=request.report_type,
            analytics_data=analytics_data,
            empresa_nombre=empresa_nombre,
            periodo=periodo_str,
        )
    except ValueError as e:
        # JSON del LLM mal formado
        raise HTTPException(
            status_code=502,
            detail=f"El LLM devolvió una respuesta inválida: {e}",
        )

    # 4. Armar respuesta
    now = datetime.now()
    return ReportResponse(
        report_id=f"sync-{int(now.timestamp())}",
        empresa_id=request.empresa_id,
        report_type=request.report_type,
        status=ReportStatus.COMPLETED,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        created_at=now,
        completed_at=now,
        resumen=contenido["resumen"],
        datos=contenido["datos"],
        insights=contenido["insights"],
        recomendaciones=contenido["recomendaciones"],
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Consulta el estado de un reporte. (No disponible en modo síncrono.)"""
    raise HTTPException(
        status_code=501,
        detail="Endpoint disponible solo en modo async (Celery + DB).",
    )


@router.get("/empresa/{empresa_id}")
async def list_reports(
    empresa_id: int,
    report_type: ReportType | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(default=20, le=100),
):
    """Lista reportes generados. (No disponible en modo síncrono.)"""
    raise HTTPException(
        status_code=501,
        detail="Endpoint disponible solo en modo async (Celery + DB).",
    )
