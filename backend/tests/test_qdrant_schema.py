import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.recommendation import ProductEmbedding, UserInterestProfile
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.tasks.qdrant_schema_tasks import ensure_product_collection


def build_settings(collection_name: str) -> AppSettings:
    return AppSettings(
        vector_db_provider="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection_products=collection_name,
        qdrant_collection_users="schema-test-users",
        qdrant_collection_cf="schema-test-cf",
    )


def test_product_collection_schema_is_initialized_idempotently() -> None:
    settings = build_settings("shiyige_products_schema_test")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for schema test")

    client = create_qdrant_client(settings)
    try:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)

        first_run = ensure_product_collection(client=client, settings=settings)
        second_run = ensure_product_collection(client=client, settings=settings)
        collection_info = client.get_collection(settings.qdrant_collection_products)

        assert first_run["created"] is True
        assert second_run["created"] is False
        assert first_run["named_vectors"] == ["colbert", "dense"]
        assert first_run["sparse_vectors"] == ["sparse"]
        assert sorted(collection_info.config.params.vectors.keys()) == ["colbert", "dense"]
        assert sorted(collection_info.config.params.sparse_vectors.keys()) == ["sparse"]
        assert "status" in collection_info.payload_schema
        assert "category_id" in collection_info.payload_schema
        assert "embedding_model_version" in collection_info.payload_schema
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()


def test_recommendation_tables_expose_qdrant_sync_metadata_columns() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        product_columns = ProductEmbedding.__table__.columns.keys()
        profile_columns = UserInterestProfile.__table__.columns.keys()

        assert "qdrant_point_id" in product_columns
        assert "qdrant_collection" in product_columns
        assert "index_status" in product_columns
        assert "index_error" in product_columns
        assert "qdrant_user_point_id" in profile_columns
        assert "profile_version" in profile_columns
        assert "last_synced_at" in profile_columns
        session.commit()
