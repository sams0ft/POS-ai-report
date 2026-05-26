"""Loader JSON: serializa el output del ETL a disco."""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID


def _default_serializer(obj):
    """Serializador custom para tipos no soportados por json.dumps."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)!r}")


def save_json(data: dict, output_path: Path) -> Path:
    """Serializa el dict a JSON y lo escribe en output_path.

    Args:
        data: Diccionario con los datos a serializar.
        output_path: Ruta donde escribir el archivo JSON.

    Returns:
        El path donde se escribió el archivo.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(data, default=_default_serializer, ensure_ascii=False, indent=2)
    output_path.write_text(json_str, encoding="utf-8")
    return output_path
