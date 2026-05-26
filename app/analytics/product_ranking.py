"""Analytics: ranking de productos — top, bottom y categorías."""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.analytics.trends import clasificar_tendencia


def calcular_top_productos(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_inventario: pd.DataFrame,
    df_velocidad: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
    n: int = 5,
) -> list[dict]:
    """Calcula el top N productos por ingresos del período.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo enriquecido con categoria_nombre y marca_nombre.
        df_inventario: Inventario actual (stock por producto/sucursal).
        df_velocidad: DataFrame con id_producto y velocidad_diaria (30 días).
        df_ventas_anterior: Líneas de detalle_venta del período de comparación.
        n: Número de productos a retornar.

    Returns:
        Lista de dicts con la forma del bloque productos_top del payload.
    """
    if df_ventas.empty:
        return []

    df = df_ventas.copy()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df["subtotal_linea"] = pd.to_numeric(df["subtotal_linea"], errors="coerce").fillna(0)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)

    # Agregación por producto
    agg = (
        df.groupby("id_producto")
        .agg(
            unidades=("cantidad", "sum"),
            ingresos=("subtotal_linea", "sum"),
            precio_venta_prom=("precio_unitario", "mean"),
        )
        .reset_index()
    )
    agg = agg[agg["unidades"] > 0].sort_values("ingresos", ascending=False).head(n).copy()

    if agg.empty:
        return []

    # Merge catálogo
    cat_cols = [
        c for c in [
            "id_producto", "nombre", "precio_compra",
            "categoria_nombre", "marca_nombre",
        ]
        if c in df_catalogo.columns
    ]
    agg = agg.merge(df_catalogo[cat_cols], on="id_producto", how="left")

    if "precio_compra" not in agg.columns:
        agg["precio_compra"] = 0.0
    agg["precio_compra"] = pd.to_numeric(agg["precio_compra"], errors="coerce").fillna(0)

    if "nombre" not in agg.columns:
        agg["nombre"] = agg["id_producto"].apply(lambda x: f"Producto {x}")
    agg["nombre"] = agg["nombre"].fillna(agg["id_producto"].apply(lambda x: f"Producto {x}"))

    # Stock actual agregado por producto
    if not df_inventario.empty and "id_producto" in df_inventario.columns:
        df_inv = df_inventario.copy()
        df_inv["stock_actual"] = pd.to_numeric(df_inv["stock_actual"], errors="coerce").fillna(0)
        stock_agg = df_inv.groupby("id_producto")["stock_actual"].sum().reset_index()
        agg = agg.merge(stock_agg, on="id_producto", how="left")
    if "stock_actual" not in agg.columns:
        agg["stock_actual"] = 0.0
    agg["stock_actual"] = agg["stock_actual"].fillna(0)

    # Velocidad de venta
    if not df_velocidad.empty and "id_producto" in df_velocidad.columns:
        agg = agg.merge(df_velocidad[["id_producto", "velocidad_diaria"]], on="id_producto", how="left")
    if "velocidad_diaria" not in agg.columns:
        agg["velocidad_diaria"] = 0.0
    agg["velocidad_diaria"] = agg["velocidad_diaria"].fillna(0)

    # Deltas vs período anterior
    delta_map = _calcular_delta_productos(df_ventas, df_ventas_anterior)

    resultado = []
    for _, row in agg.iterrows():
        id_prod = int(row["id_producto"])
        unidades = float(row["unidades"])
        ingresos = float(row["ingresos"])
        precio_compra = float(row["precio_compra"])
        stock = float(row["stock_actual"])
        velocidad = float(row["velocidad_diaria"])

        costo_total = int(round(unidades * precio_compra))
        margen_bruto = int(round(ingresos - costo_total))
        margen_pct = round((ingresos - costo_total) / ingresos * 100, 2) if ingresos > 0 else 0.0
        dias_cobertura = round(stock / velocidad, 1) if velocidad > 0 else 0.0

        deltas = delta_map.get(id_prod, {})
        delta_unidades_pct = deltas.get("delta_unidades_pct", 0.0)
        tendencia = clasificar_tendencia(delta_unidades_pct)

        entry: dict = {
            "id": id_prod,
            "nombre": str(row["nombre"]),
            "categoria": str(row.get("categoria_nombre", "")),
            "marca": str(row.get("marca_nombre", "")),
            "unidades": int(round(unidades)),
            "ingresos": int(round(ingresos)),
            "costo_total": costo_total,
            "margen_bruto": margen_bruto,
            "margen_pct": margen_pct,
            "precio_venta_prom": int(round(float(row.get("precio_venta_prom", 0)))),
            "precio_compra_prom": int(round(precio_compra)),
            "stock_actual": int(round(stock)),
            "dias_cobertura": dias_cobertura,
            "tendencia": tendencia,
            "delta_unidades_pct": round(delta_unidades_pct, 2),
        }

        # Alerta opcional — omitir si no aplica
        if velocidad > 0 and dias_cobertura <= 7:
            entry["alerta"] = "quiebre_inminente"
        elif dias_cobertura > 90:
            entry["alerta"] = "sobrestock"

        resultado.append(entry)

    return resultado


def calcular_bottom_productos(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_inventario: pd.DataFrame,
    fecha_hasta: date,
    n: int = 5,
) -> list[dict]:
    """Calcula el bottom N productos y los productos muertos con inventario.

    Incluye los n peores vendedores (ingresos > 0) más todos los productos
    con stock pero cero ventas en el período (clasificados como 'muerto').

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo enriquecido con categoria_nombre y marca_nombre.
        df_inventario: Inventario actual.
        fecha_hasta: Fecha de fin del período para calcular dias_sin_venta.
        n: Número de peores vendedores a incluir (los muertos se suman aparte).

    Returns:
        Lista de dicts con la forma del bloque productos_bottom del payload.
    """
    if df_inventario.empty:
        return []

    df_inv = df_inventario.copy()
    df_inv["stock_actual"] = pd.to_numeric(df_inv["stock_actual"], errors="coerce").fillna(0)
    stock_agg = df_inv.groupby("id_producto")["stock_actual"].sum().reset_index(name="stock_actual")

    dias_calendario = 0

    if not df_ventas.empty:
        df_v = df_ventas.copy()
        df_v["cantidad"] = pd.to_numeric(df_v["cantidad"], errors="coerce").fillna(0)
        df_v["subtotal_linea"] = pd.to_numeric(df_v["subtotal_linea"], errors="coerce").fillna(0)
        df_v["fecha_venta"] = pd.to_datetime(df_v["fecha_venta"])

        fecha_min_d = df_v["fecha_venta"].dt.date.min()
        dias_calendario = (fecha_hasta - fecha_min_d).days + 1 if fecha_min_d else 30

        agg_v = (
            df_v.groupby("id_producto")
            .agg(
                unidades=("cantidad", "sum"),
                ingresos=("subtotal_linea", "sum"),
                ultima_venta=("fecha_venta", "max"),
            )
            .reset_index()
        )
        agg_v = agg_v[agg_v["unidades"] > 0]
        df_all = stock_agg.merge(agg_v, on="id_producto", how="left")
    else:
        df_all = stock_agg.copy()
        df_all["unidades"] = 0.0
        df_all["ingresos"] = 0.0
        df_all["ultima_venta"] = pd.NaT
        dias_calendario = 30

    df_all["unidades"] = df_all["unidades"].fillna(0)
    df_all["ingresos"] = df_all["ingresos"].fillna(0)

    # Solo con stock (sin stock no hay problema de inmovilizado)
    df_all = df_all[df_all["stock_actual"] > 0]
    if df_all.empty:
        return []

    # Merge catálogo
    cat_cols = [
        c for c in [
            "id_producto", "nombre", "precio_compra",
            "categoria_nombre", "marca_nombre",
        ]
        if c in df_catalogo.columns
    ]
    df_all = df_all.merge(df_catalogo[cat_cols], on="id_producto", how="left")

    if "precio_compra" not in df_all.columns:
        df_all["precio_compra"] = 0.0
    df_all["precio_compra"] = pd.to_numeric(df_all["precio_compra"], errors="coerce").fillna(0)
    if "nombre" not in df_all.columns:
        df_all["nombre"] = df_all["id_producto"].apply(lambda x: f"Producto {x}")
    df_all["nombre"] = df_all["nombre"].fillna(df_all["id_producto"].apply(lambda x: f"Producto {x}"))

    # Bottom N vendedores + todos los muertos
    df_sold = df_all[df_all["unidades"] > 0].sort_values("ingresos").head(n)
    df_dead = df_all[df_all["unidades"] == 0]
    df_bottom = pd.concat([df_sold, df_dead], ignore_index=True).drop_duplicates("id_producto")

    dias_periodo = dias_calendario if dias_calendario > 0 else 1

    resultado = []
    for _, row in df_bottom.iterrows():
        id_prod = int(row["id_producto"])
        stock = float(row["stock_actual"])
        unidades = float(row.get("unidades", 0))
        ingresos = float(row.get("ingresos", 0))
        precio_compra = float(row.get("precio_compra", 0))
        valor_inmovilizado = int(round(stock * precio_compra))

        margen_pct = 0.0
        if ingresos > 0:
            costo = unidades * precio_compra
            margen_pct = round((ingresos - costo) / ingresos * 100, 2)

        ultima_venta = row.get("ultima_venta")
        if pd.isna(ultima_venta) or ultima_venta is None:
            dias_sin_venta = dias_calendario
        else:
            dias_sin_venta = (fecha_hasta - pd.Timestamp(ultima_venta).date()).days

        velocidad_aprox = unidades / dias_periodo
        dias_cobertura = round(stock / velocidad_aprox, 1) if velocidad_aprox > 0 else 0.0

        # Clasificación
        if unidades == 0 and stock > 0:
            clasificacion = "muerto"
            tendencia = "bajando"
        elif dias_sin_venta >= 14:
            clasificacion = "estancado"
            tendencia = "bajando"
        else:
            clasificacion = "lento"
            tendencia = "estable"

        resultado.append({
            "id": id_prod,
            "nombre": str(row["nombre"]),
            "categoria": str(row.get("categoria_nombre", "")),
            "marca": str(row.get("marca_nombre", "")),
            "unidades": int(round(unidades)),
            "ingresos": int(round(ingresos)),
            "stock_actual": int(round(stock)),
            "dias_sin_venta": dias_sin_venta,
            "dias_cobertura": dias_cobertura,
            "margen_pct": margen_pct,
            "valor_inventario_inmovilizado": valor_inmovilizado,
            "tendencia": tendencia,
            "clasificacion": clasificacion,
        })

    return resultado


def calcular_categorias(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_ventas_anterior: pd.DataFrame,
) -> list[dict]:
    """Calcula métricas de ventas por categoría del período.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_catalogo: Catálogo con id_categoria y categoria_nombre.
        df_ventas_anterior: Líneas del período de comparación.

    Returns:
        Lista de dicts con la forma del bloque categorias del payload.
    """
    if df_ventas.empty or df_catalogo.empty:
        return []

    if "id_categoria" not in df_catalogo.columns:
        return []

    cat_cols = [
        c for c in ["id_producto", "id_categoria", "precio_compra", "categoria_nombre"]
        if c in df_catalogo.columns
    ]

    df_v = df_ventas.copy()
    df_v["cantidad"] = pd.to_numeric(df_v["cantidad"], errors="coerce").fillna(0)
    df_v["subtotal_linea"] = pd.to_numeric(df_v["subtotal_linea"], errors="coerce").fillna(0)
    df_v = df_v.merge(df_catalogo[cat_cols], on="id_producto", how="left")

    if "id_categoria" not in df_v.columns or df_v["id_categoria"].isna().all():
        return []

    if "precio_compra" not in df_v.columns:
        df_v["precio_compra"] = 0.0
    df_v["precio_compra"] = pd.to_numeric(df_v["precio_compra"], errors="coerce").fillna(0)
    df_v["costo_linea"] = df_v["cantidad"] * df_v["precio_compra"]

    # Agregación principal
    agg = (
        df_v.groupby("id_categoria")
        .agg(
            ingresos=("subtotal_linea", "sum"),
            unidades=("cantidad", "sum"),
            productos_activos=("id_producto", "nunique"),
            ingresos_brutos=("subtotal_linea", "sum"),
            costos_brutos=("costo_linea", "sum"),
        )
        .reset_index()
    )
    agg["margen_pct_prom"] = (
        (agg["ingresos_brutos"] - agg["costos_brutos"]) / agg["ingresos_brutos"] * 100
    ).where(agg["ingresos_brutos"] > 0, 0.0).round(2)
    agg = agg.drop(columns=["ingresos_brutos", "costos_brutos"])

    # Nombre de categoría
    if "categoria_nombre" in df_catalogo.columns:
        cat_nombres = (
            df_catalogo[["id_categoria", "categoria_nombre"]]
            .drop_duplicates("id_categoria")
        )
        agg = agg.merge(cat_nombres, on="id_categoria", how="left")
        agg["categoria_nombre"] = agg["categoria_nombre"].fillna(
            agg["id_categoria"].apply(lambda x: f"Categoria {x}")
        )
    else:
        agg["categoria_nombre"] = agg["id_categoria"].apply(lambda x: f"Categoria {x}")

    total_ingresos = float(agg["ingresos"].sum())
    delta_cat_map = _calcular_delta_categorias(df_ventas, df_ventas_anterior, df_catalogo)

    resultado = []
    for _, row in agg.nlargest(5, "ingresos").iterrows():
        ingresos = float(row["ingresos"])
        pct = round(ingresos / total_ingresos * 100, 2) if total_ingresos > 0 else 0.0
        id_cat = int(row["id_categoria"]) if pd.notna(row["id_categoria"]) else 0
        delta = delta_cat_map.get(id_cat, 0.0)
        tendencia = clasificar_tendencia(delta)

        resultado.append({
            "id": id_cat,
            "nombre": str(row["categoria_nombre"]),
            "ingresos": int(round(ingresos)),
            "unidades": int(round(float(row["unidades"]))),
            "margen_pct_prom": round(float(row["margen_pct_prom"]), 2),
            "pct_total_ventas": pct,
            "productos_activos": int(row["productos_activos"]),
            "tendencia": tendencia,
        })

    return resultado


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _calcular_delta_productos(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
) -> dict[int, dict]:
    """Calcula delta de unidades por producto entre dos períodos.

    Args:
        df_actual: Ventas del período actual.
        df_anterior: Ventas del período de comparación.

    Returns:
        Dict id_producto → {delta_unidades_pct: float}.
    """
    if df_actual.empty or df_anterior.empty:
        return {}

    def _agg(df: pd.DataFrame) -> pd.Series:
        d = df.copy()
        d["cantidad"] = pd.to_numeric(d["cantidad"], errors="coerce").fillna(0)
        return d.groupby("id_producto")["cantidad"].sum()

    act = _agg(df_actual)
    ant = _agg(df_anterior)

    result: dict[int, dict] = {}
    for id_prod, unid_act in act.items():
        unid_ant = float(ant.get(id_prod, 0))
        if unid_ant > 0:
            delta = round((float(unid_act) - unid_ant) / unid_ant * 100, 2)
        elif float(unid_act) > 0:
            delta = 100.0
        else:
            delta = 0.0
        result[int(id_prod)] = {"delta_unidades_pct": delta}

    return result


def _calcular_delta_categorias(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    df_catalogo: pd.DataFrame,
) -> dict[int, float]:
    """Calcula delta de ingresos por categoría entre dos períodos.

    Args:
        df_actual: Ventas del período actual.
        df_anterior: Ventas del período de comparación.
        df_catalogo: Catálogo con id_producto e id_categoria.

    Returns:
        Dict id_categoria → delta_pct.
    """
    if df_actual.empty or df_anterior.empty or df_catalogo.empty:
        return {}

    if "id_categoria" not in df_catalogo.columns:
        return {}

    cat_map = df_catalogo[["id_producto", "id_categoria"]].copy()

    def _agg_cat(df: pd.DataFrame) -> pd.Series:
        d = df.copy()
        d["subtotal_linea"] = pd.to_numeric(d["subtotal_linea"], errors="coerce").fillna(0)
        d = d.merge(cat_map, on="id_producto", how="left")
        return d.groupby("id_categoria")["subtotal_linea"].sum()

    act = _agg_cat(df_actual)
    ant = _agg_cat(df_anterior)

    result: dict[int, float] = {}
    for id_cat, ing_act in act.items():
        if pd.isna(id_cat):
            continue
        ing_ant = float(ant.get(id_cat, 0))
        if ing_ant > 0:
            delta = round((float(ing_act) - ing_ant) / ing_ant * 100, 2)
        elif float(ing_act) > 0:
            delta = 100.0
        else:
            delta = 0.0
        result[int(id_cat)] = delta

    return result
