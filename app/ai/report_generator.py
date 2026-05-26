"""Generador de reportes — orquesta el Analytics Engine con el LLM."""

import json
import re
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


def _extract_json(raw: str) -> dict:
    """Extrae el primer objeto JSON de la respuesta del LLM.

    Tolera respuestas envueltas en bloques ```json ... ``` o con texto
    introductorio antes del JSON, lo cual es común con modelos locales.
    """
    # 1. Intento directo
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Quitar fences ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Buscar el primer {...} balanceado
    start = raw.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(
        f"La respuesta del LLM no contiene JSON válido. Respuesta cruda:\n{raw[:500]}"
    )


async def generate_report_content(
    report_type: ReportType,
    analytics_data: dict,
    empresa_nombre: str,
    periodo: str,
) -> dict:
    """Genera el contenido del reporte usando el LLM apropiado.

    Args:
        report_type: Tipo de reporte a generar.
        analytics_data: Datos ya procesados por el Analytics Engine.
        empresa_nombre: Nombre de la empresa para personalización.
        periodo: Período del reporte (ej: "2026-04-01 → 2026-04-30").

    Returns:
        Dict con: resumen (str), insights (list), recomendaciones (list),
        datos (los analytics originales).
    """
    client = get_llm_client(report_type)
    template = load_template(report_type)

    datos_formateados = json.dumps(
        analytics_data, indent=2, ensure_ascii=False, default=str
    )
    prompt = template.format(
        empresa=empresa_nombre,
        periodo=periodo,
        datos=datos_formateados,
    )

    system = (
        "Eres un analista de negocios experto para tiendas, cafeterías y "
        "minimarkets en Colombia. Respondes únicamente con JSON válido "
        "según el esquema solicitado. Sin texto adicional, sin markdown, "
        "sin bloques de código."
    )

    raw_response = await client.generate(prompt=prompt, system=system)
    parsed = _extract_json(raw_response)

    return {
        "resumen": parsed.get("resumen", ""),
        "insights": parsed.get("insights", []),
        "recomendaciones": parsed.get("recomendaciones", []),
        "datos": analytics_data,
    }
