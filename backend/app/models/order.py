from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING_PAYMENT", nullable=False)
    goods_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_region: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_detail_address: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    buyer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payment_records: Mapped[list[PaymentRecord]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("product_sku.id"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_member_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")
    sku: Mapped[ProductSku] = relationship(back_populates="order_items")


class PaymentRecord(TimestampMixin, Base):
    __tablename__ = "payment_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order] = relationship(back_populates="payment_records")
