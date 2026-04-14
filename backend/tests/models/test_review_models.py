from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.order import Order
from backend.app.models.product import Category, Product
from backend.app.models.review import Review, ReviewImage
from backend.app.models.user import User, UserProfile


def test_review_models_create_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"review", "review_image"}.issubset(set(inspector.get_table_names()))


def test_review_model_supports_images_and_user_product_relationships() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        category = Category(name="饰品", slug="accessory", description="饰品类目")
        product = Product(
            category=category,
            name="点翠发簪",
            subtitle="测试商品",
            cover_url="https://example.com/cover.jpg",
            description="商品描述",
            culture_summary="文化简介",
            dynasty_style="宫廷风",
            craft_type="金属镶嵌",
            festival_tag="拍照",
            scene_tag="穿搭",
            status=1,
        )
        user = User(
            email="review-model@example.com",
            username="review-model",
            password_hash="hash",
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name="评测用户")
        order = Order(
            order_no="SYGREVIEWMODEL001",
            user=user,
            status="PAID",
            goods_amount=Decimal("129.00"),
            shipping_amount=Decimal("10.00"),
            payable_amount=Decimal("139.00"),
            recipient_name="张三",
            recipient_phone="13800138000",
            recipient_region="北京市东城区",
            recipient_detail_address="景山前街 4 号",
            recipient_postal_code="100010",
        )
        session.add_all([product, user, order])
        session.flush()
        review = Review(
            user=user,
            product=product,
            order_id=order.id,
            rating=5,
            content="很喜欢，做工细致。",
            is_anonymous=False,
        )
        review.images.append(
            ReviewImage(
                image_url="https://example.com/review-1.jpg",
                sort_order=1,
            )
        )

        session.add(review)
        session.commit()
        session.refresh(review)

        assert review.user.username == "review-model"
        assert review.product.name == "点翠发簪"
        assert review.images[0].image_url == "https://example.com/review-1.jpg"
