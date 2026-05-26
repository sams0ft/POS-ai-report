"""Extractor de gastos en el período del reporte."""

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractGastos(BaseExtractor):
    """Extrae gastos registrados dentro del período del reporte."""

    async def extract(self) -> list[dict]:
        """Extrae gastos con estado 'registrado' en el período.

        Returns:
            Lista de dicts con id_gasto, id_sucursal, id_categoria_gasto,
            descripcion, monto, fecha_gasto, referencia.
        """
        return await self._execute(
            """
            SELECT
                g.id_gasto,
                g.id_sucursal,
                g.id_categoria_gasto,
                g.descripcion,
                g.monto,
                g.fecha_gasto,
                g.referencia
            FROM system_pos.gasto g
            WHERE g.id_empresa = :empresa_id
              AND g.estado = 'registrado'
              AND g.fecha_gasto::date BETWEEN :fecha_desde AND :fecha_hasta
            """,
            {
                "empresa_id": self.empresa_id,
                "fecha_desde": self.fecha_desde,
                "fecha_hasta": self.fecha_hasta,
            },
        )
