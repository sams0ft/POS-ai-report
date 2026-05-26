"""Transformer para inventario_salud, alertas_stock y perecederos_riesgo."""

from datetime import date

import pandas as pd

from app.analytics import expiry_tracker, inventory_health, stock_predictor


def transform(
    df_inventario: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_ventas: pd.DataFrame,
    df_velocidad: pd.DataFrame,
    df_bottom: list[dict],
    dias_periodo: int,
    fecha_hasta: date,
) -> tuple[dict, list[dict], list[dict]]:
    """Ensambla inventario_salud, alertas_stock y perecederos_riesgo.

    Args:
        df_inventario: Inventario actual por producto/sucursal.
        df_catalogo: Catálogo con precio_compra y stock_minimo.
        df_ventas: Ventas del período actual (para calcular CMV).
        df_velocidad: Velocidad de venta por producto.
        df_bottom: Productos bottom ya calculados (para valor inmovilizado).
        dias_periodo: Número de días del período del reporte.
        fecha_hasta: Fecha de referencia para perecederos.

    Returns:
        Tupla (inventario_salud dict, alertas_stock list, perecederos_riesgo list).
    """
    salud = inventory_health.calcular_inventario_salud(
        df_inventario, df_catalogo, df_ventas, df_bottom, dias_periodo
    )
    alertas = stock_predictor.calcular_alertas_stock(
        df_inventario, df_velocidad, df_catalogo
    )
    perecederos = expiry_tracker.calcular_perecederos_riesgo(
        df_inventario, df_velocidad, df_catalogo, fecha_hasta
    )
    return salud, alertas, perecederos
