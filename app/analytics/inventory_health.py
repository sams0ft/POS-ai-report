"""Analytics: indicadores de salud global del inventario."""

from __future__ import annotations

import pandas as pd


def calcular_inventario_salud(
    df_inventario: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_ventas: pd.DataFrame,
    df_bottom: list[dict],
    dias_periodo: int,
) -> dict:
    """Calcula los indicadores de salud global del inventario.

    Args:
        df_inventario: Inventario actual con stock_actual por producto/sucursal.
        df_catalogo: Productos con precio_compra y stock_minimo.
        df_ventas: Ventas del periodo (para calcular costo mercancia vendida).
        df_bottom: Lista de productos bottom ya calculados (para inmovilizado).
        dias_periodo: Dias del periodo del reporte.

    Returns:
        Dict con estructura del payload inventario_salud.
    """
    vacio = {
        "valor_total_inventario": 0,
        "productos_total": 0,
        "productos_bajo_stock_minimo": 0,
        "productos_sin_stock": 0,
        "productos_sobrestock": 0,
        "rotacion_promedio": 0.0,
        "dias_inventario_promedio": 0.0,
        "valor_inmovilizado_estancados": 0,
        "pct_inmovilizado": 0.0,
    }

    if df_inventario.empty or df_catalogo.empty:
        return vacio

    df_inv = df_inventario.copy()
    df_inv["stock_actual"] = pd.to_numeric(df_inv["stock_actual"], errors="coerce").fillna(0)
    stock_agg = df_inv.groupby("id_producto")["stock_actual"].sum().reset_index()

    cols_cat = [c for c in ["id_producto", "precio_compra", "stock_minimo"] if c in df_catalogo.columns]
    df = stock_agg.merge(df_catalogo[cols_cat], on="id_producto", how="left")
    df["precio_compra"] = pd.to_numeric(df.get("precio_compra", 0), errors="coerce").fillna(0)
    df["stock_minimo"] = pd.to_numeric(df.get("stock_minimo", 0), errors="coerce").fillna(0)

    valor_total = int(round(float((df["stock_actual"] * df["precio_compra"]).sum())))
    productos_total = len(df)
    sin_stock = int((df["stock_actual"] <= 0).sum())
    bajo_minimo = int(((df["stock_actual"] > 0) & (df["stock_actual"] < df["stock_minimo"])).sum())

    costo_mercancia = 0.0
    if not df_ventas.empty and not df_catalogo.empty and "precio_compra" in df_catalogo.columns:
        df_v = df_ventas.copy()
        df_v["cantidad"] = pd.to_numeric(df_v["cantidad"], errors="coerce").fillna(0)
        df_v = df_v.merge(df_catalogo[["id_producto", "precio_compra"]], on="id_producto", how="left")
        df_v["precio_compra"] = pd.to_numeric(df_v["precio_compra"], errors="coerce").fillna(0)
        costo_mercancia = float((df_v["cantidad"] * df_v["precio_compra"]).sum())

    costo_diario = costo_mercancia / dias_periodo if dias_periodo > 0 else 0
    dias_inventario = round(valor_total / costo_diario, 1) if costo_diario > 0 else 0.0

    sobrestock = 0
    if costo_diario > 0 and len(df) > 0:
        df = df.copy()
        df["valor_producto"] = df["stock_actual"] * df["precio_compra"]
        costo_per_producto = costo_diario / len(df) if len(df) > 0 else 1
        df["dias_cob_aprox"] = df["valor_producto"] / costo_per_producto
        sobrestock = int((df["dias_cob_aprox"] > 90).sum())

    valor_inmovilizado = sum(p.get("valor_inventario_inmovilizado", 0) for p in df_bottom)
    pct_inmovilizado = round(valor_inmovilizado / valor_total * 100, 2) if valor_total > 0 else 0.0

    unidades_vendidas = 0.0
    if not df_ventas.empty and "cantidad" in df_ventas.columns:
        unidades_vendidas = float(pd.to_numeric(df_ventas["cantidad"], errors="coerce").fillna(0).sum())
    stock_promedio = float(stock_agg["stock_actual"].mean()) if not stock_agg.empty else 0
    rotacion = round(unidades_vendidas / stock_promedio, 2) if stock_promedio > 0 else 0.0

    return {
        "valor_total_inventario": valor_total,
        "productos_total": productos_total,
        "productos_bajo_stock_minimo": bajo_minimo,
        "productos_sin_stock": sin_stock,
        "productos_sobrestock": sobrestock,
        "rotacion_promedio": rotacion,
        "dias_inventario_promedio": dias_inventario,
        "valor_inmovilizado_estancados": int(round(valor_inmovilizado)),
        "pct_inmovilizado": pct_inmovilizado,
    }
