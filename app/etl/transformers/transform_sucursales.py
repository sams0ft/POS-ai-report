"""Transformer para el bloque sucursales del payload."""

import pandas as pd

from app.analytics import revenue


def transform(
    df_ventas: pd.DataFrame,
    df_sucursales: pd.DataFrame,
) -> list[dict]:
    """Ensambla el bloque sucursales del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_sucursales: Catálogo de sucursales con id_sucursal y nombre.

    Returns:
        Lista de dicts con id, nombre, ingresos, transacciones,
        ticket_promedio y pct_total.
    """
    return revenue.calcular_por_sucursal(df_ventas, df_sucursales)
