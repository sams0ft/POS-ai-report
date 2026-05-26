"""Transformer para el bloque afinidad_productos del payload."""

import pandas as pd

from app.analytics import promotions


def transform(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
) -> list[dict]:
    """Ensambla el bloque afinidad_productos del payload.

    Solo ejecuta Apriori si hay más de 100 transacciones en el período.
    Retorna lista vacía si no hay suficientes datos.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo de productos (reservado para futuras versiones).

    Returns:
        Lista de dicts con par, co_ocurrencia y lift (top 5 por lift).
    """
    return promotions.calcular_afinidad(df_ventas, df_catalogo)
