from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from qdrant_client import QdrantClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.models.product import Product, ProductSku
from backend.app.models.recommendation import ProductEmbedding
from backend.app.services.embedding_registry import EmbeddingProviderBundle, get_embedding_bundle
from backend.app.services.product_index_document import (
    build_product_index_document,
    build_product_index_payload,
    get_product_point_id,
    is_product_indexable,
)
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.tasks.embedding_tasks import upsert_product_embedding
from backend.app.tasks.qdrant_schema_tasks import ensure_product_collection

INDEX_STATUS_INDEXED = "indexed"
INDEX_STATUS_FAILED = "failed"
INDEX_STATUS_INACTIVE = "inactive"


def build_product_index_query(product_ids: Iterable[int] | None = None):
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
        query = query.where(Product.id.in_(sorted(set(product_ids))))
    return query


def sync_products_to_qdrant(
    db: Session,
    *,
    mode: str = "full",
    product_ids: Iterable[int] | None = None,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle: EmbeddingProviderBundle | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    product_bundle = bundle or get_embedding_bundle(app_settings)
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None

    try:
        ensure_product_collection(
            client=qdrant_client,
            settings=app_settings,
            recreate_on_drift=mode == "full",
        )
        resolved_product_ids = resolve_product_ids(db, mode, product_ids)
        products = db.scalars(build_product_index_query(resolved_product_ids)).unique().all()

        indexed = 0
        payload_updates = 0
        deleted = 0
        skipped = 0
        failed = 0
        processed_product_ids: list[int] = []
        failed_product_ids: list[int] = []

        for product in products:
            if (
                mode == "incremental"
                and product_ids is None
                and not needs_incremental_sync(product)
            ):
                skipped += 1
                continue

            processed_product_ids.append(product.id)
            existing = product.embedding
            current_embedding = existing

            try:
                if not is_product_indexable(product):
                    delete_product_point(
                        qdrant_client,
                        collection_name=app_settings.qdrant_collection_products,
                        point_id=get_product_point_id(product.id),
                    )
                    if existing is not None:
                        existing.qdrant_point_id = str(get_product_point_id(product.id))
                        existing.qdrant_collection = app_settings.qdrant_collection_products
                        existing.index_status = INDEX_STATUS_INACTIVE
                        existing.index_error = None
                        existing.last_indexed_at = datetime.utcnow()
                        db.add(existing)
                    deleted += 1
                    continue

                previous_status = existing.index_status if existing is not None else None
                embedding, embedding_changed = upsert_product_embedding(
                    db,
                    product=product,
                    provider=product_bundle.dense,
                    force=mode == "full",
                )
                current_embedding = embedding
                requires_vector_upsert = (
                    mode == "full"
                    or embedding_changed
                    or previous_status != INDEX_STATUS_INDEXED
                    or not embedding.qdrant_point_id
                )

                if requires_vector_upsert:
                    document = build_product_index_document(product, bundle=product_bundle)
                    qdrant_client.upsert(
                        collection_name=app_settings.qdrant_collection_products,
                        points=[document.to_point_struct()],
                        wait=True,
                    )
                    indexed += 1
                else:
                    payload = build_product_index_payload(
                        product,
                        bundle=product_bundle,
                    )
                    qdrant_client.set_payload(
                        app_settings.qdrant_collection_products,
                        payload=payload,
                        points=[get_product_point_id(product.id)],
                        wait=True,
                    )
                    payload_updates += 1

                embedding.qdrant_point_id = str(get_product_point_id(product.id))
                embedding.qdrant_collection = app_settings.qdrant_collection_products
                embedding.index_status = INDEX_STATUS_INDEXED
                embedding.index_error = None
                embedding.last_indexed_at = datetime.utcnow()
                db.add(embedding)
            except Exception as exc:
                failed += 1
                failed_product_ids.append(product.id)
                failed_embedding = current_embedding or product.embedding
                if failed_embedding is None:
                    fallback_embedding = ProductEmbedding(
                        product_id=product.id,
                        model_name=product_bundle.dense.descriptor.model_name,
                        embedding_text=product.name,
                        embedding_vector=None,
                        content_hash="pending-qdrant-index",
                    )
                    failed_embedding = fallback_embedding
                    db.add(fallback_embedding)

                assert failed_embedding is not None
                failed_embedding.qdrant_point_id = str(get_product_point_id(product.id))
                failed_embedding.qdrant_collection = app_settings.qdrant_collection_products
                failed_embedding.index_status = INDEX_STATUS_FAILED
                failed_embedding.index_error = f"{exc.__class__.__name__}: {exc}"
                failed_embedding.last_indexed_at = datetime.utcnow()
                db.add(failed_embedding)

        db.commit()
        return {
            "mode": mode,
            "indexed": indexed,
            "payload_updates": payload_updates,
            "deleted": deleted,
            "skipped": skipped,
            "failed": failed,
            "product_ids": processed_product_ids,
            "failed_product_ids": failed_product_ids,
            "collection_name": app_settings.qdrant_collection_products,
            "dense_model_name": product_bundle.dense.descriptor.model_name,
            "sparse_model_name": product_bundle.sparse.descriptor.model_name,
            "colbert_model_name": product_bundle.colbert.descriptor.model_name,
        }
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def retry_failed_product_indexing(
    db: Session,
    *,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle: EmbeddingProviderBundle | None = None,
) -> dict[str, object]:
    failed_product_ids = db.scalars(
        select(ProductEmbedding.product_id)
        .where(ProductEmbedding.index_status == INDEX_STATUS_FAILED)
        .order_by(ProductEmbedding.product_id.asc())
    ).all()
    return sync_products_to_qdrant(
        db,
        mode="retry_failed",
        product_ids=failed_product_ids,
        settings=settings,
        client=client,
        bundle=bundle,
    )


def delete_product_points(
    db: Session,
    *,
    product_ids: Iterable[int],
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    point_ids = [get_product_point_id(product_id) for product_id in sorted(set(product_ids))]

    try:
        if point_ids:
            qdrant_client.delete(
                app_settings.qdrant_collection_products,
                points_selector=point_ids,
                wait=True,
            )

        embeddings = db.scalars(
            select(ProductEmbedding).where(ProductEmbedding.product_id.in_(sorted(set(product_ids))))
        ).all()
        for embedding in embeddings:
            embedding.qdrant_point_id = str(get_product_point_id(embedding.product_id))
            embedding.qdrant_collection = app_settings.qdrant_collection_products
            embedding.index_status = INDEX_STATUS_INACTIVE
            embedding.index_error = None
            embedding.last_indexed_at = datetime.utcnow()
            db.add(embedding)

        db.commit()
        return {
            "deleted": len(point_ids),
            "product_ids": sorted(set(product_ids)),
            "collection_name": app_settings.qdrant_collection_products,
        }
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def get_product_index_status(
    db: Session,
    *,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    connection_status = get_qdrant_connection_status(app_settings)
    active_product_count = db.scalar(
        select(func.count()).select_from(Product).where(Product.status == 1)
    ) or 0
    indexed_product_count = db.scalar(
        select(func.count()).select_from(ProductEmbedding).where(
            ProductEmbedding.index_status == INDEX_STATUS_INDEXED
        )
    ) or 0
    failed_embeddings = db.scalars(
        select(ProductEmbedding)
        .where(ProductEmbedding.index_status == INDEX_STATUS_FAILED)
        .order_by(ProductEmbedding.product_id.asc())
    ).all()

    qdrant_points = 0
    collection_exists = app_settings.qdrant_collection_products in connection_status.collections
    if connection_status.available and collection_exists:
        qdrant_client = client or create_qdrant_client(app_settings)
        owns_client = client is None
        try:
            qdrant_points = qdrant_client.count(
                app_settings.qdrant_collection_products,
                exact=True,
            ).count
        finally:
            if owns_client:
                close = getattr(qdrant_client, "close", None)
                if callable(close):
                    close()

    return {
        "qdrant_available": connection_status.available,
        "collection_name": app_settings.qdrant_collection_products,
        "collection_exists": collection_exists,
        "active_product_count": active_product_count,
        "indexed_product_count": indexed_product_count,
        "qdrant_point_count": qdrant_points,
        "failed_products": [
            {
                "product_id": embedding.product_id,
                "error": embedding.index_error,
                "last_indexed_at": (
                    embedding.last_indexed_at.isoformat() if embedding.last_indexed_at else None
                ),
            }
            for embedding in failed_embeddings
        ],
    }


def resolve_product_ids(
    db: Session,
    mode: str,
    product_ids: Iterable[int] | None,
) -> list[int] | None:
    if product_ids is not None:
        normalized_ids = sorted(set(product_ids))
        return normalized_ids or []

    if mode == "retry_failed":
        failed_ids = db.scalars(
            select(ProductEmbedding.product_id)
            .where(ProductEmbedding.index_status == INDEX_STATUS_FAILED)
            .order_by(ProductEmbedding.product_id.asc())
        ).all()
        return failed_ids or []

    return None


def needs_incremental_sync(product: Product) -> bool:
    embedding = product.embedding
    if embedding is None:
        return is_product_indexable(product)
    if embedding.index_status in {INDEX_STATUS_FAILED, "pending"}:
        return True
    if embedding.last_indexed_at is None:
        return True
    if collect_latest_product_change(product) > embedding.last_indexed_at:
        return True
    if not is_product_indexable(product) and embedding.qdrant_point_id:
        return True
    return False


def collect_latest_product_change(product: Product) -> datetime:
    timestamps = [product.updated_at]
    if product.category is not None:
        timestamps.append(product.category.updated_at)
    timestamps.extend(tag.updated_at for tag in product.tags)
    for sku in product.skus:
        timestamps.append(sku.updated_at)
        if sku.inventory is not None:
            timestamps.append(sku.inventory.updated_at)
    return max(timestamps)


def delete_product_point(
    client: QdrantClient,
    *,
    collection_name: str,
    point_id: str,
) -> None:
    client.delete(
        collection_name,
        points_selector=[point_id],
        wait=True,
    )
