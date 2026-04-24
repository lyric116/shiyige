from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import models

from backend.app.core.config import AppSettings, get_app_settings

DEFAULT_COLBERT_DIMENSION = 128


@dataclass(frozen=True)
class ProductCollectionSchema:
    collection_name: str
    dense_dimension: int
    colbert_dimension: int
    vectors_config: dict[str, models.VectorParams]
    sparse_vectors_config: dict[str, models.SparseVectorParams]
    payload_indexes: dict[str, models.PayloadSchemaType]


def build_product_collection_schema(
    settings: AppSettings | None = None,
) -> ProductCollectionSchema:
    app_settings = settings or get_app_settings()
    payload_indexes = {
        "status": models.PayloadSchemaType.KEYWORD,
        "category_id": models.PayloadSchemaType.INTEGER,
        "category_name": models.PayloadSchemaType.KEYWORD,
        "dynasty_style": models.PayloadSchemaType.KEYWORD,
        "craft_type": models.PayloadSchemaType.KEYWORD,
        "scene_tag": models.PayloadSchemaType.KEYWORD,
        "festival_tag": models.PayloadSchemaType.KEYWORD,
        "tags": models.PayloadSchemaType.KEYWORD,
        "price_min": models.PayloadSchemaType.FLOAT,
        "stock_available": models.PayloadSchemaType.BOOL,
        "embedding_model_version": models.PayloadSchemaType.KEYWORD,
    }
    return ProductCollectionSchema(
        collection_name=app_settings.qdrant_collection_products,
        dense_dimension=app_settings.embedding_dimension,
        colbert_dimension=DEFAULT_COLBERT_DIMENSION,
        vectors_config={
            "dense": models.VectorParams(
                size=app_settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
            "colbert": models.VectorParams(
                size=DEFAULT_COLBERT_DIMENSION,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                ),
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(),
        },
        payload_indexes=payload_indexes,
    )
