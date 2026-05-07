"""Tareas Celery para sincronización ETL."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.etl_tasks.sync_ventas")
def sync_ventas():
    """Sincroniza ventas del POS a la DB analítica."""
    # TODO: instanciar SyncVentas y ejecutar
    pass


@celery_app.task(name="app.tasks.etl_tasks.sync_inventario")
def sync_inventario():
    """Sincroniza inventario del POS a la DB analítica."""
    # TODO: instanciar SyncInventario y ejecutar
    pass


@celery_app.task(name="app.tasks.etl_tasks.sync_financiero")
def sync_financiero():
    """Sincroniza datos financieros del POS a la DB analítica."""
    # TODO: instanciar SyncFinanciero y ejecutar
    pass
