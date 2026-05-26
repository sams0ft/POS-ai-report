"""Extractor de inventario por sucursal (snapshot actual)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractInventario(BaseExtractor):
    """Extrae el snapshot actual del inventario.

    Sin filtro de fecha — representa el estado actual del stock.
    Para historial usar movimiento_inventario.
    """

    def __init__(self, pos_db: AsyncSession, empresa_id: int) -> None:
        super().__init__(pos_db, empresa_id)

    async def extract(self) -> list[dict]:
        """Extrae todas las entradas de inventario de la empresa.

        Returns:
            Lista de dicts con id_producto, id_sucursal, stock_actual,
            stock_reservado, fecha_vencimiento (None si no aplica).
        """
        return await self._execute(
            """
            SELECT
                i.id_inventario,
                i.id_producto,
                i.id_sucursal,
                i.stock_actual,
                i.stock_reservado,
                i.fecha_vencimiento,
                i.ultima_actualizacion
            FROM system_pos.inventario i
            WHERE i.id_empresa = :empresa_id
            """,
            {"empresa_id": self.empresa_id},
        )
