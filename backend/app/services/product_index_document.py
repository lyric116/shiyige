from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qdrant_client import models

from backend.app.models.product import Product, ProductSku
from backend.app.services.embedding_registry import EmbeddingProviderBundle
from backend.app.services.embedding_text import build_product_embedding_payload


@dataclass(frozen=True)
class ProductIndexDocument:
    product_id: int
    point_id: int
    content_hash: str
    payload: dict[str, object]
    vector: dict[str, object]

    def to_point_struct(self) -> models.PointStruct:
        return models.PointStruct(
            id=self.point_id,
            vector=self.vector,
            payload=self.payload,
        )


def build_product_index_document(
    product: Product,
    *,
    bundle: EmbeddingProviderBundle,
) -> ProductIndexDocument:
    embedding_payload = build_product_embedding_payload(product)
    return ProductIndexDocument(
        product_id=product.id,
        point_id=get_product_point_id(product.id),
        content_hash=embedding_payload["content_hash"],
        payload=build_product_index_payload(
            product,
            embedding_payload=embedding_payload,
            bundle=bundle,
        ),
        vector={
            "dense": bundle.dense.embed_query(embedding_payload["semantic_text"]),
            "sparse": build_sparse_vector(
                bundle.sparse.embed_query(embedding_payload["keyword_text"])
            ),
            "colbert": bundle.colbert.embed_query(embedding_payload["rerank_text"]),
        },
    )


def build_product_index_payload(
    product: Product,
    *,
    embedding_payload: dict[str, str] | None = None,
    bundle: EmbeddingProviderBundle,
) -> dict[str, object]:
    payload = embedding_payload or build_product_embedding_payload(product)
    price_min, price_max = get_product_price_bounds(product)
    return {
        "product_id": product.id,
        "product_name": product.name,
        "cover_url": product.cover_url,
        "status": get_product_status_label(product),
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "dynasty_style": product.dynasty_style,
        "craft_type": product.craft_type,
        "scene_tag": product.scene_tag,
        "festival_tag": product.festival_tag,
        "tags": [tag.tag for tag in sorted(product.tags, key=lambda item: item.tag)],
        "price_min": price_min,
        "price_max": price_max,
        "stock_available": product_has_available_stock(product),
        "embedding_model_version": build_embedding_model_version(bundle),
        "content_hash": payload["content_hash"],
        "title_text": payload["title_text"],
        "semantic_text": payload["semantic_text"],
        "keyword_text": payload["keyword_text"],
        "rerank_text": payload["rerank_text"],
        "updated_at": product.updated_at.isoformat(),
    }


def build_embedding_model_version(bundle: EmbeddingProviderBundle) -> str:
    return "|".join(
        [
            bundle.dense.descriptor.model_name,
            bundle.sparse.descriptor.model_name,
            bundle.colbert.descriptor.model_name,
        ]
    )


def build_sparse_vector(sparse_vector) -> models.SparseVector:
    return models.SparseVector(
        indices=list(sparse_vector.indices),
        values=list(sparse_vector.values),
    )


def get_product_point_id(product_id: int) -> int:
    return product_id


def get_product_status_label(product: Product) -> str:
    return "active" if product.status == 1 else "inactive"


def is_product_indexable(product: Product) -> bool:
    return product.status == 1


def product_has_available_stock(product: Product) -> bool:
    return any(
        sku.is_active and sku.inventory is not None and sku.inventory.quantity > 0
        for sku in product.skus
    )


def get_product_price_bounds(product: Product) -> tuple[float, float]:
    prices = [sku.price for sku in get_indexable_skus(product)]
    if not prices:
        lowest_price = product.lowest_price
        if lowest_price is None:
            return 0.0, 0.0
        price = decimal_to_float(lowest_price)
        return price, price

    return (
        decimal_to_float(min(prices)),
        decimal_to_float(max(prices)),
    )


def get_indexable_skus(product: Product) -> list[ProductSku]:
    active_skus = [sku for sku in product.skus if sku.is_active]
    return active_skus or list(product.skus)


def decimal_to_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))
