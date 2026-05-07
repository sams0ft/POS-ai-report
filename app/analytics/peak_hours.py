"""Motor analítico: horas mágicas (patrones de venta por hora/día)."""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def calcular_horas_magicas(
    pos_db: AsyncSession,
    empresa_id: int,
    fecha_desde: str,
    fecha_hasta: str,
) -> dict:
    """Analiza patrones de venta por hora del día y día de la semana.

    Returns:
        Dict con horas pico, horas valle, y matriz completa hora×día.
    """
    query = text("""
        SELECT
            EXTRACT(HOUR FROM v.fecha_venta) AS hora,
            EXTRACT(DOW FROM v.fecha_venta) AS dia_semana,
            COUNT(*) AS total_transacciones,
            SUM(v.monto_total) AS monto_total,
            AVG(v.monto_total) AS ticket_promedio
        FROM ventas v
        WHERE v.id_empresa = :empresa_id
          AND v.fecha_venta BETWEEN :fecha_desde AND :fecha_hasta
          AND v.estado = 'completada'
        GROUP BY hora, dia_semana
        ORDER BY hora, dia_semana
    """)

    result = await pos_db.execute(
        query,
        {
            "empresa_id": empresa_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    )
    rows = result.mappings().all()

    if not rows:
        return {"horas_pico": [], "horas_valle": [], "matriz": []}

    df = pd.DataFrame(rows)

    # Agregar por hora (independiente del día)
    por_hora = df.groupby("hora").agg(
        total_transacciones=("total_transacciones", "sum"),
        monto_total=("monto_total", "sum"),
        ticket_promedio=("ticket_promedio", "mean"),
    ).reset_index()

    por_hora = por_hora.sort_values("total_transacciones", ascending=False)

    horas_pico = por_hora.head(3).to_dict(orient="records")
    horas_valle = por_hora.tail(3).to_dict(orient="records")

    # Agregar por día de la semana
    por_dia = df.groupby("dia_semana").agg(
        total_transacciones=("total_transacciones", "sum"),
        monto_total=("monto_total", "sum"),
    ).reset_index()

    return {
        "horas_pico": horas_pico,
        "horas_valle": horas_valle,
        "por_dia": por_dia.to_dict(orient="records"),
        "matriz_completa": df.to_dict(orient="records"),
    }
