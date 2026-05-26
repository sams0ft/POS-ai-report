"""Transformer para el bloque patron_horario del payload."""

import pandas as pd

from app.analytics import peak_hours


def transform(df_ventas: pd.DataFrame) -> dict:
    """Ensambla el bloque patron_horario del payload.

    Args:
        df_ventas: Líneas de detalle_venta del período actual.

    Returns:
        Dict con matriz_hora_dia, horas_pico, horas_valle, dia_pico,
        dia_valle y concentracion_top3_horas_pct.
    """
    return peak_hours.calcular_patron_horario(df_ventas)
