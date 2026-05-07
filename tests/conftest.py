"""Fixtures compartidos para tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Cliente HTTP async para testing de endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_empresa():
    """Datos de empresa de prueba."""
    return {
        "id": 1,
        "nombre": "Tienda Test",
        "nit": "900123456-1",
    }


@pytest.fixture
def sample_report_request():
    """Request de reporte de prueba."""
    return {
        "empresa_id": 1,
        "report_type": "top_bottom_productos",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    }
