"""Analytics: serie diaria de ventas, métodos de pago, sucursales y proveedores."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def calcular_serie_diaria(
    df_ventas: pd.DataFrame,
    fecha_desde: date,
    fecha_hasta: date,
    top_n: int = 5,
) -> dict:
    """Retorna los N días con más ingresos del rango, ordenados por fecha.

    Args:
        df_ventas: Líneas de detalle_venta del período (una fila por línea).
        fecha_desde: Primer día del rango.
        fecha_hasta: Último día del rango.
        top_n: Cuántos días top incluir (default 5).

    Returns:
        Dict con claves fechas, ingresos, transacciones, unidades (arrays paralelos).
    """
    if df_ventas.empty:
        return {"fechas": [], "ingresos": [], "transacciones": [], "unidades": []}

    df = df_ventas.copy()
    df["fecha_venta"] = pd.to_datetime(df["fecha_venta"])
    df["fecha_dia"] = df["fecha_venta"].dt.strftime("%Y-%m-%d")
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0)
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)

    df_cab = df.drop_duplicates(subset=["id_venta"]).copy()
    por_dia_ingresos = (
        df_cab.groupby("fecha_dia")
        .agg(ingresos=("total", "sum"), transacciones=("id_venta", "count"))
        .reset_index()
    )
    por_dia_unidades = (
        df.groupby("fecha_dia")["cantidad"].sum().reset_index(name="unidades")
    )

    df_serie = por_dia_ingresos.merge(por_dia_unidades, on="fecha_dia", how="left")
    df_serie = df_serie.fillna(0)

    df_top = (
        df_serie.nlargest(top_n, "ingresos")
        .sort_values("fecha_dia")
        .reset_index(drop=True)
    )

    return {
        "fechas": df_top["fecha_dia"].tolist(),
        "ingresos": [int(round(x)) for x in df_top["ingresos"]],
        "transacciones": [int(x) for x in df_top["transacciones"]],
        "unidades": [int(round(x)) for x in df_top["unidades"]],
    }


def calcular_metodos_pago(df_ventas: pd.DataFrame) -> list[dict]:
    """Agrega ventas por método de pago.

    Args:
        df_ventas: Líneas de detalle_venta con id_metodo_pago y metodo_pago_nombre.

    Returns:
        Lista de dicts con id, nombre, monto, transacciones, pct. Ordenada por monto desc.
    """
    if df_ventas.empty:
        return []

    df_cab = df_ventas.drop_duplicates(subset=["id_venta"]).copy()
    df_cab["total"] = pd.to_numeric(df_cab["total"], errors="coerce").fillna(0)

    agg = (
        df_cab.groupby(["id_metodo_pago", "metodo_pago_nombre"])
        .agg(monto=("total", "sum"), transacciones=("id_venta", "count"))
        .reset_index()
    )
    total_global = float(agg["monto"].sum())

    resultado = []
    for _, row in agg.sort_values("monto", ascending=False).iterrows():
        monto = float(row["monto"])
        pct = round(monto / total_global * 100, 2) if total_global > 0 else 0.0
        resultado.append(
            {
                "id": int(row["id_metodo_pago"]),
                "nombre": str(row["metodo_pago_nombre"]),
                "monto": int(round(monto)),
                "transacciones": int(row["transacciones"]),
                "pct": pct,
            }
        )
    return resultado


def calcular_por_sucursal(
    df_ventas: pd.DataFrame,
    df_sucursales: pd.DataFrame,
) -> list[dict]:
    """Agrega ventas por sucursal con nombre.

    Args:
        df_ventas: Líneas de detalle_venta con id_sucursal y total.
        df_sucursales: Catálogo de sucursales con id_sucursal y nombre.

    Returns:
        Lista de dicts con id, nombre, ingresos, transacciones, ticket_promedio, pct_total.
    """
    if df_ventas.empty:
        return []

    df_cab = df_ventas.drop_duplicates(subset=["id_venta"]).copy()
    df_cab["total"] = pd.to_numeric(df_cab["total"], errors="coerce").fillna(0)

    agg = (
        df_cab.groupby("id_sucursal")
        .agg(ingresos=("total", "sum"), transacciones=("id_venta", "count"))
        .reset_index()
    )
    total_global = float(agg["ingresos"].sum())

    if not df_sucursales.empty and "id_sucursal" in df_sucursales.columns:
        agg = agg.merge(
            df_sucursales[["id_sucursal", "nombre"]],
            on="id_sucursal",
            how="left",
        )
    else:
        agg["nombre"] = agg["id_sucursal"].apply(lambda x: f"Sucursal {x}")

    agg["nombre"] = agg["nombre"].fillna(agg["id_sucursal"].apply(lambda x: f"Sucursal {x}"))

    resultado = []
    for _, row in agg.sort_values("ingresos", ascending=False).iterrows():
        ingresos = float(row["ingresos"])
        txns = int(row["transacciones"])
        ticket = int(round(ingresos / txns)) if txns > 0 else 0
        pct = round(ingresos / total_global * 100, 2) if total_global > 0 else 0.0
        resultado.append(
            {
                "id": int(row["id_sucursal"]),
                "nombre": str(row["nombre"]),
                "ingresos": int(round(ingresos)),
                "transacciones": txns,
                "ticket_promedio": ticket,
                "pct_total": pct,
            }
        )
    return resultado


def calcular_proveedores_top(
    df_compras: pd.DataFrame,
    df_proveedores: pd.DataFrame,
    top_n: int = 5,
) -> list[dict]:
    """Calcula top N proveedores por monto de compras en el período.

    Args:
        df_compras: Líneas de detalle_compra del período.
        df_proveedores: Catálogo de proveedores con razon_social.
        top_n: Cuántos proveedores retornar.

    Returns:
        Lista de dicts con id, razon_social, compras_periodo, productos_suministrados,
        lead_time_dias_prom, pct_compras_total.
    """
    if df_compras.empty:
        return []

    df = df_compras.copy()
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0)

    df_cab = df.drop_duplicates(subset=["id_compra"])
    agg_monto = (
        df_cab.groupby("id_proveedor")
        .agg(monto=("total", "sum"), compras_periodo=("id_compra", "count"))
        .reset_index()
    )

    agg_prods = (
        df.groupby("id_proveedor")["id_producto"]
        .nunique()
        .reset_index(name="productos_suministrados")
    )

    agg = agg_monto.merge(agg_prods, on="id_proveedor", how="left")
    agg["productos_suministrados"] = agg["productos_suministrados"].fillna(0).astype(int)
    total_global = float(agg["monto"].sum())

    if not df_proveedores.empty and "id_proveedor" in df_proveedores.columns:
        agg = agg.merge(
            df_proveedores[["id_proveedor", "razon_social"]],
            on="id_proveedor",
            how="left",
        )
    else:
        agg["razon_social"] = agg["id_proveedor"].apply(lambda x: f"Proveedor {x}")

    agg["razon_social"] = agg["razon_social"].fillna(
        agg["id_proveedor"].apply(lambda x: f"Proveedor {x}")
    )

    resultado = []
    for _, row in agg.sort_values("monto", ascending=False).head(top_n).iterrows():
        monto = float(row["monto"])
        pct = round(monto / total_global * 100, 2) if total_global > 0 else 0.0
        resultado.append(
            {
                "id": int(row["id_proveedor"]),
                "razon_social": str(row["razon_social"]),
                "compras_periodo": int(row["compras_periodo"]),
                "productos_suministrados": int(row["productos_suministrados"]),
                "lead_time_dias_prom": 0.0,
                "pct_compras_total": pct,
            }
        )
    return resultado
