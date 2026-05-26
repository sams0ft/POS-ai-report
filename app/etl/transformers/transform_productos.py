"""Transformer para los bloques productos_top, productos_bottom y categorias."""

from datetime import date

import pandas as pd

from app.analytics import product_ranking


def transform(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_inventario: pd.DataFrame,
    df_velocidad: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    fecha_hasta: date,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Ensambla los bloques productos_top, productos_bottom y categorias.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo enriquecido con categoria_nombre y marca_nombre.
        df_inventario: Inventario actual por producto/sucursal.
        df_velocidad: Velocidad de venta por producto (30 días).
        df_ventas_anterior: Líneas del período de comparación.
        fecha_hasta: Fecha de fin del período (para calcular dias_sin_venta en bottom).

    Returns:
        Tupla (productos_top, productos_bottom, categorias).
    """
    top = product_ranking.calcular_top_productos(
        df_ventas, df_catalogo, df_inventario, df_velocidad, df_ventas_anterior
    )
    bottom = product_ranking.calcular_bottom_productos(
        df_ventas, df_catalogo, df_inventario, fecha_hasta
    )
    categorias = product_ranking.calcular_categorias(
        df_ventas, df_catalogo, df_ventas_anterior
    )
    return top, bottom, categorias
