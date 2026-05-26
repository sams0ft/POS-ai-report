"""Analytics: resumen de clientes (nuevos vs recurrentes)."""

from __future__ import annotations

import pandas as pd


def calcular_clientes_resumen(
    df_ventas: pd.DataFrame,
    df_ventas_historico_cliente: pd.DataFrame,
) -> dict:
    """Calcula metricas de clientes del periodo.

    Args:
        df_ventas: Lineas de detalle_venta del periodo actual.
        df_ventas_historico_cliente: DataFrame con id_cliente y primera_venta (date)
            de toda la historia del negocio.

    Returns:
        Dict con total_clientes_activos, clientes_nuevos_periodo,
        ticket_promedio_cliente_recurrente, ticket_promedio_cliente_nuevo,
        pct_ventas_clientes_identificados.
    """
    vacio = {
        "total_clientes_activos": 0,
        "clientes_nuevos_periodo": 0,
        "ticket_promedio_cliente_recurrente": 0,
        "ticket_promedio_cliente_nuevo": 0,
        "pct_ventas_clientes_identificados": 0.0,
    }

    if df_ventas.empty:
        return vacio

    df_cab = df_ventas.drop_duplicates(subset=["id_venta"]).copy()
    df_cab["total"] = pd.to_numeric(df_cab["total"], errors="coerce").fillna(0)

    con_cliente = df_cab[df_cab["id_cliente"].notna() & (df_cab["id_cliente"] != 0)]
    pct_identificados = round(len(con_cliente) / len(df_cab) * 100, 2) if len(df_cab) > 0 else 0.0

    if con_cliente.empty:
        return {
            "total_clientes_activos": 0,
            "clientes_nuevos_periodo": 0,
            "ticket_promedio_cliente_recurrente": 0,
            "ticket_promedio_cliente_nuevo": 0,
            "pct_ventas_clientes_identificados": pct_identificados,
        }

    total_clientes = int(con_cliente["id_cliente"].nunique())
    compras_por_cliente = con_cliente.groupby("id_cliente")["id_venta"].count()
    clientes_recurrentes = compras_por_cliente[compras_por_cliente >= 2].index

    clientes_nuevos_ids: set = set()
    if not df_ventas_historico_cliente.empty and "id_cliente" in df_ventas_historico_cliente.columns:
        df_hist = df_ventas_historico_cliente.copy()
        df_hist["primera_venta"] = pd.to_datetime(df_hist["primera_venta"])
        df_cab2 = df_ventas.drop_duplicates("id_venta")[["id_venta", "fecha_venta", "id_cliente"]].copy()
        df_cab2["fecha_venta"] = pd.to_datetime(df_cab2["fecha_venta"])
        fecha_desde_periodo = df_cab2["fecha_venta"].min()
        fecha_hasta_periodo = df_cab2["fecha_venta"].max()
        nuevos_mask = (
            (df_hist["primera_venta"] >= fecha_desde_periodo) &
            (df_hist["primera_venta"] <= fecha_hasta_periodo)
        )
        clientes_nuevos_ids = set(df_hist[nuevos_mask]["id_cliente"].tolist())

    clientes_nuevos = len(clientes_nuevos_ids)

    ticket_rec = 0
    if len(clientes_recurrentes) > 0:
        ventas_rec = con_cliente[con_cliente["id_cliente"].isin(clientes_recurrentes)]
        val = ventas_rec.groupby("id_cliente")["total"].sum().mean()
        ticket_rec = int(round(float(val))) if not pd.isna(val) else 0

    ticket_nvo = 0
    if clientes_nuevos_ids:
        ventas_nvo = con_cliente[con_cliente["id_cliente"].isin(clientes_nuevos_ids)]
        if not ventas_nvo.empty:
            val2 = ventas_nvo.groupby("id_cliente")["total"].sum().mean()
            ticket_nvo = int(round(float(val2))) if not pd.isna(val2) else 0

    return {
        "total_clientes_activos": total_clientes,
        "clientes_nuevos_periodo": clientes_nuevos,
        "ticket_promedio_cliente_recurrente": ticket_rec,
        "ticket_promedio_cliente_nuevo": ticket_nvo,
        "pct_ventas_clientes_identificados": pct_identificados,
    }
