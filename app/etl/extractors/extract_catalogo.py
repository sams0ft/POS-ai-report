"""Extractor de datos maestros del catálogo."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.extractors.base_extractor import BaseExtractor


class ExtractCatalogo(BaseExtractor):
    """Extrae datos maestros: productos, categorías, marcas, proveedores, sucursales.

    No depende de rango de fechas — es un snapshot del estado actual del catálogo.
    """

    def __init__(self, pos_db: AsyncSession, empresa_id: int) -> None:
        super().__init__(pos_db, empresa_id)

    async def extract(self) -> dict:
        """Extrae todos los catálogos secuencialmente sobre la misma sesión.

        SQLAlchemy AsyncSession no permite queries concurrentes sobre la misma
        conexión. La paralelización ocurre a nivel del etl_runner (cada extractor
        tiene su propia sesión).

        Returns:
            Dict con claves: productos, categorias, marcas, proveedores,
            sucursales, categorias_gasto.
        """
        params = {"empresa_id": self.empresa_id}

        productos = await self._execute(
            """
            SELECT id_producto, id_categoria, id_marca, id_proveedor,
                   codigo_barras, nombre, descripcion, precio_compra,
                   precio_venta, stock_minimo, controla_inventario, unidad, estado
            FROM system_pos.producto
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        categorias = await self._execute(
            """
            SELECT id_categoria, nombre, descripcion, color, icono
            FROM system_pos.categoria
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        marcas = await self._execute(
            """
            SELECT id_marca, nombre
            FROM system_pos.marca
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        proveedores = await self._execute(
            """
            SELECT id_proveedor, nit, razon_social, nombre_contacto, telefono
            FROM system_pos.proveedor
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        sucursales = await self._execute(
            """
            SELECT id_sucursal, nombre, tipo_negocio, direccion
            FROM system_pos.sucursal
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        categorias_gasto = await self._execute(
            """
            SELECT id_categoria_gasto, nombre, descripcion
            FROM system_pos.categoria_gasto
            WHERE id_empresa = :empresa_id AND estado = true
            """,
            params,
        )
        return {
            "productos": productos,
            "categorias": categorias,
            "marcas": marcas,
            "proveedores": proveedores,
            "sucursales": sucursales,
            "categorias_gasto": categorias_gasto,
        }
