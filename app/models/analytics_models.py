"""Modelos SQLAlchemy para la DB analítica propia.

Estas tablas SÍ se crean y son propiedad de este servicio.
Incluyen: reportes generados, caché de métricas, logs de sincronización.
"""

# TODO: definir modelos para:
# - reports: almacena reportes generados (id, empresa_id, tipo, status, contenido, timestamps)
# - sync_log: registro de sincronizaciones ETL
# - metrics_cache: métricas precalculadas para acceso rápido
