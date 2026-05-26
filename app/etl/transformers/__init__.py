# Transformers ETL — arquitectura funcional (schema v1.0)
from app.etl.transformers import (
    transform_afinidad,
    transform_anomalias,
    transform_clientes,
    transform_gastos,
    transform_inventario,
    transform_meta,
    transform_metodos_pago,
    transform_patron_horario,
    transform_productos,
    transform_proveedores,
    transform_resumen_ejecutivo,
    transform_sucursales,
    transform_ventas_serie,
)

__all__ = [
    "transform_afinidad",
    "transform_anomalias",
    "transform_clientes",
    "transform_gastos",
    "transform_inventario",
    "transform_meta",
    "transform_metodos_pago",
    "transform_patron_horario",
    "transform_productos",
    "transform_proveedores",
    "transform_resumen_ejecutivo",
    "transform_sucursales",
    "transform_ventas_serie",
]
