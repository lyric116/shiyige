from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.services.embedding import (
    ColbertEmbeddingProvider,
    EmbeddingModelDescriptor,
    EmbeddingProvider,
    SparseEmbeddingProvider,
)
from backend.app.services.embedding_colbert import (
    FastEmbedColbertEmbeddingProvider,
    LocalHashColbertEmbeddingProvider,
)
from backend.app.services.embedding_dense import (
    FastEmbedDenseEmbeddingProvider,
    LocalHashEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from backend.app.services.embedding_sparse import (
    FastEmbedSparseEmbeddingProvider,
    LocalHashSparseEmbeddingProvider,
)


@dataclass(frozen=True)
class EmbeddingProviderBundle:
    dense: EmbeddingProvider
    sparse: SparseEmbeddingProvider
    colbert: ColbertEmbeddingProvider


def build_dense_embedding_descriptor(
    settings: AppSettings | None = None,
) -> EmbeddingModelDescriptor:
    app_settings = settings or get_app_settings()
    return EmbeddingModelDescriptor(
        provider=app_settings.embedding_provider,
        model_name=app_settings.embedding_model_name,
        dimension=app_settings.embedding_dimension,
        source=app_settings.embedding_model_source,
        revision=app_settings.embedding_model_revision,
        device=app_settings.embedding_device,
        normalize=app_settings.embedding_normalize,
    )


def build_sparse_embedding_descriptor(
    settings: AppSettings | None = None,
) -> EmbeddingModelDescriptor:
    app_settings = settings or get_app_settings()
    return EmbeddingModelDescriptor(
        provider=app_settings.sparse_embedding_provider,
        model_name=app_settings.sparse_embedding_model_name,
        dimension=app_settings.sparse_embedding_dimension,
        source=app_settings.sparse_embedding_model_source,
        revision=app_settings.sparse_embedding_model_revision,
        device=app_settings.sparse_embedding_device,
        normalize=app_settings.sparse_embedding_normalize,
    )


def build_colbert_embedding_descriptor(
    settings: AppSettings | None = None,
) -> EmbeddingModelDescriptor:
    app_settings = settings or get_app_settings()
    return EmbeddingModelDescriptor(
        provider=app_settings.colbert_embedding_provider,
        model_name=app_settings.colbert_embedding_model_name,
        dimension=app_settings.colbert_embedding_dimension,
        source=app_settings.colbert_embedding_model_source,
        revision=app_settings.colbert_embedding_model_revision,
        device=app_settings.colbert_embedding_device,
        normalize=app_settings.colbert_embedding_normalize,
    )


def get_dense_embedding_provider(settings: AppSettings | None = None) -> EmbeddingProvider:
    app_settings = settings or get_app_settings()
    descriptor = build_dense_embedding_descriptor(app_settings)
    return _build_dense_provider(
        descriptor.provider,
        descriptor.model_name,
        descriptor.dimension,
        descriptor.source,
        descriptor.revision,
        descriptor.device,
        descriptor.normalize,
        app_settings.embedding_cache_dir,
        app_settings.embedding_threads,
    )


def get_sparse_embedding_provider(settings: AppSettings | None = None) -> SparseEmbeddingProvider:
    app_settings = settings or get_app_settings()
    descriptor = build_sparse_embedding_descriptor(app_settings)
    return _build_sparse_provider(
        descriptor.provider,
        descriptor.model_name,
        descriptor.dimension,
        descriptor.source,
        descriptor.revision,
        descriptor.device,
        descriptor.normalize,
        app_settings.embedding_cache_dir,
        app_settings.embedding_threads,
    )


def get_colbert_embedding_provider(settings: AppSettings | None = None) -> ColbertEmbeddingProvider:
    app_settings = settings or get_app_settings()
    descriptor = build_colbert_embedding_descriptor(app_settings)
    return _build_colbert_provider(
        descriptor.provider,
        descriptor.model_name,
        descriptor.dimension,
        descriptor.source,
        descriptor.revision,
        descriptor.device,
        descriptor.normalize,
        app_settings.embedding_cache_dir,
        app_settings.embedding_threads,
    )


def get_embedding_bundle(settings: AppSettings | None = None) -> EmbeddingProviderBundle:
    app_settings = settings or get_app_settings()
    return EmbeddingProviderBundle(
        dense=get_dense_embedding_provider(app_settings),
        sparse=get_sparse_embedding_provider(app_settings),
        colbert=get_colbert_embedding_provider(app_settings),
    )


@lru_cache(maxsize=16)
def _build_dense_provider(
    provider: str,
    model_name: str,
    dimension: int,
    source: str,
    revision: str,
    device: str,
    normalize: bool,
    cache_dir: str,
    threads: int | None,
) -> EmbeddingProvider:
    descriptor = EmbeddingModelDescriptor(
        provider=provider,
        model_name=model_name,
        dimension=dimension,
        source=source,
        revision=revision,
        device=device,
        normalize=normalize,
    )
    if provider == "local_hash":
        return LocalHashEmbeddingProvider(descriptor)
    if provider == "sentence_transformer":
        return SentenceTransformerEmbeddingProvider(descriptor)
    if provider == "fastembed_dense":
        return FastEmbedDenseEmbeddingProvider(
            descriptor,
            cache_dir=cache_dir,
            threads=threads,
        )
    raise ValueError(f"Unsupported embedding provider: {provider}")


@lru_cache(maxsize=16)
def _build_sparse_provider(
    provider: str,
    model_name: str,
    dimension: int,
    source: str,
    revision: str,
    device: str,
    normalize: bool,
    cache_dir: str,
    threads: int | None,
) -> SparseEmbeddingProvider:
    descriptor = EmbeddingModelDescriptor(
        provider=provider,
        model_name=model_name,
        dimension=dimension,
        source=source,
        revision=revision,
        device=device,
        normalize=normalize,
    )
    if provider == "local_hash":
        return LocalHashSparseEmbeddingProvider(descriptor)
    if provider == "fastembed_sparse":
        return FastEmbedSparseEmbeddingProvider(
            descriptor,
            cache_dir=cache_dir,
            threads=threads,
        )
    raise ValueError(f"Unsupported sparse embedding provider: {provider}")


@lru_cache(maxsize=16)
def _build_colbert_provider(
    provider: str,
    model_name: str,
    dimension: int,
    source: str,
    revision: str,
    device: str,
    normalize: bool,
    cache_dir: str,
    threads: int | None,
) -> ColbertEmbeddingProvider:
    descriptor = EmbeddingModelDescriptor(
        provider=provider,
        model_name=model_name,
        dimension=dimension,
        source=source,
        revision=revision,
        device=device,
        normalize=normalize,
    )
    if provider == "local_hash":
        return LocalHashColbertEmbeddingProvider(descriptor)
    if provider == "fastembed_colbert":
        return FastEmbedColbertEmbeddingProvider(
            descriptor,
            cache_dir=cache_dir,
            threads=threads,
        )
    raise ValueError(f"Unsupported colbert embedding provider: {provider}")
