"""Transformer para el bloque meta del payload."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

_BOGOTA_TZ = ZoneInfo("America/Bogota")


def transform(
    empresa_id: int,
    empresa_info: dict,
    fecha_desde: date,
    fecha_hasta: date,
    fecha_comp_desde: date,
    fecha_comp_hasta: date,
    dias_periodo: int,
    dias_operados: int,
) -> dict:
    """Ensambla el bloque meta del payload.

    Args:
        empresa_id: ID de la empresa.
        empresa_info: Dict con nombre y sector_economico.
        fecha_desde: Inicio del período actual.
        fecha_hasta: Fin del período actual.
        fecha_comp_desde: Inicio del período de comparación.
        fecha_comp_hasta: Fin del período de comparación.
        dias_periodo: Días calendario del período.
        dias_operados: Días con al menos una venta en el período.

    Returns:
        Dict con la forma exacta del bloque meta del payload.
    """
    return {
        "id_empresa": empresa_id,
        "empresa_nombre": str(empresa_info.get("nombre", f"Empresa {empresa_id}")),
        "sector": str(empresa_info.get("sector_economico", "")),
        "moneda": "COP",
        "periodo": {
            "fecha_inicio": fecha_desde.isoformat(),
            "fecha_fin": fecha_hasta.isoformat(),
            "dias_calendario": dias_periodo,
            "dias_operados": dias_operados,
        },
        "periodo_comparacion": {
            "fecha_inicio": fecha_comp_desde.isoformat(),
            "fecha_fin": fecha_comp_hasta.isoformat(),
        },
        "generado_at": datetime.now(tz=_BOGOTA_TZ).isoformat(),
        "version_schema": "1.0",
    }
