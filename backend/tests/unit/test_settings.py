import pytest
from pydantic import ValidationError

from backend.app.core.config import AppSettings, InfrastructureSettings


def test_app_settings_use_safe_defaults(monkeypatch) -> None:
    for key in (
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL_NAME",
        "EMBEDDING_DIMENSION",
        "EMBEDDING_MODEL_SOURCE",
        "EMBEDDING_MODEL_REVISION",
        "SPARSE_EMBEDDING_PROVIDER",
        "SPARSE_EMBEDDING_MODEL_NAME",
        "SPARSE_EMBEDDING_DIMENSION",
        "COLBERT_EMBEDDING_PROVIDER",
        "COLBERT_EMBEDDING_MODEL_NAME",
        "COLBERT_EMBEDDING_DIMENSION",
        "QDRANT_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = AppSettings()

    assert settings.app_name == "Shiyige API"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.log_level == "INFO"
    assert settings.embedding_provider == "fastembed_dense"
    assert settings.embedding_model_name == "BAAI/bge-small-zh-v1.5"
    assert settings.embedding_dimension == 512
    assert settings.sparse_embedding_provider == "fastembed_sparse"
    assert settings.colbert_embedding_provider == "fastembed_colbert"
    assert settings.colbert_embedding_dimension == 96
    assert settings.vector_db_provider == "qdrant"
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.recommendation_pipeline_version == "v1"
    assert settings.recommendation_ltr_min_training_samples == 200


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
