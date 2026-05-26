"""Analytics: productos perecederos en riesgo de vencimiento."""

from __future__ import annotations

from datetime import date

import pandas as pd


def calcular_perecederos_riesgo(
    df_inventario: pd.DataFrame,
    df_velocidad: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    fecha_referencia: date,
    dias_max: int = 14,
    limite: int = 10,
) -> list[dict]:
    """Identifica productos perecederos con riesgo de perdida por vencimiento.

    Solo incluye productos con fecha_vencimiento IS NOT NULL, dias restantes <= dias_max,
    y unidades_en_riesgo > 0.

    Args:
        df_inventario: Inventario con fecha_vencimiento y stock_actual.
        df_velocidad: DataFrame con id_producto y velocidad_diaria.
        df_catalogo: Productos con precio_compra y nombre.
        fecha_referencia: Fecha de referencia para calcular dias restantes.
        dias_max: Umbral maximo de dias para incluir.
        limite: Maximo de registros a retornar.

    Returns:
        Lista de dicts con estructura del payload perecederos_riesgo.
    """
    if df_inventario.empty:
        return []

    df_inv = df_inventario.copy()
    df_inv = df_inv[df_inv["fecha_vencimiento"].notna()].copy()

    if df_inv.empty:
        return []

    df_inv["fecha_vencimiento"] = pd.to_datetime(df_inv["fecha_vencimiento"])
    df_inv["stock_actual"] = pd.to_numeric(df_inv["stock_actual"], errors="coerce").fillna(0)
    df_inv["dias_restantes"] = (
        df_inv["fecha_vencimiento"] - pd.Timestamp(fecha_referencia)
    ).dt.days

    df_inv = df_inv[df_inv["dias_restantes"] <= dias_max]
    df_inv = df_inv[df_inv["stock_actual"] > 0]

    if df_inv.empty:
        return []

    # Agrupar por producto (puede haber multiples entradas por sucursal)
    agg = (
        df_inv.groupby("id_producto")
        .agg(
            stock=("stock_actual", "sum"),
            fecha_vencimiento=("fecha_vencimiento", "min"),
            dias_restantes=("dias_restantes", "min"),
        )
        .reset_index()
    )

    if not df_velocidad.empty and "id_producto" in df_velocidad.columns:
        agg = agg.merge(df_velocidad[["id_producto", "velocidad_diaria"]], on="id_producto", how="left")
    else:
        agg["velocidad_diaria"] = 0.0
    agg["velocidad_diaria"] = agg["velocidad_diaria"].fillna(0)

    if not df_catalogo.empty and "id_producto" in df_catalogo.columns:
        cols_cat = [c for c in ["id_producto", "nombre", "precio_compra"] if c in df_catalogo.columns]
        agg = agg.merge(df_catalogo[cols_cat], on="id_producto", how="left")
    agg["nombre"] = agg.get("nombre", pd.Series(dtype=str)).fillna(
        agg["id_producto"].apply(lambda x: f"Producto {x}")
    )
    agg["precio_compra"] = pd.to_numeric(agg.get("precio_compra", 0), errors="coerce").fillna(0)

    agg["unidades_vendibles_proyectadas"] = (
        agg["velocidad_diaria"] * agg["dias_restantes"].clip(lower=0)
    ).round(1)
    agg["unidades_en_riesgo"] = (agg["stock"] - agg["unidades_vendibles_proyectadas"]).clip(lower=0).round(1)
    agg["perdida_estimada"] = (agg["unidades_en_riesgo"] * agg["precio_compra"]).round(0)

    agg = agg[agg["unidades_en_riesgo"] > 0].sort_values("dias_restantes")

    resultado = []
    for _, row in agg.head(limite).iterrows():
        resultado.append(
            {
                "id_producto": int(row["id_producto"]),
                "nombre": str(row["nombre"]),
                "stock": int(round(float(row["stock"]))),
                "fecha_vencimiento": row["fecha_vencimiento"].strftime("%Y-%m-%d"),
                "dias_restantes": int(row["dias_restantes"]),
                "velocidad_diaria": round(float(row["velocidad_diaria"]), 2),
                "unidades_vendibles_proyectadas": float(row["unidades_vendibles_proyectadas"]),
                "unidades_en_riesgo": float(row["unidades_en_riesgo"]),
                "perdida_estimada": int(round(float(row["perdida_estimada"]))),
            }
        )
    return resultado
