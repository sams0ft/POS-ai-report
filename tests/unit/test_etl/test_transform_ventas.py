"""Tests para app/etl/transformers/transform_ventas.py."""

from datetime import date

import pytest

from app.etl.transformers.transform_ventas import TransformVentas

FECHA_DESDE = date(2026, 4, 1)
FECHA_HASTA = date(2026, 4, 30)


def _linea(
    id_venta: int,
    id_producto: int,
    cantidad: float,
    precio_unitario: float,
    subtotal_linea: float,
    total_venta: float,
    metodo: str = "Efectivo",
    id_sucursal: int = 1,
    fecha: str = "2026-04-15T15:00:00+00:00",
) -> dict:
    """Construye una fila de detalle_venta para tests."""
    return {
        "id_venta": id_venta,
        "id_sucursal": id_sucursal,
        "id_cliente": None,
        "id_usuario": 1,
        "id_metodo_pago": 1,
        "metodo_pago_nombre": metodo,
        "numero_venta": f"V{id_venta:04d}",
        "fecha_venta": fecha,
        "subtotal": total_venta,
        "descuento": 0,
        "impuesto": 0,
        "total": total_venta,
        "id_detalle_venta": id_venta * 100 + id_producto,
        "id_producto": id_producto,
        "cantidad": cantidad,
        "precio_unitario": precio_unitario,
        "descuento_linea": 0,
        "subtotal_linea": subtotal_linea,
    }


def test_resumen_total_ventas_no_duplica_por_detalle():
    """total_ventas debe usar cabecera deduplicada, no sumar por línea."""
    rows = [
        _linea(1, 10, 2, 500, 1000, 1000),
        _linea(1, 11, 1, 200, 200, 1000),  # misma venta id=1
        _linea(2, 10, 3, 500, 1500, 1500),
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    assert resultado["resumen"]["total_ventas"] == pytest.approx(2500.0)


def test_resumen_cantidad_ventas_distinct():
    """cantidad_ventas debe ser COUNT DISTINCT id_venta."""
    rows = [
        _linea(1, 10, 1, 100, 100, 200),
        _linea(1, 11, 1, 100, 100, 200),  # misma venta
        _linea(2, 10, 1, 100, 100, 100),
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    assert resultado["resumen"]["cantidad_ventas"] == 2


def test_resumen_unidades_totales():
    """unidades_totales es la suma de todas las líneas de detalle."""
    rows = [
        _linea(1, 10, 3, 100, 300, 300),
        _linea(1, 11, 2, 50, 100, 300),
        _linea(2, 10, 5, 100, 500, 500),
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    assert resultado["resumen"]["unidades_totales"] == pytest.approx(10.0)


def test_por_dia_agrega_por_fecha():
    """por_dia debe contener una entrada por día con total correcto."""
    rows = [
        _linea(1, 10, 1, 100, 100, 100, fecha="2026-04-15T15:00:00+00:00"),
        _linea(2, 10, 1, 200, 200, 200, fecha="2026-04-16T15:00:00+00:00"),
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    dias = {d["fecha"]: d["total"] for d in resultado["por_dia"]}
    # Nota: 2026-04-15T15:00:00+00:00 = 2026-04-15T10:00:00-05:00 en Bogotá
    assert "2026-04-15" in dias
    assert "2026-04-16" in dias
    assert dias["2026-04-15"] == pytest.approx(100.0)
    assert dias["2026-04-16"] == pytest.approx(200.0)


def test_empty_retorna_estructura_con_todas_las_claves():
    """Con datos vacíos todas las claves deben estar presentes."""
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform([])
    assert "resumen" in resultado
    assert "por_dia" in resultado
    assert "por_hora_dia" in resultado
    assert "por_producto" in resultado
    assert "por_metodo_pago" in resultado
    assert "por_sucursal" in resultado
    assert resultado["resumen"]["total_ventas"] == 0.0
    assert resultado["resumen"]["cantidad_ventas"] == 0


def test_datos_fuera_de_rango_se_filtran():
    """Líneas fuera del rango fecha_desde..fecha_hasta no deben incluirse."""
    rows = [
        _linea(1, 10, 1, 100, 100, 100, fecha="2026-03-31T15:00:00+00:00"),  # antes
        _linea(2, 10, 1, 200, 200, 200, fecha="2026-04-15T15:00:00+00:00"),  # dentro
        _linea(3, 10, 1, 300, 300, 300, fecha="2026-05-01T15:00:00+00:00"),  # después
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    assert resultado["resumen"]["cantidad_ventas"] == 1
    assert resultado["resumen"]["total_ventas"] == pytest.approx(200.0)


def test_por_producto_agrega_ingresos():
    """por_producto debe tener ingresos = suma de subtotal_linea."""
    rows = [
        _linea(1, 42, 2, 500, 1000, 1000),
        _linea(2, 42, 3, 500, 1500, 1500),
    ]
    resultado = TransformVentas(FECHA_DESDE, FECHA_HASTA).transform(rows)
    producto = next(p for p in resultado["por_producto"] if p["id_producto"] == 42)
    assert producto["ingresos"] == pytest.approx(2500.0)
    assert producto["unidades_vendidas"] == pytest.approx(5.0)
