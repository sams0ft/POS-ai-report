"""Analytics: alertas de quiebre de stock y velocidad de venta."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def calcular_velocidad_venta(
    df_ventas_velocidad: pd.DataFrame,
    fecha_hasta: date,
    ventana_dias: int = 30,
) -> pd.DataFrame:
    """Calcula la velocidad de venta diaria promedio por producto (ultimos N dias).

    Args:
        df_ventas_velocidad: Lineas de ventas de los ultimos ventana_dias dias.
        fecha_hasta: Fecha de referencia (ultimo dia de la ventana).
        ventana_dias: Dias de la ventana de calculo.

    Returns:
        DataFrame con id_producto, unidades_30d, velocidad_diaria.
    """
    if df_ventas_velocidad.empty:
        return pd.DataFrame(columns=["id_producto", "unidades_30d", "velocidad_diaria"])

    df = df_ventas_velocidad.copy()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)

    agg = df.groupby("id_producto")["cantidad"].sum().reset_index(name="unidades_30d")
    agg["velocidad_diaria"] = (agg["unidades_30d"] / ventana_dias).round(4)

    return agg[["id_producto", "unidades_30d", "velocidad_diaria"]]


def calcular_alertas_stock(
    df_inventario: pd.DataFrame,
    df_velocidad: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    max_dias: float = 7.0,
    limite: int = 15,
) -> list[dict]:
    """Identifica productos con riesgo de quiebre de stock inminente.

    Solo incluye productos con dias_restantes <= max_dias y stock > 0.

    Args:
        df_inventario: Inventario actual con stock_actual por sucursal.
        df_velocidad: DataFrame con id_producto y velocidad_diaria.
        df_catalogo: Productos del catalogo (para el nombre).
        max_dias: Umbral de dias restantes para incluir en alertas.
        limite: Maximo de alertas a retornar.

    Returns:
        Lista de dicts con id_producto, nombre, stock, venta_diaria,
        dias_restantes, severidad. Ordenada por dias_restantes asc.
    """
    if df_inventario.empty or df_velocidad.empty:
        return []

    df_inv = df_inventario.copy()
    df_inv["stock_actual"] = pd.to_numeric(df_inv["stock_actual"], errors="coerce").fillna(0)
    stock_agg = df_inv.groupby("id_producto")["stock_actual"].sum().reset_index()

    df = stock_agg.merge(df_velocidad[["id_producto", "velocidad_diaria"]], on="id_producto", how="inner")
    df = df[(df["velocidad_diaria"] > 0) & (df["stock_actual"] > 0)]

    if df.empty:
        return []

    df["dias_restantes"] = (df["stock_actual"] / df["velocidad_diaria"]).round(1)
    df = df[df["dias_restantes"] <= max_dias].sort_values("dias_restantes")

    if not df_catalogo.empty and "id_producto" in df_catalogo.columns:
        df = df.merge(df_catalogo[["id_producto", "nombre"]], on="id_producto", how="left")
        df["nombre"] = df["nombre"].fillna(df["id_producto"].apply(lambda x: f"Producto {x}"))
    else:
        df["nombre"] = df["id_producto"].apply(lambda x: f"Producto {x}")

    resultado = []
    for _, row in df.head(limite).iterrows():
        dias = float(row["dias_restantes"])
        severidad = "critica" if dias <= 2 else "alta"
        resultado.append(
            {
                "id_producto": int(row["id_producto"]),
                "nombre": str(row["nombre"]),
                "stock": int(round(float(row["stock_actual"]))),
                "venta_diaria": round(float(row["velocidad_diaria"]), 2),
                "dias_restantes": dias,
                "severidad": severidad,
            }
        )
    return resultado
