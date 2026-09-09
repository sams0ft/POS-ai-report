"""Lector del JSON analítico producido por el ETL."""

import json
from datetime import date
from pathlib import Path

_OUTPUT_DIR = Path(__file__).parent / "output"


def load_etl_json(empresa_id: int, fecha_desde: date, fecha_hasta: date) -> dict:
    """Lee el JSON analítico generado por el ETL para el período indicado.

    Args:
        empresa_id: ID de la empresa.
        fecha_desde: Inicio del período (debe coincidir exactamente con el ETL).
        fecha_hasta: Fin del período (debe coincidir exactamente con el ETL).

    Returns:
        Diccionario completo con las 17 secciones del schema v1.0.

    Raises:
        FileNotFoundError: Si el archivo no existe, con el comando exacto para generarlo.
    """
    filename = f"empresa_{empresa_id}_{fecha_desde}_{fecha_hasta}.json"
    path = _OUTPUT_DIR / filename

    if not path.exists():
        comando = (
            f"python -m app.etl.etl_runner "
            f"--empresa-id {empresa_id} "
            f"--fecha-desde {fecha_desde} "
            f"--fecha-hasta {fecha_hasta}"
        )
        raise FileNotFoundError(
            f"No se encontró el archivo ETL '{filename}'. "
            f"Generalo con: {comando}"
        )

    with path.open(encoding="utf-8") as f:
        return json.load(f)
