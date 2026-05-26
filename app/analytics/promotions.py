"""Analytics: afinidad de productos mediante Apriori (Market Basket Analysis)."""

from __future__ import annotations

import pandas as pd


def calcular_afinidad(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    min_ventas: int = 100,
    min_support: float = 0.02,
    min_lift: float = 1.5,
    n: int = 5,
) -> list[dict]:
    """Calcula top N pares de productos por lift usando Apriori.

    Solo corre si hay mas de min_ventas transacciones en el periodo.
    Si no hay suficientes datos, retorna lista vacia sin error.

    Args:
        df_ventas: Lineas de detalle_venta con id_venta e id_producto.
        df_catalogo: Productos del catalogo (reservado para futuras versiones).
        min_ventas: Minimo de ventas distintas para ejecutar Apriori.
        min_support: Soporte minimo para itemsets frecuentes.
        min_lift: Lift minimo para reglas de asociacion.
        n: Top N pares por lift a retornar.

    Returns:
        Lista de dicts con par (lista de 2 ids), co_ocurrencia y lift.
    """
    if df_ventas.empty:
        return []

    n_ventas = df_ventas["id_venta"].nunique()
    if n_ventas < min_ventas:
        return []

    try:
        from mlxtend.frequent_patterns import apriori, association_rules
        from mlxtend.preprocessing import TransactionEncoder
    except ImportError:
        return []

    canastas = df_ventas.groupby("id_venta")["id_producto"].apply(list).tolist()

    te = TransactionEncoder()
    te_array = te.fit_transform(canastas)
    df_enc = pd.DataFrame(te_array, columns=te.columns_)

    try:
        itemsets = apriori(df_enc, min_support=min_support, use_colnames=True)
        if itemsets.empty:
            return []

        reglas = association_rules(itemsets, metric="lift", min_threshold=min_lift)
        if reglas.empty:
            return []

        reglas = reglas[
            (reglas["antecedents"].apply(len) == 1) &
            (reglas["consequents"].apply(len) == 1)
        ].copy()

        if reglas.empty:
            return []

        reglas["id1"] = reglas["antecedents"].apply(lambda x: list(x)[0])
        reglas["id2"] = reglas["consequents"].apply(lambda x: list(x)[0])
        reglas["par_key"] = reglas.apply(
            lambda r: tuple(sorted([r["id1"], r["id2"]])), axis=1
        )
        reglas = reglas.sort_values("lift", ascending=False).drop_duplicates("par_key")

        resultado = []
        for _, row in reglas.head(n).iterrows():
            id1, id2 = row["par_key"]
            co = int(
                df_ventas.groupby("id_venta")["id_producto"]
                .apply(lambda ps: id1 in ps.values and id2 in ps.values)
                .sum()
            )
            resultado.append({
                "par": [int(id1), int(id2)],
                "co_ocurrencia": co,
                "lift": round(float(row["lift"]), 2),
            })
        return resultado

    except Exception:
        return []
