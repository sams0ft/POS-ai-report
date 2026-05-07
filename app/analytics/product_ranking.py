"""Motor analítico: ranking de productos (Top 5 / Bottom 5)."""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def calcular_ranking_productos(
    pos_db: AsyncSession,
    empresa_id: int,
    fecha_desde: str,
    fecha_hasta: str,
) -> dict:
    """Calcula el ranking de productos por ventas y margen.

    Args:
        pos_db: Sesión read-only a la DB del POS.
        empresa_id: ID de la empresa.
        fecha_desde: Fecha inicio del período (YYYY-MM-DD).
        fecha_hasta: Fecha fin del período (YYYY-MM-DD).

    Returns:
        Dict con top_5, bottom_5, y métricas por producto.
    """
    query = text("""
        SELECT
            p.id AS producto_id,
            p.nombre,
            c.nombre AS categoria,
            SUM(dv.cantidad) AS total_vendido,
            SUM(dv.subtotal) AS ingresos,
            AVG(p.precio_venta) AS precio_venta_promedio,
            AVG(p.precio_compra) AS precio_compra_promedio,
            CASE
                WHEN AVG(p.precio_venta) > 0
                THEN ((AVG(p.precio_venta) - AVG(p.precio_compra)) / AVG(p.precio_venta)) * 100
                ELSE 0
            END AS margen_porcentaje
        FROM detalle_venta dv
        JOIN productos p ON dv.id_producto = p.id
        LEFT JOIN categorias c ON p.id_categoria = c.id
        JOIN ventas v ON dv.id_venta = v.id
        WHERE v.id_empresa = :empresa_id
          AND v.fecha_venta BETWEEN :fecha_desde AND :fecha_hasta
          AND v.estado = 'completada'
        GROUP BY p.id, p.nombre, c.nombre
        ORDER BY total_vendido DESC
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
        return {"top_5": [], "bottom_5": [], "total_productos": 0}

    df = pd.DataFrame(rows)

    # TODO: calcular tendencia comparando con período anterior
    # TODO: agregar análisis de estacionalidad

    top_5 = df.head(5).to_dict(orient="records")
    bottom_5 = df.tail(5).to_dict(orient="records")

    return {
        "top_5": top_5,
        "bottom_5": bottom_5,
        "total_productos": len(df),
        "ingreso_total": float(df["ingresos"].sum()),
        "margen_promedio": float(df["margen_porcentaje"].mean()),
    }
