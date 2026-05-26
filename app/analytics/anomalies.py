"""Analytics: detección de anomalías en ventas, márgenes y categorías."""

from __future__ import annotations

import pandas as pd


def detectar_caida_categoria(
    df_ventas_actual: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    df_catalogo: pd.DataFrame,
) -> list[dict]:
    """Detecta categorías con caída significativa de ventas vs período anterior.

    Umbrales: caída >15% → severidad alta; entre 10% y 15% → media.

    Args:
        df_ventas_actual: Ventas del período actual (una fila por línea).
        df_ventas_anterior: Ventas del período de comparación.
        df_catalogo: Catálogo con id_producto e id_categoria (y categoria_nombre si existe).

    Returns:
        Lista de anomalías tipo 'caida_ventas_categoria'.
    """
    if df_ventas_actual.empty or df_ventas_anterior.empty or df_catalogo.empty:
        return []

    if "id_categoria" not in df_catalogo.columns:
        return []

    cat_cols = ["id_producto", "id_categoria"]
    cat_map = df_catalogo[[c for c in cat_cols if c in df_catalogo.columns]].drop_duplicates("id_producto")

    # Tabla nombre de categoría
    cat_names: dict = {}
    if "categoria_nombre" in df_catalogo.columns:
        cat_names = (
            df_catalogo[["id_categoria", "categoria_nombre"]]
            .drop_duplicates("id_categoria")
            .set_index("id_categoria")["categoria_nombre"]
            .to_dict()
        )

    def _agg_por_categoria(df: pd.DataFrame) -> pd.Series:
        d = df.copy()
        d["subtotal_linea"] = pd.to_numeric(d["subtotal_linea"], errors="coerce").fillna(0)
        d = d.merge(cat_map, on="id_producto", how="left")
        return d.groupby("id_categoria")["subtotal_linea"].sum()

    act = _agg_por_categoria(df_ventas_actual)
    ant = _agg_por_categoria(df_ventas_anterior)

    resultado: list[dict] = []
    for id_cat, ing_act in act.items():
        if pd.isna(id_cat):
            continue
        ing_ant = float(ant.get(id_cat, 0))
        if ing_ant == 0:
            continue

        delta_pct = (float(ing_act) - ing_ant) / ing_ant * 100

        if delta_pct < -15:
            severidad = "alta"
        elif delta_pct < -10:
            severidad = "media"
        else:
            continue

        nombre_cat = str(cat_names.get(id_cat, f"Categoria {int(id_cat)}"))
        descripcion = (
            f"Ventas de {nombre_cat} cayeron {abs(round(delta_pct, 1))}% "
            f"vs período anterior"
        )[:100]

        resultado.append({
            "tipo": "caida_ventas_categoria",
            "entidad": nombre_cat,
            "descripcion": descripcion,
            "severidad": severidad,
            "datos": {
                "ingresos_actual": int(round(float(ing_act))),
                "ingresos_anterior": int(round(ing_ant)),
                "delta_pct": round(delta_pct, 1),
            },
        })

    return resultado


def detectar_margen_caido(
    df_ventas_actual: pd.DataFrame,
    df_catalogo: pd.DataFrame,
) -> list[dict]:
    """Detecta productos del top 20 con margen >3pp por debajo del promedio del período.

    Args:
        df_ventas_actual: Ventas del período actual.
        df_catalogo: Catálogo con id_producto, nombre y precio_compra.

    Returns:
        Lista de anomalías tipo 'margen_caido'.
    """
    if df_ventas_actual.empty or df_catalogo.empty:
        return []

    if "precio_compra" not in df_catalogo.columns:
        return []

    df = df_ventas_actual.copy()
    df["subtotal_linea"] = pd.to_numeric(df["subtotal_linea"], errors="coerce").fillna(0)
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)

    agg = (
        df.groupby("id_producto")
        .agg(ingresos=("subtotal_linea", "sum"), unidades=("cantidad", "sum"))
        .reset_index()
    )
    agg = agg[agg["ingresos"] > 0]
    if agg.empty:
        return []

    top20 = agg.sort_values("ingresos", ascending=False).head(20).copy()

    cat_cols = [c for c in ["id_producto", "nombre", "precio_compra"] if c in df_catalogo.columns]
    top20 = top20.merge(df_catalogo[cat_cols], on="id_producto", how="left")
    top20["precio_compra"] = pd.to_numeric(top20["precio_compra"], errors="coerce").fillna(0)

    top20["costo"] = top20["unidades"] * top20["precio_compra"]
    top20["margen_pct"] = (
        (top20["ingresos"] - top20["costo"]) / top20["ingresos"] * 100
    ).where(top20["ingresos"] > 0, 0.0)

    promedio_margen = float(top20["margen_pct"].mean()) if not top20.empty else 0.0

    resultado: list[dict] = []
    for _, row in top20.iterrows():
        margen = float(row["margen_pct"])
        diferencia = promedio_margen - margen
        if diferencia <= 3:
            continue

        id_prod = int(row["id_producto"])
        nombre = str(row.get("nombre", f"Producto {id_prod}"))
        descripcion = (
            f"Margen de {nombre} ({round(margen, 1)}%) está "
            f"{round(diferencia, 1)}pp por debajo del promedio"
        )[:100]

        resultado.append({
            "tipo": "margen_caido",
            "entidad": nombre,
            "descripcion": descripcion,
            "severidad": "media",
            "datos": {
                "margen_producto_pct": round(margen, 2),
                "margen_promedio_pct": round(promedio_margen, 2),
                "diferencia_pp": round(diferencia, 2),
            },
        })

    return resultado


def detectar_pico_inusual(
    df_ventas: pd.DataFrame,
    serie_diaria: dict,
) -> list[dict]:
    """Detecta días con ventas >2x el promedio diario del período.

    Args:
        df_ventas: Líneas de ventas del período (no usado directamente, reservado).
        serie_diaria: Output de calcular_serie_diaria() con claves fechas e ingresos.

    Returns:
        Lista de anomalías tipo 'pico_ventas_inusual'.
    """
    if not serie_diaria:
        return []

    ingresos: list = serie_diaria.get("ingresos", [])
    fechas: list = serie_diaria.get("fechas", [])

    if not ingresos or not fechas:
        return []

    ingresos_activos = [v for v in ingresos if v > 0]
    if not ingresos_activos:
        return []

    promedio = sum(ingresos_activos) / len(ingresos_activos)
    if promedio == 0:
        return []

    resultado: list[dict] = []
    for fecha, ingreso in zip(fechas, ingresos):
        if ingreso > 2 * promedio:
            descripcion = (
                f"Ventas del {fecha} ({int(ingreso):,} COP) superaron 2x "
                f"el promedio diario ({int(round(promedio)):,} COP)"
            )[:100]
            resultado.append({
                "tipo": "pico_ventas_inusual",
                "entidad": str(fecha),
                "descripcion": descripcion,
                "severidad": "baja",
                "datos": {
                    "fecha": str(fecha),
                    "ingresos_dia": int(ingreso),
                    "promedio_diario": int(round(promedio)),
                    "ratio": round(ingreso / promedio, 2),
                },
            })

    return resultado


def detectar_todas(
    df_ventas_actual: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    serie_diaria: dict,
) -> list[dict]:
    """Combina todas las detecciones de anomalías habilitadas.

    Args:
        df_ventas_actual: Ventas del período actual.
        df_ventas_anterior: Ventas del período de comparación.
        df_catalogo: Catálogo de productos.
        serie_diaria: Output de calcular_serie_diaria().

    Returns:
        Lista combinada de anomalías detectadas (los 3 tipos habilitados).
    """
    resultado: list[dict] = []
    resultado.extend(detectar_caida_categoria(df_ventas_actual, df_ventas_anterior, df_catalogo))
    resultado.extend(detectar_margen_caido(df_ventas_actual, df_catalogo))
    resultado.extend(detectar_pico_inusual(df_ventas_actual, serie_diaria))
    return resultado
