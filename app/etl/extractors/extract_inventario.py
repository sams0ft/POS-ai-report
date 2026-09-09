"""Extractor de inventario por sucursal (snapshot actual)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractInventario(BaseExtractor):
    """Extrae el snapshot actual del inventario.

    Sin filtro de fecha — representa el estado actual del stock.
    Para historial usar movimiento_inventario_producto.

    La tabla `inventario` ya no existe. El esquema actual parte el inventario
    en dos tablas:
        * `saldo_inventario_producto_sucursal_base` — stock por
          (empresa, producto, sucursal), en UNIDAD BASE del producto.
        * `lote_inventario_producto` — lotes, y es donde vive
          `fecha_vencimiento`.

    Un producto es perecedero si tiene algún lote activo con
    `fecha_vencimiento IS NOT NULL`. Se toma el vencimiento MÁS PRÓXIMO
    (FEFO) entre los lotes con existencias.
    """

    def __init__(self, pos_db: AsyncSession, empresa_id: int) -> None:
        super().__init__(pos_db, empresa_id)

    async def extract(self) -> list[dict]:
        """Extrae el saldo de inventario por producto y sucursal.

        Returns:
            Lista de dicts con id_inventario, id_producto, id_sucursal,
            stock_actual, stock_reservado, fecha_vencimiento (None si no
            aplica) y ultima_actualizacion. `stock_actual` viene en unidad
            base del producto.
        """
        return await self._execute(
            """
            WITH saldo AS (
                SELECT
                    s.id_saldo_inventario_producto_base AS id_inventario,
                    s.id_producto,
                    s.id_sucursal,
                    s.stock_base_disponible             AS stock_actual,
                    s.stock_base_reservado              AS stock_reservado,
                    s.actualizado_en                    AS ultima_actualizacion
                FROM system_pos.saldo_inventario_producto_sucursal_base s
                WHERE s.id_empresa = :empresa_id
            ),
            vencimiento AS (
                SELECT
                    l.id_producto,
                    l.id_sucursal,
                    MIN(l.fecha_vencimiento) AS fecha_vencimiento
                FROM system_pos.lote_inventario_producto l
                WHERE l.id_empresa                = :empresa_id
                  AND l.estado                    = 'activo'
                  AND l.cantidad_base_disponible  > 0
                  AND l.fecha_vencimiento IS NOT NULL
                GROUP BY l.id_producto, l.id_sucursal
            )
            SELECT
                s.id_inventario,
                s.id_producto,
                s.id_sucursal,
                s.stock_actual,
                s.stock_reservado,
                v.fecha_vencimiento,
                s.ultima_actualizacion
            FROM saldo s
            LEFT JOIN vencimiento v
                   ON v.id_producto = s.id_producto
                  AND v.id_sucursal = s.id_sucursal
            """,
            {"empresa_id": self.empresa_id},
        )
