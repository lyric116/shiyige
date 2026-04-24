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
    embedding_provider: str = "fastembed_dense"
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    embedding_dimension: int = 512
    embedding_model_source: str = "FastEmbed ONNX runtime for Chinese semantic retrieval"
    embedding_model_revision: str = "qdrant-fastembed"
    embedding_device: str = "cpu"
    embedding_normalize: bool = True
    embedding_cache_dir: str = "./backend/.cache/fastembed"
    embedding_threads: int | None = None
    sparse_embedding_provider: str = "fastembed_sparse"
    sparse_embedding_model_name: str = "Qdrant/bm25"
    sparse_embedding_dimension: int = 0
    sparse_embedding_model_source: str = "FastEmbed sparse BM25 for keyword retrieval"
    sparse_embedding_model_revision: str = "qdrant-bm25"
    sparse_embedding_device: str = "cpu"
    sparse_embedding_normalize: bool = False
    colbert_embedding_provider: str = "fastembed_colbert"
    colbert_embedding_model_name: str = "answerdotai/answerai-colbert-small-v1"
    colbert_embedding_dimension: int = 96
    colbert_embedding_model_source: str = "FastEmbed late interaction reranker"
    colbert_embedding_model_revision: str = "answerai-colbert-small-v1"
    colbert_embedding_device: str = "cpu"
    colbert_embedding_normalize: bool = True
    vector_db_provider: str = "qdrant"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_timeout_seconds: float = 1.5
    qdrant_collection_products: str = "shiyige_products_v1"
    qdrant_collection_users: str = "shiyige_users_v1"
    qdrant_collection_cf: str = "shiyige_collaborative_v1"
    recommendation_pipeline_version: str = "v1"


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
