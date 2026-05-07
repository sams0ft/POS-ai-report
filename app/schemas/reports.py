"""Schemas Pydantic para reportes."""

from datetime import date, datetime
from enum import StrEnum

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
    report_type: ReportType
    fecha_desde: date
    fecha_hasta: date
    parametros: dict | None = Field(default=None, description="Parámetros adicionales por tipo")


class ReportResponse(BaseModel):
    """Respuesta con el reporte generado o su estado."""

    report_id: str
    empresa_id: int
    report_type: ReportType
    status: ReportStatus
    fecha_desde: date
    fecha_hasta: date
    created_at: datetime
    completed_at: datetime | None = None

    # Contenido del reporte (solo cuando status=completed)
    resumen: str | None = None
    datos: dict | None = Field(default=None, description="Datos numéricos del análisis")
    sugerencias: list[str] | None = Field(default=None, description="Sugerencias generadas por IA")
    pdf_url: str | None = None
