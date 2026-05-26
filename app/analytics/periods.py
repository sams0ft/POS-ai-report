"""Helper: cálculo del período de comparación inmediatamente anterior."""

from datetime import date, timedelta


def calcular_periodo_comparacion(
    fecha_desde: date,
    fecha_hasta: date,
) -> tuple[date, date]:
    """Calcula el período de comparación inmediatamente anterior al rango dado.

    El período de comparación es la ventana de igual duración que termina
    el día antes de fecha_desde.

    Ejemplo: si el reporte es 1-30 de abril (30 días),
    la comparación es 2-31 de marzo.

    Args:
        fecha_desde: Inicio del período actual.
        fecha_hasta: Fin del período actual.

    Returns:
        Tupla (comp_desde, comp_hasta) del período de comparación.
    """
    dias = (fecha_hasta - fecha_desde).days + 1
    comp_hasta = fecha_desde - timedelta(days=1)
    comp_desde = comp_hasta - timedelta(days=dias - 1)
    return comp_desde, comp_hasta
