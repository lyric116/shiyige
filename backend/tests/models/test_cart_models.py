from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.cart import Cart, CartItem
from backend.app.models.product import Category, Inventory, Product, ProductSku
from backend.app.models.user import User, UserProfile


def test_cart_domain_models_create_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"cart", "cart_item"}.issubset(set(inspector.get_table_names()))


def test_cart_domain_models_support_user_cart_and_item_relations() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            email="cart@example.com",
            username="cart-user",
            password_hash="hashed-password",
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name="购物车用户")

        category = Category(name="礼盒", slug="gift-box", description="节令礼盒")
        product = Product(
            category=category,
            name="端午祈福礼盒",
            subtitle="节令送礼款",
            cover_url="https://example.com/gift-box.jpg",
            description="礼盒描述",
            culture_summary="礼盒文化背景",
            dynasty_style="节令风",
            craft_type="礼盒设计",
            festival_tag="端午",
            scene_tag="礼赠",
            status=1,
        )
        sku = ProductSku(
            sku_code="GIFT-001",
            name="默认款",
            specs_json={"default": True},
            price=Decimal("289.00"),
            member_price=Decimal("259.00"),
            is_default=True,
            is_active=True,
        )
        sku.inventory = Inventory(quantity=17)
        product.skus.append(sku)

        cart = Cart(user=user)
        cart.items.append(CartItem(product=product, sku=sku, quantity=2))

        session.add(cart)
        session.commit()
        session.refresh(cart)

        assert cart.user.username == "cart-user"
        assert len(cart.items) == 1
        assert cart.items[0].product.name == "端午祈福礼盒"
        assert cart.items[0].sku.sku_code == "GIFT-001"
        assert user.cart is not None
        assert user.cart.items[0].quantity == 2

        session.add(Cart(user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()
