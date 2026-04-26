from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.embedding import EmbeddingModelDescriptor, LocalHashEmbeddingProvider
from backend.app.services.recommendations import build_user_interest_profile
from backend.app.tasks.embedding_tasks import rebuild_all_product_embeddings
from backend.scripts.seed_base_data import seed_base_data


def build_test_provider(dimension: int = 16) -> LocalHashEmbeddingProvider:
    return LocalHashEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="local-hash-profile",
            dimension=dimension,
            source="integration-test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )


def test_user_interest_profile_differs_for_different_behavior_histories() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = build_test_provider()

    with Session(engine) as session:
        seed_base_data(session)
        rebuild_all_product_embeddings(session, provider=provider)

        hanfu_product = session.query(Product).filter(Product.name == "明制襦裙").one()
        accessory_product = session.query(Product).filter(Product.name == "点翠发簪").one()

        first_user = User(
            email="first@example.com",
            username="first-user",
            password_hash="hash",
            role="user",
            is_active=True,
        )
        first_user.profile = UserProfile(display_name="first-user")
        second_user = User(
            email="second@example.com",
            username="second-user",
            password_hash="hash",
            role="user",
            is_active=True,
        )
        second_user.profile = UserProfile(display_name="second-user")
        session.add_all([first_user, second_user])
        session.flush()

        session.add_all(
            [
                UserBehaviorLog(
                    user_id=first_user.id,
                    behavior_type="search",
                    target_type="search",
                    ext_json={"query": "春日汉服"},
                ),
                UserBehaviorLog(
                    user_id=first_user.id,
                    behavior_type="view_product",
                    target_id=hanfu_product.id,
                    target_type="product",
                ),
                UserBehaviorLog(
                    user_id=second_user.id,
                    behavior_type="search",
                    target_type="search",
                    ext_json={"query": "古风发簪"},
                ),
                UserBehaviorLog(
                    user_id=second_user.id,
                    behavior_type="view_product",
                    target_id=accessory_product.id,
                    target_type="product",
                ),
            ]
        )
        session.commit()

        first_profile = build_user_interest_profile(
            session, user_id=first_user.id, provider=provider
        )
        second_profile = build_user_interest_profile(
            session, user_id=second_user.id, provider=provider
        )
        first_profile_text = first_profile.profile_text
        second_profile_text = second_profile.profile_text
        first_top_terms = list(first_profile.ext_json["top_terms"])
        second_top_terms = list(second_profile.ext_json["top_terms"])

    assert first_profile_text != second_profile_text
    assert first_top_terms != second_top_terms
    assert "汉服" in first_top_terms
    assert any(term in second_top_terms for term in ("发簪", "饰品", "古风"))
