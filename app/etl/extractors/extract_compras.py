"""Extractor de compras (últimos 180 días) para calcular lead times."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractCompras(BaseExtractor):
    """Extrae compras de los últimos 180 días desde fecha_hasta.

    La ventana amplia (180 días) permite calcular lead times con suficiente
    historial, independientemente del rango del reporte.
    """

    def __init__(self, pos_db: AsyncSession, empresa_id: int, fecha_hasta: date) -> None:
        super().__init__(pos_db, empresa_id, fecha_hasta=fecha_hasta)

    async def extract(self) -> list[dict]:
        """Extrae compras + detalle de los últimos 180 días.

        Se excluyen únicamente las compras canceladas. `compra.estado` admite
        'pendiente', 'pagada', 'abonada' y 'cancelada' — el valor 'registrada'
        que se filtraba antes no es válido en el esquema, así que la query no
        devolvía nunca filas.

        Returns:
            Lista de dicts — una fila por línea de detalle_compra.
            Nota: costo_unitario (no precio_unitario).
        """
        return await self._execute(
            """
            SELECT
                c.id_compra,
                c.id_proveedor,
                c.id_sucursal,
                c.fecha_compra,
                c.subtotal,
                c.impuesto,
                c.total,
                c.estado,
                dc.id_producto,
                dc.cantidad,
                dc.costo_unitario,
                dc.subtotal AS subtotal_linea
            FROM system_pos.compra c
            JOIN system_pos.detalle_compra dc ON c.id_compra = dc.id_compra
            WHERE c.id_empresa = :empresa_id
              AND c.fecha_compra::date BETWEEN :fecha_inicio AND :fecha_hasta
              AND c.estado <> 'cancelada'
            ORDER BY c.id_proveedor, dc.id_producto, c.fecha_compra
            """,
            {
                "empresa_id": self.empresa_id,
                "fecha_inicio": self.fecha_hasta - timedelta(days=180),
                "fecha_hasta": self.fecha_hasta,
            },
        )
