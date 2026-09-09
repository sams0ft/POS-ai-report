"""Extractor de movimientos de inventario (últimos 30 días)."""

from datetime import timedelta

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractMovimientos(BaseExtractor):
    """Extrae movimientos de inventario de los últimos 30 días desde fecha_hasta.

    La ventana fija de 30 días es suficiente para analizar rotación reciente.

    La tabla `movimiento_inventario` fue reemplazada por
    `movimiento_inventario_producto`. Diferencias que importan:
        * `cantidad_base_firmada` viene CON SIGNO (negativa en salidas) y en
          unidad base — sustituye a la antigua `cantidad`.
        * `cantidad_anterior`, `cantidad_nueva` y `es_automatico` ya no existen;
          el saldo resultante se consulta en
          `saldo_inventario_producto_sucursal_base`.
        * `tipo_movimiento` admite: entrada, salida, ajuste, compra, venta,
          devolucion, anulacion, conversion.
    """

    async def extract(self) -> list[dict]:
        """Extrae movimientos de inventario de los últimos 30 días.

        Returns:
            Lista de dicts con id_movimiento, id_producto, id_sucursal,
            tipo_movimiento, cantidad (firmada, en unidad base),
            fecha_movimiento, referencia_tipo y motivo.
        """
        return await self._execute(
            """
            SELECT
                m.id_movimiento_inventario_producto AS id_movimiento,
                m.id_producto,
                m.id_sucursal,
                m.tipo_movimiento,
                m.cantidad_base_firmada             AS cantidad,
                m.fecha_movimiento,
                m.referencia_tipo,
                m.motivo
            FROM system_pos.movimiento_inventario_producto m
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
