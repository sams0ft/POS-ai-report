"""Tests para app/etl/transformers/transform_compras.py."""

import pytest

from app.etl.transformers.transform_compras import TransformCompras


def _fila(
    id_compra: int,
    id_proveedor: int,
    id_producto: int,
    fecha_compra: str,
    costo_unitario: float = 100.0,
    cantidad: float = 10.0,
    total: float = 1000.0,
) -> dict:
    return {
        "id_compra": id_compra,
        "id_proveedor": id_proveedor,
        "id_sucursal": 1,
        "id_producto": id_producto,
        "fecha_compra": fecha_compra,
        "subtotal": total,
        "impuesto": 0,
        "total": total,
        "estado": "registrada",
        "cantidad": cantidad,
        "costo_unitario": costo_unitario,
        "subtotal_linea": costo_unitario * cantidad,
    }


def test_lead_time_tres_compras_separadas_7_dias():
    """Con 3 compras separadas exactamente 7 días, lead_time = 7.0."""
    filas = [
        _fila(1, 5, 42, "2026-01-01T00:00:00+00:00"),
        _fila(2, 5, 42, "2026-01-08T00:00:00+00:00"),
        _fila(3, 5, 42, "2026-01-15T00:00:00+00:00"),
    ]
    resultado = TransformCompras().transform(filas)
    lt = resultado["lead_times"]
    assert len(lt) == 1
    assert lt[0]["lead_time_dias"] == pytest.approx(7.0)
    assert lt[0]["num_compras"] == 3
    assert lt[0]["id_proveedor"] == 5
    assert lt[0]["id_producto"] == 42


def test_lead_time_unica_compra_es_none():
    """Con una sola compra no hay lead time calculable."""
    filas = [_fila(1, 5, 42, "2026-01-01T00:00:00+00:00")]
    resultado = TransformCompras().transform(filas)
    assert resultado["lead_times"][0]["lead_time_dias"] is None
    assert resultado["lead_times"][0]["num_compras"] == 1


def test_lead_times_por_proveedor_producto_separados():
    """Distintos pares (proveedor, producto) tienen lead times independientes."""
    filas = [
        _fila(1, 5, 10, "2026-01-01T00:00:00+00:00"),
        _fila(2, 5, 10, "2026-01-08T00:00:00+00:00"),  # lead time 7d para (5,10)
        _fila(3, 5, 20, "2026-01-01T00:00:00+00:00"),
        _fila(4, 5, 20, "2026-01-15T00:00:00+00:00"),  # lead time 14d para (5,20)
    ]
    resultado = TransformCompras().transform(filas)
    lt_map = {(r["id_proveedor"], r["id_producto"]): r["lead_time_dias"]
              for r in resultado["lead_times"]}
    assert lt_map[(5, 10)] == pytest.approx(7.0)
    assert lt_map[(5, 20)] == pytest.approx(14.0)


def test_monto_total_no_duplicado_por_detalle():
    """monto_total usa cabecera deduplicada — no suma el total por cada línea de detalle."""
    filas = [
        _fila(1, 5, 10, "2026-01-01T00:00:00+00:00", total=1000),
        _fila(1, 5, 11, "2026-01-01T00:00:00+00:00", total=1000),  # misma compra
    ]
    resultado = TransformCompras().transform(filas)
    assert resultado["compras_resumen"]["monto_total"] == pytest.approx(1000.0)
    assert resultado["compras_resumen"]["total_compras"] == 1


def test_total_compras_cuenta_compras_distintas():
    """total_compras cuenta compras únicas (no líneas)."""
    filas = [
        _fila(1, 5, 10, "2026-01-01T00:00:00+00:00"),
        _fila(1, 5, 11, "2026-01-01T00:00:00+00:00"),  # misma compra id=1
        _fila(2, 5, 10, "2026-01-08T00:00:00+00:00"),
    ]
    resultado = TransformCompras().transform(filas)
    assert resultado["compras_resumen"]["total_compras"] == 2


def test_ventana_dias_siempre_180():
    """ventana_dias debe ser 180 independientemente de los datos."""
    resultado = TransformCompras().transform([_fila(1, 5, 10, "2026-01-01T00:00:00+00:00")])
    assert resultado["compras_resumen"]["ventana_dias"] == 180


def test_empty_retorna_estructura_con_claves():
    """Con datos vacíos las claves deben estar presentes."""
    resultado = TransformCompras().transform([])
    assert "compras_resumen" in resultado
    assert "lead_times" in resultado
    assert resultado["compras_resumen"]["total_compras"] == 0
    assert resultado["compras_resumen"]["monto_total"] == 0.0
    assert resultado["lead_times"] == []
