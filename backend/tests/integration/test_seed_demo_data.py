from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.base import Base
from backend.app.models.membership import PointAccount
from backend.app.models.order import Order
from backend.app.models.recommendation import UserInterestProfile
from backend.app.models.user import User, UserBehaviorLog
from backend.scripts.seed_demo_data import DEMO_USER_EMAIL, seed_demo_data


def test_seed_demo_data_creates_demo_user_orders_points_and_interest_profile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        first_result = seed_demo_data(session)
        second_result = seed_demo_data(session)

        demo_user = session.scalar(
            select(User).options(selectinload(User.addresses)).where(User.email == DEMO_USER_EMAIL)
        )
        assert demo_user is not None
        assert demo_user.profile is not None
        assert demo_user.profile.display_name == "拾遗演示用户"
        assert len(demo_user.addresses) == 1
        assert demo_user.addresses[0].is_default is True

        orders = session.scalars(
            select(Order).where(Order.user_id == demo_user.id).order_by(Order.id.asc())
        ).all()
        assert len(orders) == 2
        assert {order.status for order in orders} == {"PAID", "PENDING_PAYMENT"}

        behavior_logs = session.scalars(
            select(UserBehaviorLog)
            .where(UserBehaviorLog.user_id == demo_user.id)
            .order_by(UserBehaviorLog.id.asc())
        ).all()
        assert [log.behavior_type for log in behavior_logs] == [
            "search",
            "search",
            "view_product",
            "add_to_cart",
            "create_order",
            "pay_order",
        ]

        point_account = session.scalar(
            select(PointAccount)
            .options(selectinload(PointAccount.member_level))
            .where(PointAccount.user_id == demo_user.id)
        )
        assert point_account is not None
        assert point_account.points_balance == 1808
        assert point_account.member_level is not None
        assert point_account.member_level.code == "silver"

        interest_profile = session.scalar(
            select(UserInterestProfile).where(UserInterestProfile.user_id == demo_user.id)
        )
        assert interest_profile is not None
        assert interest_profile.behavior_count == 6
        assert interest_profile.profile_text is not None
        assert interest_profile.embedding_vector is not None
        assert interest_profile.ext_json["top_terms"]

        assert first_result["demo_orders"] == 2
        assert first_result["behavior_logs"] == 6
        assert first_result["member_level"] == "silver"
        assert second_result["demo_orders"] == 2
        assert second_result["behavior_logs"] == 6
