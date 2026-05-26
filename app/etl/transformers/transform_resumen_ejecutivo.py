"""Transformer para el bloque resumen_ejecutivo del payload."""

import pandas as pd

from app.analytics import financials


def transform(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_gastos: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    df_gastos_anterior: pd.DataFrame,
) -> dict:
    """Ensambla el bloque resumen_ejecutivo del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo de productos con precio_compra.
        df_gastos: Gastos del período actual.
        df_ventas_anterior: Líneas del período de comparación.
        df_gastos_anterior: Gastos del período de comparación.

    Returns:
        Dict con la forma exacta del bloque resumen_ejecutivo del payload.
    """
    return financials.calcular_resumen_ejecutivo(
        df_ventas, df_catalogo, df_gastos, df_ventas_anterior, df_gastos_anterior
    )
