import pytest
from pydantic import ValidationError

from backend.app.core.config import AppSettings, InfrastructureSettings


def test_app_settings_use_safe_defaults() -> None:
    settings = AppSettings()

    assert settings.app_name == "Shiyige API"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.log_level == "INFO"
    assert settings.vector_db_provider == "qdrant"
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.recommendation_pipeline_version == "v1"


def test_infrastructure_settings_raise_clear_error_when_required_env_missing(monkeypatch) -> None:
    for key in (
        "DATABASE_URL",
        "REDIS_URL",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        InfrastructureSettings()

    error_fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert {
        "DATABASE_URL",
        "REDIS_URL",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "SECRET_KEY",
    }.issubset(error_fields)


def test_infrastructure_settings_load_when_required_env_present(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:demo@localhost:5432/shiyige")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    settings = InfrastructureSettings()

    assert settings.database_url.startswith("postgresql://")
    assert settings.redis_url.startswith("redis://")
    assert settings.minio_endpoint == "localhost:9000"
