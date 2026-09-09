"""Generador de reportes — orquesta el ETL JSON con LM Studio."""

import json
import re
from pathlib import Path

from app.ai.llm_client import OpenAIClient

_GENERAL_PROMPT = Path(__file__).parent / "prompt_templates" / "general_prompt.txt"


def _load_template() -> str:
    return _GENERAL_PROMPT.read_text(encoding="utf-8")


def _extract_sugerencias(text: str) -> list[str]:
    """Extrae sugerencias de una respuesta markdown del LLM.

    Estrategia:
        1. Líneas numeradas (1., 2., ...)
        2. Bullets (-, *, •)
        3. Fallback: últimos 3 párrafos
    """
    lines = text.splitlines()

    numbered = [
        re.sub(r"^\d+\.\s*", "", line.strip())
        for line in lines
        if re.match(r"^\d+\.\s+\S", line.strip())
    ]
    if numbered:
        return numbered

    bullets = [
        re.sub(r"^[-*•]\s*", "", line.strip())
        for line in lines
        if re.match(r"^[-*•]\s+\S", line.strip())
    ]
    if bullets:
        return bullets

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs[-3:] if paragraphs else []


def _trim_payload(data: dict) -> dict:
    """Recorta el payload ETL a las secciones esenciales para el LLM.

    Mantiene las claves analíticas clave y limita listas largas,
    para no exceder el contexto del modelo (~4096 tokens).
    """
    meta = data.get("meta", {})
    return {
        "meta": meta,
        "resumen_ejecutivo": data.get("resumen_ejecutivo", {}),
        "ventas_serie_diaria": {
            "fechas": data.get("ventas_serie_diaria", {}).get("fechas", [])[-7:],
            "ingresos": data.get("ventas_serie_diaria", {}).get("ingresos", [])[-7:],
            "transacciones": data.get("ventas_serie_diaria", {}).get("transacciones", [])[-7:],
        },
        "patron_horario": {
            k: v for k, v in data.get("patron_horario", {}).items()
            if k != "matriz_hora_dia"
        },
        "productos_top": data.get("productos_top", [])[:5],
        "productos_bottom": data.get("productos_bottom", [])[:5],
        "categorias": data.get("categorias", [])[:5],
        "inventario_salud": data.get("inventario_salud", {}),
        "alertas_stock": data.get("alertas_stock", [])[:5],
        "perecederos_riesgo": data.get("perecederos_riesgo", [])[:3],
        "ventas_flash": data.get("ventas_flash"),
        "proveedores_top": data.get("proveedores_top", [])[:3],
        "clientes_resumen": data.get("clientes_resumen", {}),
        "gastos_breakdown": data.get("gastos_breakdown", [])[:8],
        "sucursales": data.get("sucursales", [])[:3],
        "anomalias_detectadas": data.get("anomalias_detectadas", [])[:5],
    }


async def generate_report_content(
    analytics_data: dict,
    empresa_nombre: str,
    periodo: str,
) -> dict:
    """Genera el análisis completo del negocio usando LM Studio.

    Args:
        analytics_data: Dict completo del ETL (17 secciones schema v1.0).
        empresa_nombre: Nombre de la empresa para personalización.
        periodo: Período legible (ej: "1 Abr 2026 – 30 Abr 2026").

    Returns:
        Dict con claves: resumen (str), sugerencias (list[str]), datos (dict).
    """
    client = OpenAIClient()
    template = _load_template()

    trimmed = _trim_payload(analytics_data)
    datos_json = json.dumps(trimmed, ensure_ascii=False, default=str)
    ventas_flash_json = json.dumps(
        analytics_data.get("ventas_flash") or {}, ensure_ascii=False, default=str
    )
    prompt = template.format(
        empresa=empresa_nombre,
        periodo=periodo,
        datos=datos_json,
        ventas_flash=ventas_flash_json,
    )

    raw_response = await client.generate(prompt=prompt)

    return {
        "resumen": raw_response,
        "sugerencias": _extract_sugerencias(raw_response),
        "datos": analytics_data,
    }
