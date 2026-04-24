from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import get_app_settings
from backend.app.models.product import Product, ProductSku
from backend.app.models.recommendation import ProductEmbedding
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.services.embedding_text import build_product_embedding_payload


def build_product_embedding_query(product_ids: Iterable[int] | None = None):
    query = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.embedding),
        )
        .order_by(Product.id.asc())
    )
    if product_ids is not None:
        query = query.where(Product.id.in_(list(product_ids)))
    return query


def load_product_embedding(db: Session, *, product_id: int) -> ProductEmbedding | None:
    return db.scalar(
        select(ProductEmbedding).where(ProductEmbedding.product_id == product_id)
    )


def build_product_embedding_values(
    *,
    product_id: int,
    model_name: str,
    embedding_text: str,
    embedding_vector: list[float],
    content_hash: str,
    collection_name: str,
    now: datetime,
) -> dict[str, object]:
    return {
        "product_id": product_id,
        "model_name": model_name,
        "embedding_text": embedding_text,
        "embedding_vector": embedding_vector,
        "content_hash": content_hash,
        "qdrant_point_id": str(product_id),
        "qdrant_collection": collection_name,
        "index_status": "pending",
        "index_error": None,
        "last_indexed_at": now,
        "created_at": now,
        "updated_at": now,
    }


def upsert_product_embedding_row(
    db: Session,
    *,
    values: dict[str, object],
) -> ProductEmbedding:
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    update_values = {
        key: value
        for key, value in values.items()
        if key not in {"product_id", "created_at"}
    }

    if dialect_name == "sqlite":
        statement = sqlite_insert(ProductEmbedding).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[ProductEmbedding.product_id],
            set_=update_values,
        )
        db.execute(statement)
        db.flush()
    elif dialect_name == "postgresql":
        statement = postgres_insert(ProductEmbedding).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[ProductEmbedding.product_id],
            set_=update_values,
        )
        db.execute(statement)
        db.flush()
    else:
        embedding = ProductEmbedding(**values)
        db.add(embedding)
        db.flush()

    persisted = load_product_embedding(db, product_id=int(values["product_id"]))
    if persisted is None:  # pragma: no cover - defensive safeguard
        raise RuntimeError("product embedding upsert returned no row")
    return persisted


def resolve_existing_product_embedding(db: Session, *, product: Product) -> ProductEmbedding | None:
    existing = product.embedding
    if existing is not None:
        return existing

    existing = load_product_embedding(db, product_id=product.id)
    if existing is not None:
        product.embedding = existing
    return existing


def upsert_product_embedding(
    db: Session,
    *,
    product: Product,
    provider: EmbeddingProvider,
    force: bool = False,
) -> tuple[ProductEmbedding, bool]:
    settings = get_app_settings()
    payload = build_product_embedding_payload(product)
    existing = resolve_existing_product_embedding(db, product=product)

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
    now = datetime.utcnow()
    if existing is None:
        existing = upsert_product_embedding_row(
            db,
            values=build_product_embedding_values(
                product_id=product.id,
                model_name=provider.descriptor.model_name,
                embedding_text=payload["embedding_text"],
                embedding_vector=vector,
                content_hash=payload["content_hash"],
                collection_name=settings.qdrant_collection_products,
                now=now,
            ),
        )
        product.embedding = existing
    else:
        existing.model_name = provider.descriptor.model_name
        existing.embedding_text = payload["embedding_text"]
        existing.embedding_vector = vector
        existing.content_hash = payload["content_hash"]
        existing.qdrant_point_id = str(product.id)
        existing.qdrant_collection = settings.qdrant_collection_products
        existing.index_status = "pending"
        existing.index_error = None
        existing.last_indexed_at = now

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
