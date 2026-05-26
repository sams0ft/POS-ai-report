"""Helper: clasificación de tendencia basada en delta porcentual."""


def clasificar_tendencia(delta_pct: float, umbral: float = 10.0) -> str:
    """Clasifica una variación porcentual en tendencia de negocio.

    Args:
        delta_pct: Variación porcentual (actual - anterior) / anterior * 100.
        umbral: Porcentaje mínimo para considerar cambio significativo. Default 10%.

    Returns:
        'subiendo' si delta_pct > umbral,
        'bajando' si delta_pct < -umbral,
        'estable' en caso contrario.
    """
    if delta_pct > umbral:
        return "subiendo"
    if delta_pct < -umbral:
        return "bajando"
    return "estable"
