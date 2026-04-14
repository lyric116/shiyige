from sqlalchemy import create_engine, inspect

from backend.app.models.base import Base
from backend.app.models.user import User, UserAddress, UserBehaviorLog, UserProfile


def test_user_domain_models_create_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"users", "user_profile", "user_address", "user_behavior_log"}.issubset(
        set(inspector.get_table_names())
    )


def test_user_model_exposes_core_columns_and_relationships() -> None:
    user_columns = set(User.__table__.columns.keys())
    profile_columns = set(UserProfile.__table__.columns.keys())
    address_columns = set(UserAddress.__table__.columns.keys())
    behavior_columns = set(UserBehaviorLog.__table__.columns.keys())

    assert {"email", "username", "password_hash", "role", "is_active"}.issubset(user_columns)
    assert {"user_id", "phone", "birthday", "avatar_url"}.issubset(profile_columns)
    assert {"recipient_name", "region", "detail_address", "is_default"}.issubset(address_columns)
    assert {"behavior_type", "target_id", "target_type", "ext_json"}.issubset(behavior_columns)

    assert User.profile.property.uselist is False
    assert User.addresses.property.uselist is True
    assert User.behavior_logs.property.uselist is True
