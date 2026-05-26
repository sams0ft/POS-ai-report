"""Transformer para el bloque metodos_pago del payload."""

import pandas as pd

from app.analytics import revenue


def transform(df_ventas: pd.DataFrame) -> list[dict]:
    """Ensambla el bloque metodos_pago del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.

    Returns:
        Lista de dicts con id, nombre, monto, transacciones y pct por método.
    """
    return revenue.calcular_metodos_pago(df_ventas)
