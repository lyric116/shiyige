from __future__ import annotations

import hashlib
from typing import Any, Sequence

from backend.app.services.embedding import (
    ColbertEmbeddingProvider,
    EmbeddingModelDescriptor,
    normalize_dense_vector,
    tokenize_embedding_terms,
)


class LocalHashColbertEmbeddingProvider(ColbertEmbeddingProvider):
    def embed_texts(self, texts: Sequence[str]) -> list[list[list[float]]]:
        return [self._embed_single_text(text) for text in texts]

    def _embed_single_text(self, text: str) -> list[list[float]]:
        tokens = tokenize_embedding_terms(text, unique=False) or ["<empty>"]
        return [self._embed_token(token) for token in tokens]

    def _embed_token(self, token: str) -> list[float]:
        values: list[float] = []
        salt = 0
        while len(values) < self.dimension:
            digest = hashlib.sha256(f"{token}:{salt}".encode("utf-8")).digest()
            for index in range(0, len(digest), 4):
                chunk = digest[index : index + 4]
                if len(chunk) < 4:
                    continue
                integer = int.from_bytes(chunk, "big", signed=False)
                values.append((integer / 0xFFFFFFFF) * 2 - 1)
                if len(values) >= self.dimension:
                    break
            salt += 1

        vector = values[: self.dimension]
        if self.descriptor.normalize:
            return normalize_dense_vector(vector)
        return vector


class FastEmbedColbertEmbeddingProvider(ColbertEmbeddingProvider):
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
            from fastembed import LateInteractionTextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required when COLBERT_EMBEDDING_PROVIDER=fastembed_colbert"
            ) from exc

        return LateInteractionTextEmbedding(
            model_name=self.descriptor.model_name,
            cache_dir=self._cache_dir or None,
            threads=self._threads,
            cuda=_resolve_fastembed_device(self.descriptor.device),
            lazy_load=False,
        )

    def embed_texts(self, texts: Sequence[str]) -> list[list[list[float]]]:
        matrices = list(self._model.embed(list(texts)))
        return [self._prepare_matrix(matrix) for matrix in matrices]

    def _prepare_matrix(self, matrix: Sequence[Sequence[float]]) -> list[list[float]]:
        token_vectors = [[float(value) for value in row] for row in matrix]
        if self.descriptor.normalize:
            return [normalize_dense_vector(row) for row in token_vectors]
        return token_vectors


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
