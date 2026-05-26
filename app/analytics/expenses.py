"""Analytics: breakdown de gastos operativos por categoria."""

from __future__ import annotations

import pandas as pd


def calcular_gastos_breakdown(
    df_gastos: pd.DataFrame,
    df_categorias_gasto: pd.DataFrame,
    top_n: int = 5,
) -> list[dict]:
    """Agrupa gastos por categoria: top N + Otros.

    Args:
        df_gastos: Gastos del periodo con id_categoria_gasto y monto.
        df_categorias_gasto: Catalogo de categorias de gasto con nombre.
        top_n: Cuantas categorias mostrar antes de agrupar en Otros.

    Returns:
        Lista de dicts con categoria, monto, pct.
    """
    if df_gastos.empty:
        return []

    df = df_gastos.copy()
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    agg = df.groupby("id_categoria_gasto")["monto"].sum().reset_index(name="monto")

    if not df_categorias_gasto.empty and "id_categoria_gasto" in df_categorias_gasto.columns:
        agg = agg.merge(
            df_categorias_gasto[["id_categoria_gasto", "nombre"]],
            on="id_categoria_gasto",
            how="left",
        )
        agg["nombre"] = agg["nombre"].fillna(
            agg["id_categoria_gasto"].apply(lambda x: f"Categoria {x}")
        )
    else:
        agg["nombre"] = agg["id_categoria_gasto"].apply(lambda x: f"Categoria {x}")

    agg = agg.sort_values("monto", ascending=False)
    total = float(agg["monto"].sum())

    top = agg.head(top_n)
    otros_monto = float(agg.iloc[top_n:]["monto"].sum()) if len(agg) > top_n else 0.0

    resultado = []
    for _, row in top.iterrows():
        monto = float(row["monto"])
        resultado.append({
            "categoria": str(row["nombre"]),
            "monto": int(round(monto)),
            "pct": round(monto / total * 100, 2) if total > 0 else 0.0,
        })

    if otros_monto > 0:
        resultado.append({
            "categoria": "Otros",
            "monto": int(round(otros_monto)),
            "pct": round(otros_monto / total * 100, 2) if total > 0 else 0.0,
        })

    return resultado
