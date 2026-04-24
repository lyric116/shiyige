import math

import pytest

from backend.app.core.config import AppSettings
from backend.app.services.embedding import (
    EmbeddingModelDescriptor,
    FastEmbedColbertEmbeddingProvider,
    FastEmbedDenseEmbeddingProvider,
    FastEmbedSparseEmbeddingProvider,
    LocalHashColbertEmbeddingProvider,
    LocalHashSparseEmbeddingProvider,
    build_colbert_embedding_descriptor,
    build_sparse_embedding_descriptor,
    get_colbert_embedding_provider,
    get_embedding_bundle,
    get_sparse_embedding_provider,
)


def test_fastembed_dense_provider_normalizes_model_output() -> None:
    class FakeDenseModel:
        def embed(self, texts):
            assert texts == ["宋代茶具", "宋韵点茶器具"]
            return [[3.0, 4.0], [8.0, 6.0]]

    provider = FastEmbedDenseEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="fastembed_dense",
            model_name="BAAI/bge-small-zh-v1.5",
            dimension=2,
            source="FastEmbed",
            revision="test",
            device="cpu",
            normalize=True,
        ),
        model=FakeDenseModel(),
    )

    vectors = provider.embed_texts(["宋代茶具", "宋韵点茶器具"])

    assert vectors == [[0.6, 0.8], [0.8, 0.6]]


def test_sparse_providers_keep_keyword_signal() -> None:
    descriptor = EmbeddingModelDescriptor(
        provider="local_hash",
        model_name="local-sparse-test",
        dimension=0,
        source="test",
        revision="test",
        device="cpu",
        normalize=False,
    )
    provider = LocalHashSparseEmbeddingProvider(descriptor)

    first = provider.embed_query("香囊 簪子 香囊")
    second = provider.embed_query("香囊")

    assert len(first.indices) == len(first.values)
    assert set(second.indices).issubset(set(first.indices))
    assert any(math.isclose(value, 2.0, rel_tol=1e-6) for value in first.values)


def test_fastembed_sparse_provider_converts_sparse_vectors() -> None:
    class FakeSparseVector:
        def __init__(self, indices, values) -> None:
            self.indices = FakeArray(indices)
            self.values = FakeArray(values)

    class FakeArray:
        def __init__(self, values) -> None:
            self._values = values

        def tolist(self):
            return list(self._values)

    class FakeSparseModel:
        def embed(self, texts):
            assert texts == ["香囊"]
            return [FakeSparseVector([3, 9], [1.0, 0.5])]

    provider = FastEmbedSparseEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="fastembed_sparse",
            model_name="Qdrant/bm25",
            dimension=0,
            source="FastEmbed",
            revision="test",
            device="cpu",
            normalize=False,
        ),
        model=FakeSparseModel(),
    )

    vector = provider.embed_query("香囊")

    assert vector.indices == [3, 9]
    assert vector.values == [1.0, 0.5]


def test_colbert_providers_return_token_level_vectors() -> None:
    local_provider = LocalHashColbertEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="local-colbert-test",
            dimension=4,
            source="test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )
    local_matrix = local_provider.embed_query("宋代茶具")

    assert local_matrix
    assert len(local_matrix[0]) == 4
    local_norm = math.sqrt(sum(value * value for value in local_matrix[0]))
    assert math.isclose(local_norm, 1.0, rel_tol=1e-6)

    class FakeColbertModel:
        def embed(self, texts):
            assert texts == ["宋代茶具"]
            return [[[3.0, 4.0], [5.0, 12.0]]]

    fastembed_provider = FastEmbedColbertEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="fastembed_colbert",
            model_name="answerdotai/answerai-colbert-small-v1",
            dimension=2,
            source="FastEmbed",
            revision="test",
            device="cpu",
            normalize=True,
        ),
        model=FakeColbertModel(),
    )

    matrix = fastembed_provider.embed_query("宋代茶具")

    assert matrix == [[0.6, 0.8], [5 / 13, 12 / 13]]


def test_embedding_registry_builds_dense_sparse_and_colbert_providers() -> None:
    settings = AppSettings(
        embedding_provider="local_hash",
        embedding_model_name="dense-test",
        embedding_dimension=16,
        embedding_model_source="dense-source",
        embedding_model_revision="dense-rev",
        sparse_embedding_provider="local_hash",
        sparse_embedding_model_name="sparse-test",
        sparse_embedding_dimension=0,
        sparse_embedding_model_source="sparse-source",
        sparse_embedding_model_revision="sparse-rev",
        colbert_embedding_provider="local_hash",
        colbert_embedding_model_name="colbert-test",
        colbert_embedding_dimension=8,
        colbert_embedding_model_source="colbert-source",
        colbert_embedding_model_revision="colbert-rev",
    )

    sparse_descriptor = build_sparse_embedding_descriptor(settings)
    colbert_descriptor = build_colbert_embedding_descriptor(settings)
    sparse_provider = get_sparse_embedding_provider(settings)
    colbert_provider = get_colbert_embedding_provider(settings)
    bundle = get_embedding_bundle(settings)

    assert sparse_descriptor.model_name == "sparse-test"
    assert sparse_descriptor.source == "sparse-source"
    assert colbert_descriptor.dimension == 8
    assert sparse_provider.describe() == sparse_descriptor.to_dict()
    assert colbert_provider.describe() == colbert_descriptor.to_dict()
    assert bundle.dense.dimension == 16
    assert bundle.sparse.describe()["provider"] == "local_hash"
    assert bundle.colbert.dimension == 8


def test_sparse_and_colbert_factories_reject_unknown_providers() -> None:
    with pytest.raises(ValueError, match="Unsupported sparse embedding provider"):
        get_sparse_embedding_provider(AppSettings(sparse_embedding_provider="unknown"))

    with pytest.raises(ValueError, match="Unsupported colbert embedding provider"):
        get_colbert_embedding_provider(AppSettings(colbert_embedding_provider="unknown"))
