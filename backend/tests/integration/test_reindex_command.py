from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models.base import Base
from backend.app.models.recommendation import ProductEmbedding
from backend.app.services.embedding import EmbeddingModelDescriptor, LocalHashEmbeddingProvider
from backend.scripts.reindex_embeddings import run_reindex_command
from backend.scripts.seed_base_data import seed_base_data


def build_test_provider(dimension: int = 12) -> LocalHashEmbeddingProvider:
    return LocalHashEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="local-hash-command",
            dimension=dimension,
            source="integration-test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )


def test_reindex_command_rebuilds_full_product_embedding_index() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = build_test_provider()
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with Session(engine) as session:
        seed_base_data(session)

    result = run_reindex_command(
        provider=provider,
        force=True,
        session_factory=session_factory,
    )

    assert result["indexed"] == 20
    assert result["skipped"] == 0
    assert result["model_name"] == "local-hash-command"

    with Session(engine) as session:
        embeddings = session.scalars(select(ProductEmbedding).order_by(ProductEmbedding.product_id)).all()

    assert len(embeddings) == 20
    assert len(embeddings[0].embedding_vector or []) == 12
