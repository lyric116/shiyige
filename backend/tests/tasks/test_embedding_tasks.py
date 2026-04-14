from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.recommendation import ProductEmbedding
from backend.app.services.embedding import EmbeddingModelDescriptor, LocalHashEmbeddingProvider
from backend.app.tasks.embedding_tasks import reindex_changed_product_embeddings, rebuild_all_product_embeddings
from backend.scripts.seed_base_data import seed_base_data


def build_test_provider(dimension: int = 8) -> LocalHashEmbeddingProvider:
    return LocalHashEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="local-hash-test",
            dimension=dimension,
            source="unit-test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )


def test_rebuild_all_product_embeddings_creates_vectors_for_catalog() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = build_test_provider(8)

    with Session(engine) as session:
        seed_base_data(session)
        result = rebuild_all_product_embeddings(session, provider=provider)

        assert result["indexed"] == 20
        assert result["skipped"] == 0

        embeddings = session.scalars(select(ProductEmbedding).order_by(ProductEmbedding.product_id)).all()
        assert len(embeddings) == 20
        assert embeddings[0].model_name == "local-hash-test"
        assert len(embeddings[0].embedding_vector or []) == 8
        assert embeddings[0].embedding_text
        assert embeddings[0].content_hash


def test_reindex_changed_product_embeddings_skips_unchanged_and_updates_changed_products() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = build_test_provider(8)

    with Session(engine) as session:
        seed_base_data(session)
        first_run = rebuild_all_product_embeddings(session, provider=provider)
        assert first_run["indexed"] == 20

        second_run = reindex_changed_product_embeddings(session, provider=provider)
        assert second_run["indexed"] == 0
        assert second_run["skipped"] == 20

        product = session.scalar(select(Product).where(Product.name == "故宫宫廷香囊"))
        assert product is not None
        original_hash = product.embedding.content_hash
        product.description = "更新后的香囊描述，用于验证增量重建。"
        session.add(product)
        session.commit()

        third_run = reindex_changed_product_embeddings(session, provider=provider)
        assert third_run["indexed"] == 1
        assert third_run["product_ids"] == [product.id]

        session.refresh(product)
        assert product.embedding.content_hash != original_hash
