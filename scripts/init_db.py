"""Script para inicializar la base de datos analítica.

Uso: python -m scripts.init_db
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def init_analytics_db():
    """Crea las tablas necesarias en la DB analítica."""
    settings = get_settings()
    engine = create_async_engine(settings.analytics_database_url)

    async with engine.begin() as conn:
        # Habilitar TimescaleDB
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))

        # Tabla de reportes generados
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reports (
                id UUID PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                report_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                fecha_desde DATE NOT NULL,
                fecha_hasta DATE NOT NULL,
                parametros JSONB,
                resumen TEXT,
                datos JSONB,
                sugerencias JSONB,
                pdf_url VARCHAR(500),
                modelo_usado VARCHAR(50),
                tokens_input INTEGER,
                tokens_output INTEGER,
                costo_estimado DECIMAL(10, 6),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                error_message TEXT
            )
        """))

        # Tabla de log de sincronización ETL
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                sync_type VARCHAR(50) NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                registros_nuevos INTEGER DEFAULT 0,
                registros_actualizados INTEGER DEFAULT 0,
                errores INTEGER DEFAULT 0,
                detalles JSONB
            )
        """))

        # Tabla de métricas precalculadas (TimescaleDB hypertable)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS metrics_cache (
                time TIMESTAMPTZ NOT NULL,
                empresa_id INTEGER NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(15, 4),
                metadata JSONB
            )
        """))

        # Convertir a hypertable para series temporales
        await conn.execute(text("""
            SELECT create_hypertable('metrics_cache', 'time', if_not_exists => TRUE)
        """))

        # Índices
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reports_empresa_type
            ON reports (empresa_id, report_type, created_at DESC)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_metrics_empresa_name
            ON metrics_cache (empresa_id, metric_name, time DESC)
        """))

    print("Base de datos analítica inicializada correctamente.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_analytics_db())
