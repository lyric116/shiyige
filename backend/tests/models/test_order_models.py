from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.order import Order, OrderItem, PaymentRecord
from backend.app.models.product import Category, Inventory, Product, ProductSku
from backend.app.models.user import User, UserProfile


def test_order_domain_models_create_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"orders", "order_item", "payment_record"}.issubset(set(inspector.get_table_names()))


def test_order_models_support_items_payment_records_and_snapshots() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            email="order@example.com",
            username="order-user",
            password_hash="hashed-password",
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name="订单用户")

        category = Category(name="文创", slug="wenchuang", description="文创类目")
        product = Product(
            category=category,
            name="故宫宫廷香囊",
            subtitle="端午限定",
            cover_url="https://example.com/sachet.jpg",
            description="商品描述",
            culture_summary="文化介绍",
            dynasty_style="宫廷风",
            craft_type="刺绣",
            festival_tag="端午",
            scene_tag="赠礼",
            status=1,
        )
        sku = ProductSku(
            sku_code="ORDER-001",
            name="默认款",
            specs_json={"default": True},
            price=Decimal("129.00"),
            member_price=Decimal("109.00"),
            is_default=True,
            is_active=True,
        )
        sku.inventory = Inventory(quantity=30)
        product.skus.append(sku)

        order = Order(
            order_no="SYG202604140001",
            user=user,
            status="PENDING_PAYMENT",
            goods_amount=Decimal("258.00"),
            shipping_amount=Decimal("10.00"),
            payable_amount=Decimal("268.00"),
            recipient_name="张三",
            recipient_phone="13800138000",
            recipient_region="北京市东城区",
            recipient_detail_address="景山前街 4 号",
            recipient_postal_code="100010",
            buyer_note="请轻拿轻放",
            idempotency_key="order-key-001",
        )
        order.items.append(
            OrderItem(
                product=product,
                sku=sku,
                product_name=product.name,
                sku_name=sku.name,
                quantity=2,
                unit_price=Decimal("129.00"),
                unit_member_price=Decimal("109.00"),
                subtotal_amount=Decimal("258.00"),
            )
        )
        order.payment_records.append(
            PaymentRecord(
                payment_no="PAY202604140001",
                payment_method="alipay",
                amount=Decimal("268.00"),
                status="PENDING",
            )
        )

        session.add(order)
        session.commit()
        session.refresh(order)

        assert order.user.username == "order-user"
        assert len(order.items) == 1
        assert order.items[0].product_name == "故宫宫廷香囊"
        assert order.items[0].sku.sku_code == "ORDER-001"
        assert order.payable_amount == Decimal("268.00")
        assert order.payment_records[0].payment_no == "PAY202604140001"
