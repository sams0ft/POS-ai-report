"""Conexiones a bases de datos: POS (read-only) y Analítica (read-write)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Supabase requiere SSL en todas las conexiones directas
_ssl_args = {"ssl": "require"}

# --- Motor POS (READ-ONLY) ---
pos_engine = create_async_engine(
    settings.pos_database_url,
    echo=settings.environment == "development",
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_ssl_args,
)

# --- Motor Analítica (READ-WRITE) ---
analytics_engine = create_async_engine(
    settings.analytics_database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args=_ssl_args,
)

# Session factories
PosSession = async_sessionmaker(pos_engine, class_=AsyncSession, expire_on_commit=False)
AnalyticsSession = async_sessionmaker(analytics_engine, class_=AsyncSession, expire_on_commit=False)


async def get_pos_db() -> AsyncSession:
    """Dependency: sesión read-only a la DB del POS."""
    async with PosSession() as session:
        yield session


async def get_analytics_db() -> AsyncSession:
    """Dependency: sesión read-write a la DB analítica."""
    async with AnalyticsSession() as session:
        yield session
