from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Category, Inventory, Product, ProductMedia, ProductSku, ProductTag


def test_product_domain_models_create_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"category", "product", "product_sku", "product_media", "product_tag", "inventory"}.issubset(
        set(inspector.get_table_names())
    )


def test_product_model_supports_default_sku_lowest_price_and_inventory() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        category = Category(name="汉服", slug="hanfu", description="汉服类目")
        product = Product(
            category=category,
            name="明制襦裙",
            subtitle="春日限定",
            cover_url="https://example.com/hanfu-cover.jpg",
            description="商品描述",
            culture_summary="文化简介",
            dynasty_style="明制",
            craft_type="刺绣",
            festival_tag="春日",
            scene_tag="出游",
            status=1,
        )
        default_sku = ProductSku(
            sku_code="HANFU-001-DEFAULT",
            name="默认款",
            specs_json={"color": "海棠红", "size": "M"},
            price=Decimal("899.00"),
            member_price=Decimal("799.00"),
            is_default=True,
            is_active=True,
        )
        default_sku.inventory = Inventory(quantity=12)
        alt_sku = ProductSku(
            sku_code="HANFU-001-L",
            name="大码款",
            specs_json={"color": "海棠红", "size": "L"},
            price=Decimal("959.00"),
            member_price=Decimal("859.00"),
            is_default=False,
            is_active=True,
        )
        alt_sku.inventory = Inventory(quantity=5)
        product.skus.extend([default_sku, alt_sku])
        product.media_items.append(ProductMedia(media_type="image", url="https://example.com/hanfu-1.jpg"))
        product.tags.append(ProductTag(tag="汉服"))
        product.tags.append(ProductTag(tag="明制"))

        session.add(product)
        session.commit()
        session.refresh(product)

        assert product.default_sku is not None
        assert product.default_sku.sku_code == "HANFU-001-DEFAULT"
        assert product.lowest_price == Decimal("899.00")
        assert product.default_sku.inventory is not None
        assert product.default_sku.inventory.quantity == 12
        assert len(product.media_items) == 1
        assert {tag.tag for tag in product.tags} == {"汉服", "明制"}
