"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Verifica que el servicio esté vivo."""
    return {"status": "ok", "service": "pos-reportes-ia"}
