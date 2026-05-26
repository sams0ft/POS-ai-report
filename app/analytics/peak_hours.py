"""Analytics: patrón horario de ventas (matriz hora × día de semana)."""

from __future__ import annotations

import pandas as pd


def calcular_patron_horario(df_ventas: pd.DataFrame) -> dict:
    """Calcula la matriz dispersa de ventas por hora y día de semana.

    Solo incluye celdas con actividad (omite hora×día con cero transacciones).
    Día de semana: 1=lunes, 7=domingo (ISO).

    Args:
        df_ventas: Líneas de detalle_venta con fecha_venta y total.
                   Una fila por línea; la cabecera de venta se deduplica internamente.

    Returns:
        Dict con:
            - matriz_hora_dia: list de {h, d, v (monto), t (transacciones)}
            - horas_pico: top 3 horas por ingresos
            - horas_valle: bottom 3 horas con actividad
            - dia_pico: día con más ingresos (1-7)
            - dia_valle: día con menos ingresos entre los días con actividad
            - concentracion_top3_horas_pct: % de ventas en las 3 horas con más ventas
    """
    vacio = {
        "matriz_hora_dia": [],
        "horas_pico": [],
        "horas_valle": [],
        "dia_pico": None,
        "dia_valle": None,
        "concentracion_top3_horas_pct": 0.0,
    }

    if df_ventas.empty:
        return vacio

    df_cab = df_ventas.drop_duplicates(subset=["id_venta"]).copy()
    df_cab["fecha_venta"] = pd.to_datetime(df_cab["fecha_venta"])

    # Zona horaria Colombia
    if df_cab["fecha_venta"].dt.tz is None:
        df_cab["fecha_local"] = df_cab["fecha_venta"].dt.tz_localize("UTC").dt.tz_convert(
            "America/Bogota"
        )
    else:
        df_cab["fecha_local"] = df_cab["fecha_venta"].dt.tz_convert("America/Bogota")

    df_cab["hora"] = df_cab["fecha_local"].dt.hour
    # dt.day_of_week: 0=lunes..6=domingo → +1 para ISO (1=lunes, 7=domingo)
    df_cab["dia_semana"] = df_cab["fecha_local"].dt.day_of_week + 1
    df_cab["total"] = pd.to_numeric(df_cab["total"], errors="coerce").fillna(0)

    # Matriz dispersa hora × día
    matriz_agg = (
        df_cab.groupby(["hora", "dia_semana"])
        .agg(v=("total", "sum"), t=("id_venta", "count"))
        .reset_index()
    )
    matriz_top = matriz_agg.nlargest(5, "v").sort_values(["hora", "dia_semana"])
    matriz_lista = [
        {
            "h": int(row["hora"]),
            "d": int(row["dia_semana"]),
            "v": int(round(float(row["v"]))),
            "t": int(row["t"]),
        }
        for _, row in matriz_top.iterrows()
    ]

    # Agrupar por hora (independiente de día)
    por_hora = (
        df_cab.groupby("hora")
        .agg(monto=("total", "sum"), txns=("id_venta", "count"))
        .reset_index()
    )
    por_hora = por_hora.sort_values("monto", ascending=False)

    horas_pico = [int(h) for h in por_hora.head(3)["hora"].tolist()]
    horas_activas = por_hora[por_hora["monto"] > 0]
    horas_valle = [int(h) for h in horas_activas.tail(3)["hora"].tolist()]

    # Concentración top 3 horas
    total_ventas = float(por_hora["monto"].sum())
    top3_monto = float(por_hora.head(3)["monto"].sum())
    concentracion = (
        round(top3_monto / total_ventas * 100, 2) if total_ventas > 0 else 0.0
    )

    # Agrupar por día
    por_dia = (
        df_cab.groupby("dia_semana")["total"]
        .sum()
        .reset_index(name="monto")
    )
    por_dia = por_dia[por_dia["monto"] > 0]

    dia_pico = None
    dia_valle = None
    if not por_dia.empty:
        dia_pico = int(por_dia.loc[por_dia["monto"].idxmax(), "dia_semana"])
        dia_valle = int(por_dia.loc[por_dia["monto"].idxmin(), "dia_semana"])

    return {
        "matriz_hora_dia": matriz_lista,
        "horas_pico": horas_pico,
        "horas_valle": horas_valle,
        "dia_pico": dia_pico,
        "dia_valle": dia_valle,
        "concentracion_top3_horas_pct": concentracion,
    }
