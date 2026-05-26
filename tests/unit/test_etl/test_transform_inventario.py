"""Tests para app/etl/transformers/transform_inventario.py."""

from datetime import date

import pytest

from app.etl.transformers.transform_inventario import TransformInventario

FECHA_HASTA = date(2026, 5, 10)

CATALOGO = {
    "productos": [
        {"id_producto": 1, "stock_minimo": 5.0},
        {"id_producto": 2, "stock_minimo": 10.0},
        {"id_producto": 3, "stock_minimo": 0.0},
    ]
}


def _fila(
    id_producto: int,
    stock_actual: float,
    fecha_vencimiento=None,
    id_sucursal: int = 1,
    stock_reservado: float = 0.0,
) -> dict:
    return {
        "id_inventario": id_producto * 10,
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "stock_actual": stock_actual,
        "stock_reservado": stock_reservado,
        "fecha_vencimiento": fecha_vencimiento,
        "ultima_actualizacion": None,
    }


def test_no_perecedero_cuando_sin_fecha_vencimiento():
    """Producto sin fecha_vencimiento → es_perecedero=False."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10)])
    item = resultado["por_producto_sucursal"][0]
    assert item["es_perecedero"] is False
    assert item["clasificacion_vencimiento"] is None
    assert item["dias_hasta_vencer"] is None


def test_clasificacion_vencido():
    """Vence antes de fecha_hasta → vencido."""
    # fecha_hasta = 2026-05-10, vence 2026-05-08 → -2 días
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 5, 8))])
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "vencido"
    assert item["dias_hasta_vencer"] == -2


def test_clasificacion_critico():
    """Vence en 5 días → critico (0..7 días)."""
    # fecha_hasta = 2026-05-10, vence 2026-05-15 → 5 días
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 5, 15))])
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "critico"
    assert item["dias_hasta_vencer"] == 5


def test_clasificacion_critico_exactamente_7_dias():
    """En exactamente 7 días también es crítico (límite incluido)."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 5, 17))])  # 7 días
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "critico"


def test_clasificacion_vigilancia():
    """Vence en 20 días → vigilancia (8..30 días)."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 5, 30))])  # 20 días
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "vigilancia"


def test_clasificacion_vigilancia_exactamente_30_dias():
    """En exactamente 30 días también es vigilancia (límite incluido)."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 6, 9))])  # 30 días
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "vigilancia"


def test_clasificacion_normal():
    """Vence en más de 30 días → normal."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 10, date(2026, 7, 9))])  # 60 días
    item = resultado["por_producto_sucursal"][0]
    assert item["clasificacion_vencimiento"] == "normal"


def test_bajo_stock_minimo_verdadero():
    """stock_actual < stock_minimo → bajo_stock_minimo=True."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 3)])  # stock_minimo=5, stock_actual=3
    assert resultado["por_producto_sucursal"][0]["bajo_stock_minimo"] is True


def test_sobre_stock_minimo_falso():
    """stock_actual >= stock_minimo → bajo_stock_minimo=False."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(2, 15)])  # stock_minimo=10, stock_actual=15
    assert resultado["por_producto_sucursal"][0]["bajo_stock_minimo"] is False


def test_stock_disponible_descuenta_reservado():
    """stock_disponible = stock_actual - stock_reservado."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([_fila(1, 20, stock_reservado=5)])
    assert resultado["por_producto_sucursal"][0]["stock_disponible"] == pytest.approx(15.0)


def test_perecederos_en_riesgo_solo_critico_y_vigilancia():
    """perecederos_en_riesgo incluye solo critico y vigilancia, no normal ni vencido."""
    filas = [
        _fila(1, 10, date(2026, 5, 12), id_sucursal=1),   # 2 días → critico
        _fila(2, 10, date(2026, 5, 25), id_sucursal=1),   # 15 días → vigilancia
        _fila(3, 10, date(2026, 7, 9), id_sucursal=1),    # 60 días → normal
    ]
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform(filas)
    ids_riesgo = {r["id_producto"] for r in resultado["perecederos_en_riesgo"]}
    assert 1 in ids_riesgo
    assert 2 in ids_riesgo
    assert 3 not in ids_riesgo


def test_bajo_stock_subset():
    """bajo_stock lista solo los que tienen bajo_stock_minimo=True."""
    filas = [
        _fila(1, 3),   # stock_minimo=5, bajo stock
        _fila(2, 15),  # stock_minimo=10, OK
    ]
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform(filas)
    assert len(resultado["bajo_stock"]) == 1
    assert resultado["bajo_stock"][0]["id_producto"] == 1


def test_empty_retorna_estructura_con_claves():
    """Con datos vacíos las claves deben estar presentes."""
    t = TransformInventario(CATALOGO, FECHA_HASTA)
    resultado = t.transform([])
    assert "por_producto_sucursal" in resultado
    assert "perecederos_en_riesgo" in resultado
    assert "bajo_stock" in resultado
