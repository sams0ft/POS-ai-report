"""Extractor de movimientos de inventario (últimos 30 días)."""

from datetime import timedelta

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractMovimientos(BaseExtractor):
    """Extrae movimientos de inventario de los últimos 30 días desde fecha_hasta.

    La ventana fija de 30 días es suficiente para analizar rotación reciente.
    """

    async def extract(self) -> list[dict]:
        """Extrae movimientos de inventario de los últimos 30 días.

        Returns:
            Lista de dicts con id_movimiento, id_producto, id_sucursal,
            tipo_movimiento, cantidad, fecha_movimiento, es_automatico.
        """
        return await self._execute(
            """
            SELECT
                m.id_movimiento,
                m.id_producto,
                m.id_sucursal,
                m.tipo_movimiento,
                m.cantidad,
                m.cantidad_anterior,
                m.cantidad_nueva,
                m.fecha_movimiento,
                m.es_automatico
            FROM system_pos.movimiento_inventario m
            WHERE m.id_empresa = :empresa_id
              AND m.fecha_movimiento::date BETWEEN :fecha_inicio AND :fecha_hasta
            ORDER BY m.id_producto, m.fecha_movimiento
            """,
            {
                "empresa_id": self.empresa_id,
                "fecha_inicio": self.fecha_hasta - timedelta(days=30),
                "fecha_hasta": self.fecha_hasta,
            },
        )
