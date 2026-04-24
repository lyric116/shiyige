from __future__ import annotations

import hashlib
from typing import Any, Sequence

from backend.app.services.embedding import (
    EmbeddingModelDescriptor,
    EmbeddingProvider,
    normalize_dense_vector,
)


class LocalHashEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_single_text(text) for text in texts]

    def _embed_single_text(self, text: str) -> list[float]:
        normalized_text = " ".join(text.strip().lower().split()) or "<empty>"
        values: list[float] = []
        salt = 0

        while len(values) < self.dimension:
            digest = hashlib.sha256(f"{normalized_text}:{salt}".encode("utf-8")).digest()
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


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        descriptor: EmbeddingModelDescriptor,
        *,
        model: Any | None = None,
    ) -> None:
        super().__init__(descriptor)
        self._model = model or self._load_model()

    def _load_model(self) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required when EMBEDDING_PROVIDER=sentence_transformer"
            ) from exc

        return SentenceTransformer(self.descriptor.model_name, device=self.descriptor.device)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        encoded = self._model.encode(
            list(texts),
            normalize_embeddings=self.descriptor.normalize,
            convert_to_numpy=True,
        )
        return [[float(value) for value in row] for row in encoded]


class FastEmbedDenseEmbeddingProvider(EmbeddingProvider):
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
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required when EMBEDDING_PROVIDER=fastembed_dense"
            ) from exc

        return TextEmbedding(
            model_name=self.descriptor.model_name,
            cache_dir=self._cache_dir or None,
            threads=self._threads,
            cuda=_resolve_fastembed_device(self.descriptor.device),
            lazy_load=False,
        )

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = list(self._model.embed(list(texts)))
        return [self._prepare_vector(vector) for vector in vectors]

    def _prepare_vector(self, vector: Sequence[float]) -> list[float]:
        values = [float(value) for value in vector]
        if self.descriptor.normalize:
            return normalize_dense_vector(values)
        return values


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
