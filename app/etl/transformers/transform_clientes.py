"""Transformer para el bloque clientes_resumen del payload."""

import pandas as pd

from app.analytics import customers


def transform(
    df_ventas: pd.DataFrame,
    df_historico_cliente: pd.DataFrame,
) -> dict:
    """Ensambla el bloque clientes_resumen del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.
        df_historico_cliente: DataFrame con id_cliente y primera_venta (date)
            de toda la historia del negocio.

    Returns:
        Dict con total_clientes_activos, clientes_nuevos_periodo,
        ticket_promedio_cliente_recurrente, ticket_promedio_cliente_nuevo,
        pct_ventas_clientes_identificados.
    """
    return customers.calcular_clientes_resumen(df_ventas, df_historico_cliente)
