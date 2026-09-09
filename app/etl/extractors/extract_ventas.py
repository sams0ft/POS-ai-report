"""Extractor de ventas (venta + detalle_venta)."""

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractVentas(BaseExtractor):
    """Extrae ventas completadas con sus líneas de detalle.

    NO trae datos del producto — esos vienen del catálogo.
    Solo incluye id_producto para joinear en la transformación.
    """

    async def extract(self) -> list[dict]:
        """Extrae ventas y sus detalles en el rango de fechas.

        Returns:
            Lista de dicts — una fila por línea de detalle_venta
            (la cabecera de venta se repite por cada línea).
        """
        return await self._execute(
            """
            SELECT
                v.id_venta,
                v.id_sucursal,
                v.id_cliente,
                v.id_usuario,
                v.numero_venta,
                v.fecha_venta,
                v.subtotal,
                v.descuento,
                v.impuesto,
                v.total,
                dv.id_detalle_venta,
                dv.id_producto,
                dv.cantidad,
                dv.precio_unitario,
                dv.descuento AS descuento_linea,
                dv.subtotal AS subtotal_linea
            FROM system_pos.venta v
            JOIN system_pos.detalle_venta dv ON v.id_venta = dv.id_venta
            WHERE v.id_empresa = :empresa_id
              AND v.estado = 'completada'
              AND v.fecha_venta::date BETWEEN :fecha_desde AND :fecha_hasta
            ORDER BY v.fecha_venta
            """,
            {
                "empresa_id": self.empresa_id,
                "fecha_desde": self.fecha_desde,
                "fecha_hasta": self.fecha_hasta,
            },
        )
