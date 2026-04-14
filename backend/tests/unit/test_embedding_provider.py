import math

import pytest

from backend.app.core.config import AppSettings
from backend.app.services.embedding import (
    EmbeddingModelDescriptor,
    LocalHashEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    build_embedding_descriptor,
    get_embedding_provider,
)


def test_local_hash_provider_returns_deterministic_normalized_vectors() -> None:
    descriptor = EmbeddingModelDescriptor(
        provider="local_hash",
        model_name="hash-test",
        dimension=8,
        source="local-test",
        revision="test",
        device="cpu",
        normalize=True,
    )
    provider = LocalHashEmbeddingProvider(descriptor)

    first_vector = provider.embed_query("春日出游的素雅汉服")
    second_vector = provider.embed_query("春日出游的素雅汉服")
    third_vector = provider.embed_query("端午香囊礼盒")

    assert len(first_vector) == 8
    assert first_vector == second_vector
    assert first_vector != third_vector
    assert math.isclose(math.sqrt(sum(value * value for value in first_vector)), 1.0, rel_tol=1e-6)


def test_sentence_transformer_provider_delegates_to_underlying_model() -> None:
    class FakeModel:
        def __init__(self) -> None:
            self.calls = []

        def encode(self, texts, normalize_embeddings, convert_to_numpy):
            self.calls.append(
                {
                    "texts": texts,
                    "normalize_embeddings": normalize_embeddings,
                    "convert_to_numpy": convert_to_numpy,
                }
            )
            return [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    fake_model = FakeModel()
    descriptor = EmbeddingModelDescriptor(
        provider="sentence_transformer",
        model_name="BAAI/bge-small-zh-v1.5",
        dimension=3,
        source="Hugging Face / BAAI",
        revision="main",
        device="cpu",
        normalize=True,
    )
    provider = SentenceTransformerEmbeddingProvider(descriptor, model=fake_model)

    vectors = provider.embed_texts(["香囊", "汉服"])

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert fake_model.calls == [
        {
            "texts": ["香囊", "汉服"],
            "normalize_embeddings": True,
            "convert_to_numpy": True,
        }
    ]


def test_embedding_descriptor_and_factory_use_configured_source_and_dimension() -> None:
    settings = AppSettings(
        embedding_provider="local_hash",
        embedding_model_name="BAAI/bge-small-zh-v1.5",
        embedding_dimension=16,
        embedding_model_source="Hugging Face / BAAI",
        embedding_model_revision="main",
        embedding_device="cpu",
        embedding_normalize=False,
    )

    descriptor = build_embedding_descriptor(settings)
    provider = get_embedding_provider(settings)

    assert descriptor.model_name == "BAAI/bge-small-zh-v1.5"
    assert descriptor.dimension == 16
    assert descriptor.source == "Hugging Face / BAAI"
    assert descriptor.normalize is False
    assert provider.describe() == descriptor.to_dict()
    assert provider.dimension == 16


def test_embedding_factory_rejects_unknown_provider() -> None:
    settings = AppSettings(embedding_provider="unknown-provider")

    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        get_embedding_provider(settings)
