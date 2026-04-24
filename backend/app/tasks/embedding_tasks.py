from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import get_app_settings
from backend.app.models.product import Product
from backend.app.models.recommendation import ProductEmbedding
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.services.embedding_text import build_product_embedding_payload


def build_product_embedding_query(product_ids: Iterable[int] | None = None):
    query = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.embedding),
        )
        .order_by(Product.id.asc())
    )
    if product_ids is not None:
        query = query.where(Product.id.in_(list(product_ids)))
    return query


def upsert_product_embedding(
    db: Session,
    *,
    product: Product,
    provider: EmbeddingProvider,
    force: bool = False,
) -> tuple[ProductEmbedding, bool]:
    settings = get_app_settings()
    payload = build_product_embedding_payload(product)
    existing = product.embedding

    should_reindex = force or existing is None
    if existing is not None and not force:
      should_reindex = (
          existing.model_name != provider.descriptor.model_name
          or existing.content_hash != payload["content_hash"]
          or not existing.embedding_vector
      )

    if not should_reindex and existing is not None:
        return existing, False

    vector = provider.embed_query(payload["embedding_text"])
    if existing is None:
        existing = ProductEmbedding(
            product_id=product.id,
            model_name=provider.descriptor.model_name,
            embedding_text=payload["embedding_text"],
            embedding_vector=vector,
            content_hash=payload["content_hash"],
            qdrant_point_id=str(product.id),
            qdrant_collection=settings.qdrant_collection_products,
            index_status="pending",
            last_indexed_at=datetime.utcnow(),
        )
    else:
        existing.model_name = provider.descriptor.model_name
        existing.embedding_text = payload["embedding_text"]
        existing.embedding_vector = vector
        existing.content_hash = payload["content_hash"]
        existing.qdrant_point_id = str(product.id)
        existing.qdrant_collection = settings.qdrant_collection_products
        existing.index_status = "pending"
        existing.index_error = None
        existing.last_indexed_at = datetime.utcnow()

    db.add(existing)
    return existing, True


def reindex_product_embeddings(
    db: Session,
    *,
    provider: EmbeddingProvider | None = None,
    product_ids: Iterable[int] | None = None,
    force: bool = False,
) -> dict[str, object]:
    embedding_provider = provider or get_embedding_provider()
    products = db.scalars(build_product_embedding_query(product_ids)).unique().all()

    indexed = 0
    skipped = 0
    indexed_product_ids: list[int] = []

    for product in products:
        _, changed = upsert_product_embedding(
            db,
            product=product,
            provider=embedding_provider,
            force=force,
        )
        if changed:
            indexed += 1
            indexed_product_ids.append(product.id)
        else:
            skipped += 1

    db.commit()
    return {
        "indexed": indexed,
        "skipped": skipped,
        "product_ids": indexed_product_ids,
        "model_name": embedding_provider.descriptor.model_name,
    }


def reindex_changed_product_embeddings(
    db: Session,
    *,
    provider: EmbeddingProvider | None = None,
    product_ids: Iterable[int] | None = None,
) -> dict[str, object]:
    return reindex_product_embeddings(
        db,
        provider=provider,
        product_ids=product_ids,
        force=False,
    )


def rebuild_all_product_embeddings(
    db: Session,
    *,
    provider: EmbeddingProvider | None = None,
) -> dict[str, object]:
    return reindex_product_embeddings(db, provider=provider, force=True)
