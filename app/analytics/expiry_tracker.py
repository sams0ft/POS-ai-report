"""Motor analítico: anti-desperdicio (productos perecederos próximos a vencer)."""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def calcular_riesgo_desperdicio(
    pos_db: AsyncSession,
    empresa_id: int,
    fecha_referencia: str,
) -> dict:
    """Identifica productos perecederos en riesgo de vencer sin venderse.

    Args:
        pos_db: Sesión read-only a la DB del POS.
        empresa_id: ID de la empresa.
        fecha_referencia: Fecha actual o de referencia (YYYY-MM-DD).

    Returns:
        Dict con productos en riesgo crítico, vigilancia, y patrones.
    """
    # Productos perecederos con fecha de vencimiento próxima
    query_perecederos = text("""
        SELECT
            p.id AS producto_id,
            p.nombre,
            c.nombre AS categoria,
            i.stock_actual,
            p.fecha_vencimiento,
            (p.fecha_vencimiento - CAST(:fecha_referencia AS DATE)) AS dias_restantes,
            p.precio_venta,
            p.precio_compra
        FROM productos p
        JOIN inventario i ON p.id = i.id_producto
        LEFT JOIN categorias c ON p.id_categoria = c.id
        WHERE p.id_empresa = :empresa_id
          AND p.es_perecedero = true
          AND p.fecha_vencimiento IS NOT NULL
          AND p.fecha_vencimiento > CAST(:fecha_referencia AS DATE)
          AND i.stock_actual > 0
        ORDER BY p.fecha_vencimiento ASC
    """)

    # Velocidad de venta promedio por producto (últimos 30 días)
    query_velocidad = text("""
        SELECT
            dv.id_producto AS producto_id,
            SUM(dv.cantidad) / 30.0 AS venta_diaria_promedio
        FROM detalle_venta dv
        JOIN ventas v ON dv.id_venta = v.id
        WHERE v.id_empresa = :empresa_id
          AND v.fecha_venta >= (CAST(:fecha_referencia AS DATE) - INTERVAL '30 days')
          AND v.estado = 'completada'
        GROUP BY dv.id_producto
    """)

    result_p = await pos_db.execute(
        query_perecederos,
        {"empresa_id": empresa_id, "fecha_referencia": fecha_referencia},
    )
    result_v = await pos_db.execute(
        query_velocidad,
        {"empresa_id": empresa_id, "fecha_referencia": fecha_referencia},
    )

    perecederos = pd.DataFrame(result_p.mappings().all())
    velocidad = pd.DataFrame(result_v.mappings().all())

    if perecederos.empty:
        return {"riesgo_critico": [], "vigilancia": [], "perdida_estimada": 0}

    # Merge velocidad de venta
    df = perecederos.merge(velocidad, on="producto_id", how="left")
    df["venta_diaria_promedio"] = df["venta_diaria_promedio"].fillna(0)

    # Calcular unidades en riesgo
    df["unidades_vendibles"] = df["venta_diaria_promedio"] * df["dias_restantes"]
    df["unidades_en_riesgo"] = (df["stock_actual"] - df["unidades_vendibles"]).clip(lower=0)
    df["perdida_estimada"] = df["unidades_en_riesgo"] * df["precio_compra"]

    # Clasificar por urgencia
    critico = df[df["dias_restantes"] <= 7].to_dict(orient="records")
    vigilancia = df[(df["dias_restantes"] > 7) & (df["dias_restantes"] <= 30)].to_dict(
        orient="records"
    )

    return {
        "riesgo_critico": critico,
        "vigilancia": vigilancia,
        "perdida_estimada_total": float(df["perdida_estimada"].sum()),
        "total_productos_en_riesgo": int((df["unidades_en_riesgo"] > 0).sum()),
    }
