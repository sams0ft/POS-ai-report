"""Configuración central del servicio de reportes IA."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de datos POS (solo lectura)
    pos_database_url: str = "postgresql+asyncpg://readonly:pass@localhost:5432/pos_db"

    # Base de datos analítica
    analytics_database_url: str = "postgresql+asyncpg://user:pass@localhost:5433/analytics_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # LM Studio (servidor local — usar temporalmente en desarrollo)
    use_lmstudio: bool = False
    lmstudio_url: str = "http://127.0.0.1:1234"
    lmstudio_model: str = "google/gemma-4-e4b"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    app_port: int = 8001
    timezone: str = "America/Bogota"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración."""
    return Settings()
