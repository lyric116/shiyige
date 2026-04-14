from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.membership import MemberLevel, PointAccount, PointLog
from backend.app.models.user import User, UserProfile
from backend.scripts.seed_base_data import seed_base_data


def test_member_levels_and_point_tables_seed_correctly() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        result = seed_base_data(session)

        member_levels = session.scalars(
            select(MemberLevel).order_by(MemberLevel.level_order.asc())
        ).all()
        assert result["member_levels"] == 4
        assert [level.code for level in member_levels] == ["bronze", "silver", "gold", "platinum"]
        assert member_levels[0].is_default is True
        assert member_levels[0].discount_rate == Decimal("0.98")
        assert member_levels[-1].points_rate == Decimal("2.00")

        user = User(
            email="member-seed@example.com",
            username="member-seed",
            password_hash="hash",
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name="member-seed")
        session.add(user)
        session.flush()

        account = PointAccount(
            user_id=user.id,
            member_level_id=member_levels[0].id,
            points_balance=120,
            lifetime_points=120,
            total_spent_amount=Decimal("99.00"),
        )
        session.add(account)
        session.flush()

        session.add(
            PointLog(
                point_account_id=account.id,
                change_type="seed_bonus",
                change_amount=120,
                balance_after=120,
                source_type="manual",
                source_id=user.id,
                remark="初始化会员积分",
                ext_json={"operator": "test"},
            )
        )
        session.commit()

        session.refresh(account)
        assert account.user.email == "member-seed@example.com"
        assert account.member_level.code == "bronze"
        assert account.point_logs[0].change_type == "seed_bonus"
        assert account.point_logs[0].balance_after == 120
