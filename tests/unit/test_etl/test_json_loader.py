"""Tests para app/etl/loaders/json_loader.py."""

import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.etl.loaders.json_loader import save_json


def test_serializa_decimal():
    """Decimal debe convertirse a float sin error."""
    data = {"precio": Decimal("12345.67")}
    with tempfile.TemporaryDirectory() as tmp:
        path = save_json(data, Path(tmp) / "test.json")
        loaded = json.loads(path.read_text())
    assert loaded["precio"] == pytest.approx(12345.67)


def test_serializa_datetime():
    """datetime debe convertirse a string ISO 8601."""
    dt = datetime(2026, 4, 15, 10, 30, 0)
    data = {"ts": dt}
    with tempfile.TemporaryDirectory() as tmp:
        path = save_json(data, Path(tmp) / "test.json")
        loaded = json.loads(path.read_text())
    assert loaded["ts"] == "2026-04-15T10:30:00"


def test_serializa_date():
    """date debe convertirse a string ISO 8601."""
    data = {"fecha": date(2026, 4, 15)}
    with tempfile.TemporaryDirectory() as tmp:
        path = save_json(data, Path(tmp) / "test.json")
        loaded = json.loads(path.read_text())
    assert loaded["fecha"] == "2026-04-15"


def test_crea_directorio_padre():
    """Debe crear la carpeta padre si no existe."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "nested" / "data.json"
        result = save_json({"ok": True}, path)
        assert result.exists()
        loaded = json.loads(result.read_text())
        assert loaded["ok"] is True


def test_retorna_el_path():
    """save_json debe retornar el path donde escribió."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.json"
        result = save_json({"x": 1}, path)
        assert result == path


def test_tipo_no_soportado_lanza_type_error():
    """Un tipo no soportado (set) debe lanzar TypeError, no silenciarse."""
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(TypeError):
            save_json({"conjunto": {1, 2, 3}}, Path(tmp) / "test.json")


def test_json_cargable_sin_errores():
    """El JSON generado debe cargarse sin excepciones con json.load()."""
    data = {
        "precio": Decimal("100.5"),
        "fecha": date(2026, 1, 1),
        "ts": datetime(2026, 1, 1, 12, 0),
        "lista": [1, 2, 3],
        "anidado": {"clave": "valor"},
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = save_json(data, Path(tmp) / "test.json")
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
    assert loaded["lista"] == [1, 2, 3]
