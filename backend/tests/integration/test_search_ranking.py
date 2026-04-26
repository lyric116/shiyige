from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.services.embedding import EmbeddingModelDescriptor, LocalHashEmbeddingProvider
from backend.app.services.vector_search import semantic_search_products
from backend.app.tasks.embedding_tasks import rebuild_all_product_embeddings
from backend.scripts.seed_base_data import seed_base_data


def build_test_provider(dimension: int = 16) -> LocalHashEmbeddingProvider:
    return LocalHashEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="local-hash-semantic",
            dimension=dimension,
            source="integration-test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )


def test_semantic_search_ranking_prefers_matching_scene_and_respects_filters() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = build_test_provider()

    with Session(engine) as session:
        seed_base_data(session)
        rebuild_all_product_embeddings(session, provider=provider)

        hanfu_results = semantic_search_products(
            session,
            query="适合春日出游的素雅汉服",
            limit=3,
            provider=provider,
        )
        accessory_results = semantic_search_products(
            session,
            query="古风发簪饰品",
            limit=3,
            max_price=Decimal("150"),
            provider=provider,
        )

    assert hanfu_results[0].product.name == "明制襦裙"
    assert "汉服" in hanfu_results[0].reason
    assert accessory_results[0].product.name == "点翠发簪"
    assert all(
        (result.product.lowest_price or Decimal("0")) <= Decimal("150")
        for result in accessory_results
    )
