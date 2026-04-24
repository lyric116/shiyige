from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Sequence

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class EmbeddingModelDescriptor:
    provider: str
    model_name: str
    dimension: int
    source: str
    revision: str
    device: str
    normalize: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SparseEmbeddingVector:
    indices: list[int]
    values: list[float]

    def to_dict(self) -> dict[str, list[float] | list[int]]:
        return {
            "indices": list(self.indices),
            "values": list(self.values),
        }


class EmbeddingProvider(ABC):
    def __init__(self, descriptor: EmbeddingModelDescriptor) -> None:
        self.descriptor = descriptor

    @property
    def dimension(self) -> int:
        return self.descriptor.dimension

    def describe(self) -> dict[str, Any]:
        return self.descriptor.to_dict()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError


class SparseEmbeddingProvider(ABC):
    def __init__(self, descriptor: EmbeddingModelDescriptor) -> None:
        self.descriptor = descriptor

    def describe(self) -> dict[str, Any]:
        return self.descriptor.to_dict()

    def embed_query(self, text: str) -> SparseEmbeddingVector:
        return self.embed_texts([text])[0]

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[SparseEmbeddingVector]:
        raise NotImplementedError


class ColbertEmbeddingProvider(ABC):
    def __init__(self, descriptor: EmbeddingModelDescriptor) -> None:
        self.descriptor = descriptor

    @property
    def dimension(self) -> int:
        return self.descriptor.dimension

    def describe(self) -> dict[str, Any]:
        return self.descriptor.to_dict()

    def embed_query(self, text: str) -> list[list[float]]:
        return self.embed_texts([text])[0]

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[list[float]]]:
        raise NotImplementedError


def normalize_dense_vector(vector: Sequence[float]) -> list[float]:
    normalized_vector = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in normalized_vector))
    if norm == 0:
        return normalized_vector
    return [value / norm for value in normalized_vector]


def normalize_multivector(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    return [normalize_dense_vector(row) for row in matrix]


def tokenize_embedding_terms(text: str, *, unique: bool = True) -> list[str]:
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return []

    matched_tokens = [match.group(0) for match in TOKEN_PATTERN.finditer(normalized)]
    if not matched_tokens:
        return [normalized]

    ordered_tokens: list[str] = []
    seen_tokens: set[str] = set()
    for token in matched_tokens:
        for candidate in _expand_token(token):
            if not candidate:
                continue
            if not unique:
                ordered_tokens.append(candidate)
                continue
            if candidate not in seen_tokens:
                ordered_tokens.append(candidate)
                seen_tokens.add(candidate)
    return ordered_tokens


def _expand_token(token: str) -> list[str]:
    candidates = [token]
    if all("\u4e00" <= char <= "\u9fff" for char in token) and len(token) > 2:
        for index in range(len(token) - 1):
            candidates.append(token[index : index + 2])
    return candidates


def build_embedding_descriptor(settings: Any | None = None) -> EmbeddingModelDescriptor:
    from backend.app.services.embedding_registry import build_dense_embedding_descriptor

    return build_dense_embedding_descriptor(settings)


def build_sparse_embedding_descriptor(settings: Any | None = None) -> EmbeddingModelDescriptor:
    from backend.app.services.embedding_registry import build_sparse_embedding_descriptor

    return build_sparse_embedding_descriptor(settings)


def build_colbert_embedding_descriptor(settings: Any | None = None) -> EmbeddingModelDescriptor:
    from backend.app.services.embedding_registry import build_colbert_embedding_descriptor

    return build_colbert_embedding_descriptor(settings)


def get_embedding_provider(settings: Any | None = None) -> EmbeddingProvider:
    from backend.app.services.embedding_registry import get_dense_embedding_provider

    return get_dense_embedding_provider(settings)


def get_sparse_embedding_provider(settings: Any | None = None) -> SparseEmbeddingProvider:
    from backend.app.services.embedding_registry import get_sparse_embedding_provider

    return get_sparse_embedding_provider(settings)


def get_colbert_embedding_provider(settings: Any | None = None) -> ColbertEmbeddingProvider:
    from backend.app.services.embedding_registry import get_colbert_embedding_provider

    return get_colbert_embedding_provider(settings)


def get_embedding_bundle(settings: Any | None = None) -> Any:
    from backend.app.services.embedding_registry import get_embedding_bundle

    return get_embedding_bundle(settings)


from backend.app.services.embedding_colbert import (  # noqa: E402
    FastEmbedColbertEmbeddingProvider,
    LocalHashColbertEmbeddingProvider,
)
from backend.app.services.embedding_dense import (  # noqa: E402
    FastEmbedDenseEmbeddingProvider,
    LocalHashEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from backend.app.services.embedding_sparse import (  # noqa: E402
    FastEmbedSparseEmbeddingProvider,
    LocalHashSparseEmbeddingProvider,
)

__all__ = [
    "ColbertEmbeddingProvider",
    "EmbeddingModelDescriptor",
    "EmbeddingProvider",
    "FastEmbedColbertEmbeddingProvider",
    "FastEmbedDenseEmbeddingProvider",
    "FastEmbedSparseEmbeddingProvider",
    "LocalHashColbertEmbeddingProvider",
    "LocalHashEmbeddingProvider",
    "LocalHashSparseEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "SparseEmbeddingProvider",
    "SparseEmbeddingVector",
    "build_colbert_embedding_descriptor",
    "build_embedding_descriptor",
    "build_sparse_embedding_descriptor",
    "get_colbert_embedding_provider",
    "get_embedding_bundle",
    "get_embedding_provider",
    "get_sparse_embedding_provider",
    "normalize_dense_vector",
    "normalize_multivector",
    "tokenize_embedding_terms",
]
