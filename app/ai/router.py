"""Router de modelos LLM — decide qué modelo usar según el tipo de reporte."""

from app.ai.llm_client import BaseLLMClient, ClaudeClient, GeminiClient, LMStudioClient
from app.core.config import get_settings
from app.schemas.reports import ReportType

settings = get_settings()

# Reportes que requieren razonamiento más sofisticado → Claude Sonnet
PREMIUM_REPORTS: set[ReportType] = {
    ReportType.PRECIO_OPTIMO,
    ReportType.PROMOCIONES,
    ReportType.SCORE_SALUD,
    ReportType.EJECUTIVO_COMPLETO,
}

# El resto → Gemini Flash (más económico, suficiente calidad)
ROUTINE_REPORTS: set[ReportType] = {
    ReportType.INGRESOS_EGRESOS,
    ReportType.TOP_BOTTOM_PRODUCTOS,
    ReportType.HORAS_MAGICAS,
    ReportType.ANTI_DESPERDICIO,
    ReportType.QUIEBRE_STOCK,
}


def get_llm_client(report_type: ReportType) -> BaseLLMClient:
    """Retorna el cliente LLM apropiado según el tipo de reporte.

    Si USE_LMSTUDIO=true en .env, todos los reportes usan LM Studio (desarrollo).
    En producción:
    - Reportes rutinarios (80%) → Gemini 2.5 Flash (~$0.30/$2.50 por 1M tokens)
    - Reportes premium (20%)   → Claude Sonnet 4.6 (~$3/$15 por 1M tokens)
    """
    if settings.use_lmstudio:
        return LMStudioClient()

    if report_type in PREMIUM_REPORTS:
        return ClaudeClient()
    return GeminiClient()
