"""Tests para el router de modelos LLM."""

from app.ai.llm_client import ClaudeClient, GeminiClient
from app.ai.router import get_llm_client
from app.schemas.reports import ReportType


def test_routine_reports_use_gemini():
    """Los reportes rutinarios deben usar Gemini Flash."""
    routine_types = [
        ReportType.INGRESOS_EGRESOS,
        ReportType.TOP_BOTTOM_PRODUCTOS,
        ReportType.HORAS_MAGICAS,
        ReportType.ANTI_DESPERDICIO,
        ReportType.QUIEBRE_STOCK,
    ]
    for rt in routine_types:
        client = get_llm_client(rt)
        assert isinstance(client, GeminiClient), f"{rt} debería usar Gemini, no {type(client)}"


def test_premium_reports_use_claude():
    """Los reportes premium deben usar Claude Sonnet."""
    premium_types = [
        ReportType.PRECIO_OPTIMO,
        ReportType.PROMOCIONES,
        ReportType.SCORE_SALUD,
        ReportType.EJECUTIVO_COMPLETO,
    ]
    for rt in premium_types:
        client = get_llm_client(rt)
        assert isinstance(client, ClaudeClient), f"{rt} debería usar Claude, no {type(client)}"
