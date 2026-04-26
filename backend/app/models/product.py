from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.cart import CartItem
    from backend.app.models.order import OrderItem
    from backend.app.models.recommendation import ProductEmbedding
    from backend.app.models.review import Review


class Category(TimestampMixin, Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(TimestampMixin, Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    culture_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    dynasty_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    craft_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    festival_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scene_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    category: Mapped["Category"] = relationship(back_populates="products")
    skus: Mapped[list["ProductSku"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    media_items: Mapped[list["ProductMedia"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["ProductTag"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    embedding: Mapped["ProductEmbedding | None"] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def default_sku(self) -> ProductSku | None:
        if not self.skus:
            return None
        return next((sku for sku in self.skus if sku.is_default), self.skus[0])

    @property
    def lowest_price(self) -> Decimal | None:
        prices = [sku.price for sku in self.skus]
        return min(prices) if prices else None


class ProductSku(TimestampMixin, Base):
    __tablename__ = "product_sku"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    sku_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    specs_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    member_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="skus")
    inventory: Mapped["Inventory | None"] = relationship(
        back_populates="sku",
        cascade="all, delete-orphan",
        uselist=False,
    )
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="sku")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="sku")


class ProductMedia(TimestampMixin, Base):
    __tablename__ = "product_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    media_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="media_items")


class ProductTag(TimestampMixin, Base):
    __tablename__ = "product_tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    product: Mapped["Product"] = relationship(back_populates="tags")


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("product_sku.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sku: Mapped["ProductSku"] = relationship(back_populates="inventory")
