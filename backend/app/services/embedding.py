from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from backend.app.core.config import AppSettings, get_app_settings


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


class LocalHashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, descriptor: EmbeddingModelDescriptor) -> None:
        super().__init__(descriptor)

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
            norm = math.sqrt(sum(value * value for value in vector))
            if norm > 0:
                vector = [value / norm for value in vector]
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


def build_embedding_descriptor(settings: AppSettings | None = None) -> EmbeddingModelDescriptor:
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


def get_embedding_provider(settings: AppSettings | None = None) -> EmbeddingProvider:
    descriptor = build_embedding_descriptor(settings)
    if descriptor.provider == "local_hash":
        return LocalHashEmbeddingProvider(descriptor)
    if descriptor.provider == "sentence_transformer":
        return SentenceTransformerEmbeddingProvider(descriptor)
    raise ValueError(f"Unsupported embedding provider: {descriptor.provider}")
