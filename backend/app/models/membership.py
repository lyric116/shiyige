from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin


class MemberLevel(TimestampMixin, Base):
    __tablename__ = "member_level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    level_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    min_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    points_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    point_accounts: Mapped[list[PointAccount]] = relationship(back_populates="member_level")


class PointAccount(TimestampMixin, Base):
    __tablename__ = "point_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    member_level_id: Mapped[int] = mapped_column(
        ForeignKey("member_level.id"),
        nullable=False,
        index=True,
    )
    points_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="point_account")
    member_level: Mapped[MemberLevel] = relationship(back_populates="point_accounts")
    point_logs: Mapped[list[PointLog]] = relationship(
        back_populates="point_account",
        cascade="all, delete-orphan",
    )


class PointLog(Base):
    __tablename__ = "point_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    point_account_id: Mapped[int] = mapped_column(
        ForeignKey("point_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    change_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    ext_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    point_account: Mapped[PointAccount] = relationship(back_populates="point_logs")
