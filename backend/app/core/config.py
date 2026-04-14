from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Shiyige API"
    app_version: str = "0.1.0"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    enable_startup_checks: bool = False
    embedding_provider: str = "local_hash"
    embedding_model_name: str = "shiyige-local-hash-zh"
    embedding_dimension: int = 384
    embedding_model_source: str = "Deterministic local hash fallback for offline development and tests"
    embedding_model_revision: str = "local"
    embedding_device: str = "cpu"
    embedding_normalize: bool = True


class InfrastructureSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    minio_endpoint: str = Field(..., alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., alias="MINIO_SECRET_KEY")
    secret_key: str = Field(..., alias="SECRET_KEY")


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache
def get_infrastructure_settings() -> InfrastructureSettings:
    return InfrastructureSettings()
