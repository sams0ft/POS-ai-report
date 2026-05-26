"""Clase base para todos los extractores del ETL."""

from abc import ABC, abstractmethod
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BaseExtractor(ABC):
    """Extractor base: ejecuta queries contra system_pos y retorna dicts.

    Todos los extractores heredan de esta clase. Los que no requieren
    fechas (catálogo, inventario snapshot) pueden ignorar esos parámetros.
    """

    def __init__(
        self,
        pos_db: AsyncSession,
        empresa_id: int,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> None:
        """Inicializa el extractor.

        Args:
            pos_db: Sesión asíncrona a la DB del POS (solo lectura).
            empresa_id: ID de la empresa a procesar.
            fecha_desde: Inicio del período (opcional según extractor).
            fecha_hasta: Fin del período (opcional según extractor).
        """
        self.pos_db = pos_db
        self.empresa_id = empresa_id
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta

    @abstractmethod
    async def extract(self) -> list[dict] | dict:
        """Ejecuta la extracción y retorna los registros.

        Returns:
            Lista de dicts (una por fila) o dict de listas (catálogo).
        """
        ...

    async def _execute(self, query: str, params: dict) -> list[dict]:
        """Ejecuta una query SQL y retorna lista de dicts.

        Args:
            query: SQL como string (se envuelve en text()).
            params: Parámetros para la query.

        Returns:
            Lista de dicts con los resultados.
        """
        result = await self.pos_db.execute(text(query), params)
        return [dict(row) for row in result.mappings().all()]
