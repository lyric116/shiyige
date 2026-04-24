from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any, Sequence

from backend.app.services.embedding import (
    EmbeddingModelDescriptor,
    SparseEmbeddingProvider,
    SparseEmbeddingVector,
    tokenize_embedding_terms,
)


class LocalHashSparseEmbeddingProvider(SparseEmbeddingProvider):
    HASH_MODULUS = 2_147_483_647

    def embed_texts(self, texts: Sequence[str]) -> list[SparseEmbeddingVector]:
        return [self._embed_single_text(text) for text in texts]

    def _embed_single_text(self, text: str) -> SparseEmbeddingVector:
        counts = Counter(tokenize_embedding_terms(text, unique=False))
        buckets: dict[int, float] = defaultdict(float)
        for token, count in counts.items():
            bucket = self._hash_token(token)
            buckets[bucket] += float(count)

        ordered_items = sorted(buckets.items(), key=lambda item: item[0])
        return SparseEmbeddingVector(
            indices=[index for index, _ in ordered_items],
            values=[value for _, value in ordered_items],
        )

    def _hash_token(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big", signed=False) % self.HASH_MODULUS


class FastEmbedSparseEmbeddingProvider(SparseEmbeddingProvider):
    def __init__(
        self,
        descriptor: EmbeddingModelDescriptor,
        *,
        cache_dir: str | None = None,
        threads: int | None = None,
        model: Any | None = None,
    ) -> None:
        super().__init__(descriptor)
        self._cache_dir = cache_dir
        self._threads = threads
        self._model = model or self._load_model()

    def _load_model(self) -> Any:
        try:
            from fastembed import SparseTextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required when SPARSE_EMBEDDING_PROVIDER=fastembed_sparse"
            ) from exc

        return SparseTextEmbedding(
            model_name=self.descriptor.model_name,
            cache_dir=self._cache_dir or None,
            threads=self._threads,
            cuda=_resolve_fastembed_device(self.descriptor.device),
            lazy_load=False,
        )

    def embed_texts(self, texts: Sequence[str]) -> list[SparseEmbeddingVector]:
        sparse_vectors = list(self._model.embed(list(texts)))
        return [
            SparseEmbeddingVector(
                indices=[int(index) for index in vector.indices.tolist()],
                values=[float(value) for value in vector.values.tolist()],
            )
            for vector in sparse_vectors
        ]


def _resolve_fastembed_device(device: str) -> bool | Any:
    normalized_device = device.strip().lower()
    if normalized_device in {"", "auto"}:
        try:
            from fastembed.common.types import Device
        except ImportError:
            return False
        return Device.AUTO
    if normalized_device in {"cuda", "gpu"}:
        return True
    return False
