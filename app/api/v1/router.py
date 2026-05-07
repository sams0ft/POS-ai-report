"""Router principal que agrupa todos los endpoints v1."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
