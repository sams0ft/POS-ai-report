"""Transformer para el bloque anomalias_detectadas del payload."""

import pandas as pd

from app.analytics import anomalies


def transform(
    df_ventas_actual: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    serie_diaria: dict,
) -> list[dict]:
    """Ensambla el bloque anomalias_detectadas del payload.

    Detecta los 3 tipos habilitados: caida_ventas_categoria,
    margen_caido y pico_ventas_inusual.

    Args:
        df_ventas_actual: Ventas del período actual.
        df_ventas_anterior: Ventas del período de comparación.
        df_catalogo: Catálogo de productos.
        serie_diaria: Output de calcular_serie_diaria() con fechas e ingresos.

    Returns:
        Lista de anomalías detectadas con tipo, entidad, descripcion,
        severidad y datos.
    """
    return anomalies.detectar_todas(
        df_ventas_actual, df_ventas_anterior, df_catalogo, serie_diaria
    )
