"""Generador de reportes — orquesta el Analytics Engine con el LLM."""

from pathlib import Path

from app.ai.router import get_llm_client
from app.schemas.reports import ReportType

TEMPLATES_DIR = Path(__file__).parent / "prompt_templates"


def load_template(report_type: ReportType) -> str:
    """Carga el prompt template correspondiente al tipo de reporte."""
    template_path = TEMPLATES_DIR / f"{report_type.value}.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")
    return template_path.read_text(encoding="utf-8")


async def generate_report_content(
    report_type: ReportType,
    analytics_data: dict,
    empresa_nombre: str,
    periodo: str,
) -> dict:
    """Genera el contenido narrativo del reporte usando el LLM apropiado.

    Args:
        report_type: Tipo de reporte a generar.
        analytics_data: Datos ya procesados por el Analytics Engine.
        empresa_nombre: Nombre de la empresa para personalización.
        periodo: Período del reporte (ej: "1 Mar 2026 - 31 Mar 2026").

    Returns:
        Dict con resumen, sugerencias y datos formateados.
    """
    # 1. Seleccionar modelo según tipo de reporte
    client = get_llm_client(report_type)

    # 2. Cargar template y rellenar con datos
    template = load_template(report_type)
    prompt = template.format(
        empresa=empresa_nombre,
        periodo=periodo,
        datos=analytics_data,
    )

    # 3. System prompt común
    system = (
        "Eres un analista de negocios experto para tiendas, cafeterías y minimarkets en Colombia. "
        "Generas reportes claros, accionables y en español. "
        "Tus sugerencias deben ser específicas, con números concretos cuando sea posible. "
        "Evita generalidades. Cada sugerencia debe indicar QUÉ hacer, POR QUÉ y el impacto estimado."
    )

    # 4. Generar narrativa
    response = await client.generate(prompt=prompt, system=system)

    # TODO: parsear respuesta del LLM en estructura (resumen + sugerencias)
    return {
        "resumen": response,
        "sugerencias": [],  # TODO: extraer sugerencias del response
        "datos": analytics_data,
    }
