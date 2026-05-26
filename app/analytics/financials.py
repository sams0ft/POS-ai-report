"""Analytics: resumen ejecutivo financiero, márgenes y variaciones."""

from __future__ import annotations

import pandas as pd

from app.analytics.trends import clasificar_tendencia


def calcular_resumen_ejecutivo(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_gastos: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    df_gastos_anterior: pd.DataFrame,
) -> dict:
    """Calcula el resumen ejecutivo financiero del período.

    Args:
        df_ventas: Líneas de detalle_venta del período actual (una fila por línea).
        df_catalogo: Productos del catálogo con precio_compra.
        df_gastos: Gastos operativos del período actual.
        df_ventas_anterior: Líneas de detalle_venta del período de comparación.
        df_gastos_anterior: Gastos del período de comparación.

    Returns:
        Dict con la forma exacta del bloque resumen_ejecutivo del payload.
    """
    # --- Período actual ---
    if df_ventas.empty:
        total_ingresos = 0
        cantidad_ventas = 0
        impuestos_pagados = 0
        cantidad_unidades = 0
    else:
        df_cab = df_ventas.drop_duplicates(subset=["id_venta"])
        total_ingresos = int(round(float(df_cab["total"].sum())))
        cantidad_ventas = int(df_cab["id_venta"].nunique())
        impuestos_pagados = int(round(float(df_cab["impuesto"].sum())))
        cantidad_unidades = int(round(float(df_ventas["cantidad"].sum())))

    gastos_operativos = 0
    if not df_gastos.empty and "monto" in df_gastos.columns:
        gastos_operativos = int(round(float(df_gastos["monto"].sum())))

    # Costo mercancía vendida = sum(cantidad × precio_compra del producto)
    costo_mercancia = _calcular_costo_mercancia(df_ventas, df_catalogo)

    total_egresos = gastos_operativos + costo_mercancia
    utilidad_bruta = total_ingresos - costo_mercancia
    utilidad_neta = utilidad_bruta - gastos_operativos - impuestos_pagados

    margen_bruto_pct = (
        round(utilidad_bruta / total_ingresos * 100, 2) if total_ingresos > 0 else 0.0
    )
    margen_neto_pct = (
        round(utilidad_neta / total_ingresos * 100, 2) if total_ingresos > 0 else 0.0
    )

    ticket_promedio = int(round(total_ingresos / cantidad_ventas)) if cantidad_ventas > 0 else 0
    items_por_ticket = (
        round(cantidad_unidades / cantidad_ventas, 2) if cantidad_ventas > 0 else 0.0
    )

    # --- Período anterior (comparación) ---
    variacion = _calcular_variacion(
        total_ingresos,
        cantidad_ventas,
        ticket_promedio,
        margen_bruto_pct,
        df_ventas_anterior,
        df_catalogo,
        df_gastos_anterior,
    )

    return {
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "utilidad_bruta": utilidad_bruta,
        "utilidad_neta": utilidad_neta,
        "margen_bruto_pct": margen_bruto_pct,
        "margen_neto_pct": margen_neto_pct,
        "impuestos_pagados": impuestos_pagados,
        "gastos_operativos": gastos_operativos,
        "costo_mercancia_vendida": costo_mercancia,
        "cantidad_ventas": cantidad_ventas,
        "cantidad_unidades_vendidas": cantidad_unidades,
        "ticket_promedio": ticket_promedio,
        "items_por_ticket": items_por_ticket,
        "variacion_vs_mes_anterior": variacion,
    }


def _calcular_costo_mercancia(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
) -> int:
    """Calcula el costo de mercancía vendida cruzando ventas con precio_compra.

    Args:
        df_ventas: Líneas de ventas con id_producto y cantidad.
        df_catalogo: Productos con id_producto y precio_compra.

    Returns:
        Costo total en COP (int redondeado).
    """
    if df_ventas.empty or df_catalogo.empty:
        return 0

    cols_precio = {"id_producto", "precio_compra"}
    if not cols_precio.issubset(df_catalogo.columns):
        return 0

    df_precio = df_catalogo[["id_producto", "precio_compra"]].copy()
    df_precio["precio_compra"] = pd.to_numeric(df_precio["precio_compra"], errors="coerce").fillna(0)

    df_costo = df_ventas[["id_producto", "cantidad"]].copy()
    df_costo["cantidad"] = pd.to_numeric(df_costo["cantidad"], errors="coerce").fillna(0)
    df_costo = df_costo.merge(df_precio, on="id_producto", how="left")
    df_costo["precio_compra"] = df_costo["precio_compra"].fillna(0)
    df_costo["costo_linea"] = df_costo["cantidad"] * df_costo["precio_compra"]

    return int(round(float(df_costo["costo_linea"].sum())))


def _calcular_variacion(
    ingresos_actual: int,
    ventas_actual: int,
    ticket_actual: int,
    margen_actual: float,
    df_ventas_ant: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_gastos_ant: pd.DataFrame,
) -> dict:
    """Calcula variaciones porcentuales vs período anterior.

    Args:
        ingresos_actual: Total de ingresos del período actual.
        ventas_actual: Cantidad de transacciones del período actual.
        ticket_actual: Ticket promedio del período actual.
        margen_actual: Margen bruto % del período actual.
        df_ventas_ant: Ventas del período de comparación.
        df_catalogo: Catálogo de productos.
        df_gastos_ant: Gastos del período de comparación.

    Returns:
        Dict con ingresos_pct, ventas_pct, ticket_promedio_pct, margen_pct_delta.
    """
    if df_ventas_ant.empty:
        return {
            "ingresos_pct": 0.0,
            "ventas_pct": 0.0,
            "ticket_promedio_pct": 0.0,
            "margen_pct_delta": 0.0,
        }

    df_cab_ant = df_ventas_ant.drop_duplicates(subset=["id_venta"])
    ingresos_ant = float(df_cab_ant["total"].sum())
    ventas_ant = int(df_cab_ant["id_venta"].nunique())
    ticket_ant = int(round(ingresos_ant / ventas_ant)) if ventas_ant > 0 else 0

    costo_ant = _calcular_costo_mercancia(df_ventas_ant, df_catalogo)
    margen_ant = (
        round((ingresos_ant - costo_ant) / ingresos_ant * 100, 2)
        if ingresos_ant > 0
        else 0.0
    )

    def _pct(actual: float, anterior: float) -> float:
        if anterior == 0:
            return 0.0
        return round((actual - anterior) / anterior * 100, 2)

    return {
        "ingresos_pct": _pct(ingresos_actual, ingresos_ant),
        "ventas_pct": _pct(ventas_actual, ventas_ant),
        "ticket_promedio_pct": _pct(ticket_actual, ticket_ant),
        "margen_pct_delta": round(margen_actual - margen_ant, 2),
    }
