"""Tests para endpoints de la API."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """El health check retorna status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "pos-reportes-ia"


@pytest.mark.asyncio
async def test_generate_report_returns_pending(client, sample_report_request):
    """Generar un reporte retorna status PENDING con un report_id."""
    response = await client.post("/api/v1/reports/generate", json=sample_report_request)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["report_id"] is not None
    assert data["empresa_id"] == 1
    assert data["report_type"] == "top_bottom_productos"
