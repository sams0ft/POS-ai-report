"""Punto de entrada del servicio de Reportes IA."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza del servicio."""
    # TODO: verificar conexión a DB POS, DB analítica, Redis
    yield
    # TODO: cerrar conexiones


app = FastAPI(
    title="POS Reportes IA",
    description="Servicio de reportes inteligentes con sugerencias basadas en IA",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
