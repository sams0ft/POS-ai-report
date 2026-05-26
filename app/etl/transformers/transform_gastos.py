"""Transformer para el bloque gastos_breakdown del payload."""

import pandas as pd

from app.analytics import expenses


def transform(
    df_gastos: pd.DataFrame,
    df_categorias_gasto: pd.DataFrame,
) -> list[dict]:
    """Ensambla el bloque gastos_breakdown del payload.

    Args:
        df_gastos: Gastos del período actual con id_categoria_gasto y monto.
        df_categorias_gasto: Catálogo de categorías de gasto con nombre.

    Returns:
        Lista de dicts con categoria, monto y pct (top 5 + Otros).
    """
    return expenses.calcular_gastos_breakdown(df_gastos, df_categorias_gasto)
