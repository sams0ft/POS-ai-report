"""Schemas Pydantic para reportes."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(StrEnum):
    """Tipos de reporte disponibles."""

    INGRESOS_EGRESOS = "ingresos_egresos"
    TOP_BOTTOM_PRODUCTOS = "top_bottom_productos"
    HORAS_MAGICAS = "horas_magicas"
    ANTI_DESPERDICIO = "anti_desperdicio"
    PRECIO_OPTIMO = "precio_optimo"
    PROMOCIONES = "promociones"
    QUIEBRE_STOCK = "quiebre_stock"
    SCORE_SALUD = "score_salud"
    EJECUTIVO_COMPLETO = "ejecutivo_completo"


class ReportStatus(StrEnum):
    """Estado del reporte."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportRequest(BaseModel):
    """Solicitud de generación de reporte."""

    empresa_id: int
    fecha_desde: date
    fecha_hasta: date
    report_type: ReportType | None = None
    parametros: dict | None = Field(default=None, description="Parámetros adicionales por tipo")


class InsightItem(BaseModel):
    """Hallazgo del análisis (mapea 1:1 a system_pos.insight_ia)."""

    titulo: str
    descripcion: str
    severidad: str = "info"  # info | success | warning | error | critical


class RecomendacionItem(BaseModel):
    """Acción sugerida (mapea 1:1 a system_pos.recomendacion_ia)."""

    titulo: str
    descripcion: str
    accion_sugerida: str
    prioridad: str = "media"  # baja | media | alta | critica
    impacto_estimado: float | None = None
    producto_id: int | None = None


class ReportResponse(BaseModel):
    """Respuesta con el reporte generado o su estado."""

    report_id: str
    empresa_id: int
    report_type: ReportType | None = None
    status: ReportStatus
    fecha_desde: date
    fecha_hasta: date
    created_at: datetime
    completed_at: datetime | None = None

    # Contenido del reporte (solo cuando status=completed)
    resumen: str | None = None
    sugerencias: list[str] = Field(
        default_factory=list, description="Acciones accionables extraídas del análisis"
    )
    datos: dict[str, Any] | None = Field(
        default=None, description="Datos numéricos del análisis"
    )
    insights: list[InsightItem] = Field(
        default_factory=list, description="Hallazgos generados por IA"
    )
    recomendaciones: list[RecomendacionItem] = Field(
        default_factory=list, description="Acciones sugeridas por IA"
    )
