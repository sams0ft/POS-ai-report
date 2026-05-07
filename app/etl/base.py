"""Clase base para sincronizadores ETL."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class BaseSynchronizer(ABC):
    """Base para todos los sincronizadores POS → DB Analítica."""

    def __init__(self, pos_db: AsyncSession, analytics_db: AsyncSession, empresa_id: int):
        self.pos_db = pos_db
        self.analytics_db = analytics_db
        self.empresa_id = empresa_id

    @abstractmethod
    async def sync(self) -> dict:
        """Ejecuta la sincronización.

        Returns:
            Dict con métricas: registros_nuevos, registros_actualizados, errores.
        """
        ...

    @abstractmethod
    async def get_last_sync_timestamp(self) -> str | None:
        """Obtiene el timestamp de la última sincronización exitosa."""
        ...
