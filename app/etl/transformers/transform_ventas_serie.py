"""Transformer para el bloque ventas_serie_diaria del payload."""

from datetime import date

import pandas as pd

from app.analytics import revenue


def transform(
    df_ventas: pd.DataFrame,
    fecha_desde: date,
    fecha_hasta: date,
) -> dict:
    """Ensambla el bloque ventas_serie_diaria del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        fecha_desde: Primer día del rango.
        fecha_hasta: Último día del rango.

    Returns:
        Dict con arrays paralelos fechas, ingresos, transacciones, unidades.
    """
    return revenue.calcular_serie_diaria(df_ventas, fecha_desde, fecha_hasta)
