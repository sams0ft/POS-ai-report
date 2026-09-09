"""Transformer para el bloque ventas_flash del payload."""

from datetime import date

from app.analytics.flash_sales import (
    armar_bloque_ventas_flash,
    calcular_candidato_flash,
    calcular_dia_objetivo,
)


def transform(
    raw_flash: dict,
    dias_periodo: int,
    fecha_hasta: date,
) -> dict | None:
    """Ensambla el bloque ventas_flash del payload.

    Orquesta las funciones de analytics sin lógica de negocio propia.

    Args:
        raw_flash: Dict con ``dia_debil_crudo`` y ``pool_productos_crudo``
            (resultado de get_flash_sales_data).
        dias_periodo: Días del período analizado.
        fecha_hasta: Fecha de corte para calcular dias_para_vencer.

    Returns:
        Dict listo para la key ``ventas_flash``, o None si no hay datos
        suficientes para armar una sugerencia coherente.
    """
    dia_objetivo = calcular_dia_objetivo(raw_flash.get("dia_debil_crudo", []))
    candidato = calcular_candidato_flash(
        raw_flash.get("pool_productos_crudo", []),
        dias_periodo,
        fecha_hasta,
    )
    return armar_bloque_ventas_flash(dia_objetivo, candidato)
