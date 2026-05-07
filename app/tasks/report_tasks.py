"""Tareas Celery para generación de reportes IA."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.report_tasks.generate_report", bind=True)
def generate_report(self, report_id: str, empresa_id: int, report_type: str, params: dict):
    """Genera un reporte individual.

    Flujo:
    1. Actualizar status → PROCESSING
    2. Ejecutar motor analítico correspondiente
    3. Pasar datos al LLM (vía router de modelos)
    4. Guardar resultado en DB + Redis caché
    5. Actualizar status → COMPLETED
    """
    # TODO: implementar flujo completo
    pass


@celery_app.task(name="app.tasks.report_tasks.generate_daily_reports")
def generate_daily_reports():
    """Genera reportes diarios automáticos para todas las empresas activas.

    Se ejecuta a las 6 AM Colombia (configurado en celery beat).
    Genera: score_salud + anti_desperdicio + quiebre_stock.
    """
    # TODO: listar empresas activas y encolar reportes para cada una
    pass
