"""Configuración de Celery para tareas asíncronas."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pos_reportes_ia",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Tareas programadas
celery_app.conf.beat_schedule = {
    # Sincronización ETL cada 15 minutos
    "sync-ventas-15min": {
        "task": "app.tasks.etl_tasks.sync_ventas",
        "schedule": crontab(minute="*/15"),
    },
    "sync-inventario-30min": {
        "task": "app.tasks.etl_tasks.sync_inventario",
        "schedule": crontab(minute="*/30"),
    },
    "sync-financiero-1h": {
        "task": "app.tasks.etl_tasks.sync_financiero",
        "schedule": crontab(minute=0),
    },
    # Reporte diario automático a las 6 AM Colombia
    "reporte-diario-6am": {
        "task": "app.tasks.report_tasks.generate_daily_reports",
        "schedule": crontab(hour=6, minute=0),
    },
}
