"""Application settings loaded from environment / .env (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration.

    DATABASE_URL defaults to PostgreSQL; override to sqlite:///./buildpulse.db
    (or :memory: for tests) when Docker/Postgres is unavailable.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BUILDPULSE_", extra="ignore")

    app_name: str = "BuildPulse"
    debug: bool = False
    api_version: str = "1.0"

    database_url: str = "postgresql+psycopg://buildpulse:buildpulse@localhost:5432/buildpulse"

    # Optional auth: if a project has an api_key set it must be presented
    # via the X-API-Key header. Backend cannot be locked down globally by default.
    global_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Ingestion guardrails
    max_report_bytes: int = 32 * 1024 * 1024
    max_issues_per_build: int = 20000


@lru_cache
def get_settings() -> Settings:
    return Settings()
