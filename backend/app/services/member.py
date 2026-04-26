from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.membership import MemberLevel, PointAccount, PointLog
from backend.app.models.order import Order, PaymentRecord


def serialize_member_level(level: MemberLevel, *, is_current: bool = False) -> dict[str, object]:
    return {
        "id": level.id,
        "code": level.code,
        "name": level.name,
        "level_order": level.level_order,
        "min_points": level.min_points,
        "discount_rate": level.discount_rate,
        "points_rate": level.points_rate,
        "description": level.description,
        "is_default": level.is_default,
        "is_current": is_current,
    }


def serialize_point_log(log: PointLog) -> dict[str, object]:
    return {
        "id": log.id,
        "change_type": log.change_type,
        "change_amount": log.change_amount,
        "balance_after": log.balance_after,
        "source_type": log.source_type,
        "source_id": log.source_id,
        "remark": log.remark,
        "ext_json": log.ext_json,
        "created_at": log.created_at.isoformat(),
    }


def list_member_levels(db: Session) -> list[MemberLevel]:
    return db.scalars(select(MemberLevel).order_by(MemberLevel.level_order.asc())).all()


def get_default_member_level(db: Session) -> MemberLevel:
    level = db.scalar(
        select(MemberLevel)
        .where(MemberLevel.is_default.is_(True))
        .order_by(MemberLevel.level_order.asc())
    )
    if level is None:
        level = db.scalar(select(MemberLevel).order_by(MemberLevel.level_order.asc()))
    if level is None:
        raise RuntimeError("member levels are not seeded")
    return level


def resolve_member_level(db: Session, points_balance: int) -> MemberLevel:
    level = db.scalar(
        select(MemberLevel)
        .where(MemberLevel.min_points <= points_balance)
        .order_by(MemberLevel.min_points.desc(), MemberLevel.level_order.desc())
    )
    if level is None:
        level = get_default_member_level(db)
    return level


def get_point_account(
    db: Session, user_id: int, *, include_logs: bool = False
) -> PointAccount | None:
    options = [selectinload(PointAccount.member_level)]
    if include_logs:
        options.append(selectinload(PointAccount.point_logs))
    return db.scalar(select(PointAccount).options(*options).where(PointAccount.user_id == user_id))


def ensure_point_account(db: Session, user_id: int) -> PointAccount:
    account = get_point_account(db, user_id)
    if account is not None:
        return account

    default_level = get_default_member_level(db)
    account = PointAccount(
        user_id=user_id,
        member_level=default_level,
        points_balance=0,
        lifetime_points=0,
        total_spent_amount=Decimal("0.00"),
    )
    db.add(account)
    db.flush()
    return account


def build_next_level(levels: list[MemberLevel], points_balance: int) -> dict[str, object] | None:
    for level in levels:
        if level.min_points > points_balance:
            return {
                "id": level.id,
                "code": level.code,
                "name": level.name,
                "min_points": level.min_points,
                "remaining_points": level.min_points - points_balance,
            }
    return None


def build_member_summary(account: PointAccount, levels: list[MemberLevel]) -> dict[str, object]:
    current_level = account.member_level
    assert current_level is not None
    next_level = build_next_level(levels, account.points_balance)
    progress_percent = (
        100.0
        if next_level is None
        else round((account.points_balance / next_level["min_points"]) * 100, 2)
    )
    return {
        "points_balance": account.points_balance,
        "lifetime_points": account.lifetime_points,
        "total_spent_amount": account.total_spent_amount,
        "current_level": serialize_member_level(current_level, is_current=True),
        "next_level": next_level,
        "progress_percent": progress_percent,
    }


def build_member_benefits(level: MemberLevel) -> list[str]:
    discount_text = f"购物享{int(Decimal(level.discount_rate) * 100)}折"
    points_text = f"消费享{Decimal(level.points_rate).normalize()}倍积分"
    return [discount_text, points_text]


def accrue_points_for_paid_order(
    db: Session,
    *,
    user_id: int,
    order: Order,
    payment_record: PaymentRecord | None = None,
) -> tuple[PointAccount, PointLog, int]:
    account = ensure_point_account(db, user_id)
    current_level = account.member_level
    assert current_level is not None

    points_earned = int(
        (Decimal(order.payable_amount) * Decimal(current_level.points_rate)).quantize(
            Decimal("1"),
            rounding=ROUND_DOWN,
        )
    )
    account.points_balance += points_earned
    account.lifetime_points += points_earned
    account.total_spent_amount = Decimal(account.total_spent_amount) + Decimal(order.payable_amount)
    account.member_level = resolve_member_level(db, account.points_balance)
    db.add(account)
    db.flush()

    point_log = PointLog(
        point_account_id=account.id,
        change_type="order_pay",
        change_amount=points_earned,
        balance_after=account.points_balance,
        source_type="order",
        source_id=order.id,
        remark=f"订单 {order.order_no} 支付获得积分",
        ext_json={
            "order_no": order.order_no,
            "payable_amount": str(order.payable_amount),
            "payment_no": payment_record.payment_no if payment_record else None,
            "points_rate": str(current_level.points_rate),
        },
    )
    db.add(point_log)
    db.flush()
    return account, point_log, points_earned
