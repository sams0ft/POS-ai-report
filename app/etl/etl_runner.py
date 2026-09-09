"""Orquestador del ETL: extract → transform → load → JSON.

Produce un payload analítico con las 16 claves del schema v1.0.

Uso manual:
    python -m app.etl.etl_runner --empresa-id 1 --fecha-desde 2026-04-01 --fecha-hasta 2026-04-30
"""

import argparse
import asyncio
import json as _json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import structlog
from sqlalchemy import text

from app.analytics.periods import calcular_periodo_comparacion
from app.analytics.stock_predictor import calcular_velocidad_venta
from app.core.database import PosSession
from app.etl.extractors.extract_catalogo import ExtractCatalogo
from app.etl.extractors.extract_compras import ExtractCompras
from app.etl.extractors.extract_gastos import ExtractGastos
from app.etl.extractors.extract_inventario import ExtractInventario
from app.etl.extractors.extract_ventas import ExtractVentas
from app.etl.loaders.json_loader import save_json
from app.analytics.flash_sales import get_flash_sales_data
from app.etl.transformers import (
    transform_afinidad,
    transform_anomalias,
    transform_clientes,
    transform_gastos,
    transform_inventario,
    transform_meta,
    transform_patron_horario,
    transform_productos,
    transform_proveedores,
    transform_resumen_ejecutivo,
    transform_sucursales,
    transform_ventas_flash,
    transform_ventas_serie,
)

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
VERSION_SCHEMA = "1.0"
VENTANA_VELOCIDAD_DIAS = 30


async def run_etl(empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Path:
    """Ejecuta el ETL completo y produce el JSON analítico con 16 secciones.

    Flujo:
        1. Calcular ventanas temporales (período actual, comparación, velocidad).
        2. Extraer en paralelo (catálogo, ventas, inventario, compras, gastos).
        3. Convertir a DataFrames y separar por período.
        4. Llamar a cada transformer en orden del schema.
        5. Ensamblar payload, validar tamaño y guardar.

    Args:
        empresa_id: ID de la empresa a procesar.
        fecha_desde: Inicio del período del reporte.
        fecha_hasta: Fin del período del reporte.

    Returns:
        Path del archivo JSON generado en app/etl/output/.
    """
    log = logger.bind(
        empresa_id=empresa_id,
        fecha_desde=str(fecha_desde),
        fecha_hasta=str(fecha_hasta),
    )
    log.info("etl.inicio")

    # 1. Calcular ventanas temporales
    fecha_comp_desde, fecha_comp_hasta = calcular_periodo_comparacion(fecha_desde, fecha_hasta)
    fecha_desde_efectiva = min(
        fecha_desde - timedelta(days=VENTANA_VELOCIDAD_DIAS),
        fecha_comp_desde,
    )

    # 2. Definir corutinas de extracción
    async def _empresa_info() -> dict:
        async with PosSession() as db:
            result = await db.execute(
                text(
                    "SELECT nombre, sector_economico "
                    "FROM system_pos.empresa "
                    "WHERE id_empresa = :id"
                ),
                {"id": empresa_id},
            )
            row = result.mappings().first()
            return dict(row) if row else {"nombre": f"Empresa {empresa_id}", "sector_economico": ""}

    async def _historico_cliente() -> list[dict]:
        async with PosSession() as db:
            result = await db.execute(
                text(
                    "SELECT id_cliente, MIN(fecha_venta)::date AS primera_venta "
                    "FROM system_pos.venta "
                    "WHERE id_empresa = :id AND id_cliente IS NOT NULL "
                    "GROUP BY id_cliente"
                ),
                {"id": empresa_id},
            )
            return [dict(row) for row in result.mappings().all()]

    async def _catalogo() -> dict:
        async with PosSession() as db:
            resultado = await ExtractCatalogo(db, empresa_id).extract()
        log.info("etl.extraido.catalogo", productos=len(resultado.get("productos", [])))
        return resultado

    async def _ventas() -> list[dict]:
        async with PosSession() as db:
            resultado = await ExtractVentas(
                db, empresa_id, fecha_desde_efectiva, fecha_hasta
            ).extract()
        log.info("etl.extraido.ventas", lineas=len(resultado))
        return resultado

    async def _inventario() -> list[dict]:
        async with PosSession() as db:
            resultado = await ExtractInventario(db, empresa_id).extract()
        log.info("etl.extraido.inventario", filas=len(resultado))
        return resultado

    async def _compras() -> list[dict]:
        async with PosSession() as db:
            resultado = await ExtractCompras(db, empresa_id, fecha_hasta).extract()
        log.info("etl.extraido.compras", lineas=len(resultado))
        return resultado

    async def _gastos() -> list[dict]:
        # Extraer rango ampliado para cubrir período de comparación
        async with PosSession() as db:
            resultado = await ExtractGastos(
                db, empresa_id, fecha_desde_efectiva, fecha_hasta
            ).extract()
        log.info("etl.extraido.gastos", filas=len(resultado))
        return resultado

    async def _flash_sales() -> dict:
        async with PosSession() as db:
            resultado = await get_flash_sales_data(db, empresa_id, fecha_desde, fecha_hasta)
        log.info(
            "etl.extraido.flash_sales",
            dias_debil=len(resultado.get("dia_debil_crudo", [])),
            pool=len(resultado.get("pool_productos_crudo", [])),
        )
        return resultado

    # Extraer todo en paralelo
    log.info("etl.extraccion.inicio")
    (
        empresa_info,
        raw_hist_cliente,
        raw_catalogo,
        raw_ventas,
        raw_inventario,
        raw_compras,
        raw_gastos,
        raw_flash_sales,
    ) = await asyncio.gather(
        _empresa_info(),
        _historico_cliente(),
        _catalogo(),
        _ventas(),
        _inventario(),
        _compras(),
        _gastos(),
        _flash_sales(),
    )
    log.info("etl.extraccion.completada")

    # 3. Construir DataFrames del catálogo
    def _to_df(data: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(data) if data else pd.DataFrame()

    df_productos = _to_df(raw_catalogo.get("productos", []))
    df_categorias_cat = _to_df(raw_catalogo.get("categorias", []))
    df_marcas_cat = _to_df(raw_catalogo.get("marcas", []))
    df_proveedores_cat = _to_df(raw_catalogo.get("proveedores", []))
    df_sucursales_cat = _to_df(raw_catalogo.get("sucursales", []))
    df_categorias_gasto = _to_df(raw_catalogo.get("categorias_gasto", []))

    # Enriquecer catálogo con nombres de categoría y marca
    df_catalogo = df_productos.copy()
    if not df_catalogo.empty:
        if not df_categorias_cat.empty and "id_categoria" in df_categorias_cat.columns:
            df_catalogo = df_catalogo.merge(
                df_categorias_cat[["id_categoria", "nombre"]].rename(
                    columns={"nombre": "categoria_nombre"}
                ),
                on="id_categoria",
                how="left",
            )
        else:
            df_catalogo["categoria_nombre"] = ""

        if not df_marcas_cat.empty and "id_marca" in df_marcas_cat.columns:
            df_catalogo = df_catalogo.merge(
                df_marcas_cat[["id_marca", "nombre"]].rename(
                    columns={"nombre": "marca_nombre"}
                ),
                on="id_marca",
                how="left",
            )
        else:
            df_catalogo["marca_nombre"] = ""

        df_catalogo["categoria_nombre"] = df_catalogo["categoria_nombre"].fillna("")
        df_catalogo["marca_nombre"] = df_catalogo["marca_nombre"].fillna("")

    # 4. Construir DataFrames de ventas y separar por período
    df_ventas_ext = _to_df(raw_ventas)
    if not df_ventas_ext.empty:
        df_ventas_ext["fecha_venta"] = pd.to_datetime(df_ventas_ext["fecha_venta"])
        df_ventas_ext["_fecha_date"] = df_ventas_ext["fecha_venta"].dt.date

    def _filtrar_ventas(df: pd.DataFrame, desde: date, hasta: date) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        mask = (df["_fecha_date"] >= desde) & (df["_fecha_date"] <= hasta)
        return df[mask].copy()

    df_ventas_actual = _filtrar_ventas(df_ventas_ext, fecha_desde, fecha_hasta)
    df_ventas_anterior = _filtrar_ventas(df_ventas_ext, fecha_comp_desde, fecha_comp_hasta)
    df_ventas_velocidad = _filtrar_ventas(
        df_ventas_ext,
        fecha_hasta - timedelta(days=VENTANA_VELOCIDAD_DIAS),
        fecha_hasta,
    )

    # 5. Construir DataFrames de gastos y separar por período
    df_gastos_ext = _to_df(raw_gastos)
    if not df_gastos_ext.empty:
        df_gastos_ext["fecha_gasto"] = pd.to_datetime(df_gastos_ext["fecha_gasto"])
        df_gastos_ext["_fecha_date"] = df_gastos_ext["fecha_gasto"].dt.date

    def _filtrar_gastos(df: pd.DataFrame, desde: date, hasta: date) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        mask = (df["_fecha_date"] >= desde) & (df["_fecha_date"] <= hasta)
        return df[mask].copy()

    df_gastos_actual = _filtrar_gastos(df_gastos_ext, fecha_desde, fecha_hasta)
    df_gastos_anterior = _filtrar_gastos(df_gastos_ext, fecha_comp_desde, fecha_comp_hasta)

    # 6. Otros DataFrames
    df_inventario = _to_df(raw_inventario)
    df_compras = _to_df(raw_compras)
    df_hist_cliente = _to_df(raw_hist_cliente)

    # 7. Pre-calcular velocidad de venta
    df_velocidad = calcular_velocidad_venta(df_ventas_velocidad, fecha_hasta)

    # 8. Métricas de contexto
    dias_periodo = (fecha_hasta - fecha_desde).days + 1
    dias_operados = (
        int(df_ventas_actual["_fecha_date"].nunique())
        if not df_ventas_actual.empty
        else 0
    )

    log.info("etl.transformacion.inicio")

    # 9. Transformaciones (orden importa: bottom se necesita antes que inventario)
    meta = transform_meta.transform(
        empresa_id,
        empresa_info,
        fecha_desde,
        fecha_hasta,
        fecha_comp_desde,
        fecha_comp_hasta,
        dias_periodo,
        dias_operados,
    )

    resumen = transform_resumen_ejecutivo.transform(
        df_ventas_actual,
        df_catalogo,
        df_gastos_actual,
        df_ventas_anterior,
        df_gastos_anterior,
    )

    ventas_serie = transform_ventas_serie.transform(df_ventas_actual, fecha_desde, fecha_hasta)

    patron = transform_patron_horario.transform(df_ventas_actual)

    ventas_flash = transform_ventas_flash.transform(raw_flash_sales, dias_periodo, fecha_hasta)

    top, bottom, categorias = transform_productos.transform(
        df_ventas_actual,
        df_catalogo,
        df_inventario,
        df_velocidad,
        df_ventas_anterior,
        fecha_hasta,
    )

    # bottom se pasa a inventario para calcular valor_inmovilizado
    inv_salud, alertas, perecederos = transform_inventario.transform(
        df_inventario,
        df_catalogo,
        df_ventas_actual,
        df_velocidad,
        bottom,
        dias_periodo,
        fecha_hasta,
    )

    afinidad = transform_afinidad.transform(df_ventas_actual, df_catalogo)

    proveedores = transform_proveedores.transform(df_compras, df_proveedores_cat)

    clientes = transform_clientes.transform(df_ventas_actual, df_hist_cliente)

    gastos = transform_gastos.transform(df_gastos_actual, df_categorias_gasto)

    sucursales = transform_sucursales.transform(df_ventas_actual, df_sucursales_cat)

    anomalias = transform_anomalias.transform(
        df_ventas_actual, df_ventas_anterior, df_catalogo, ventas_serie
    )

    log.info("etl.transformacion.completada")

    # 10. Ensamblar payload con las 17 claves en orden exacto del schema
    payload: dict = {
        "meta": meta,
        "resumen_ejecutivo": resumen,
        "ventas_serie_diaria": ventas_serie,
        "patron_horario": patron,
        "ventas_flash": ventas_flash,
        "productos_top": top,
        "productos_bottom": bottom,
        "categorias": categorias,
        "inventario_salud": inv_salud,
        "alertas_stock": alertas,
        "perecederos_riesgo": perecederos,
        "afinidad_productos": afinidad,
        "proveedores_top": proveedores,
        "clientes_resumen": clientes,
        "gastos_breakdown": gastos,
        "sucursales": sucursales,
        "anomalias_detectadas": anomalias,
    }

    # 11. Validar tamaño del payload
    size_bytes = len(_json.dumps(payload, default=str).encode())
    size_kb = round(size_bytes / 1024, 1)
    if size_kb > 50:
        log.warning("etl.payload.oversized", size_kb=size_kb)
    else:
        log.info("etl.payload.size", size_kb=size_kb)

    # 12. Guardar en disco
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"empresa_{empresa_id}_{fecha_desde}_{fecha_hasta}.json"
    output_path = OUTPUT_DIR / filename
    saved = save_json(payload, output_path)
    log.info("etl.guardado", path=str(saved), size_kb=size_kb)

    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ETL POS Reportes IA — generación de JSON analítico (schema v1.0)"
    )
    parser.add_argument("--empresa-id", type=int, required=True, help="ID de la empresa")
    parser.add_argument(
        "--fecha-desde",
        type=date.fromisoformat,
        required=True,
        help="Fecha inicio del período (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--fecha-hasta",
        type=date.fromisoformat,
        required=True,
        help="Fecha fin del período (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    asyncio.run(run_etl(args.empresa_id, args.fecha_desde, args.fecha_hasta))
