"""Transformer para el bloque proveedores_top del payload."""

import pandas as pd

from app.analytics import revenue


def transform(
    df_compras: pd.DataFrame,
    df_proveedores: pd.DataFrame,
) -> list[dict]:
    """Ensambla el bloque proveedores_top del payload.

    Args:
        df_compras: Líneas de detalle_compra del período de compras.
        df_proveedores: Catálogo de proveedores con razon_social.

    Returns:
        Lista de dicts con id, razon_social, compras_periodo,
        productos_suministrados, lead_time_dias_prom y pct_compras_total.
    """
    return revenue.calcular_proveedores_top(df_compras, df_proveedores)
