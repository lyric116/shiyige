from decimal import Decimal

from backend.app.models.product import Inventory, Product, ProductSku
from backend.app.services.search_filters import (
    build_qdrant_search_filter,
    build_search_filters,
    product_matches_search_filters,
)


def build_product(*, stock: int = 6) -> Product:
    product = Product(
        category_id=1,
        name="宋风褙子套装",
        dynasty_style="宋制",
        craft_type="绣花",
        festival_tag="春夏",
        scene_tag="茶会",
        status=1,
    )
    sku = ProductSku(
        sku_code="SKU-TEST-001",
        name="默认款",
        price=Decimal("699.00"),
        member_price=Decimal("629.00"),
        is_default=True,
        is_active=True,
    )
    sku.inventory = Inventory(quantity=stock)
    product.skus.append(sku)
    return product


def test_build_qdrant_search_filter_contains_all_structured_conditions() -> None:
    filters = build_search_filters(
        category_id=3,
        min_price=Decimal("100"),
        max_price=Decimal("300"),
        dynasty_style="宋制",
        craft_type="刺绣",
        scene_tag="礼赠",
        festival_tag="端午",
        stock_only=True,
    )

    qdrant_filter = build_qdrant_search_filter(filters)
    conditions = {condition.key: condition for condition in qdrant_filter.must}

    assert sorted(conditions) == [
        "category_id",
        "craft_type",
        "dynasty_style",
        "festival_tag",
        "price_min",
        "scene_tag",
        "status",
        "stock_available",
    ]
    assert conditions["status"].match.value == "active"
    assert conditions["category_id"].match.value == 3
    assert conditions["price_min"].range.gte == 100.0
    assert conditions["price_min"].range.lte == 300.0
    assert conditions["dynasty_style"].match.value == "宋制"
    assert conditions["craft_type"].match.value == "刺绣"
    assert conditions["scene_tag"].match.value == "礼赠"
    assert conditions["festival_tag"].match.value == "端午"
    assert conditions["stock_available"].match.value is True


def test_product_matches_search_filters_respects_stock_and_structured_fields() -> None:
    product = build_product(stock=8)
    matching_filters = build_search_filters(
        category_id=1,
        min_price=Decimal("500"),
        max_price=Decimal("800"),
        dynasty_style="宋制",
        craft_type="绣花",
        scene_tag="茶会",
        festival_tag="春夏",
        stock_only=True,
    )
    out_of_stock_filters = build_search_filters(
        scene_tag="茶会",
        stock_only=False,
    )

    assert product_matches_search_filters(product, matching_filters) is True

    product.skus[0].inventory.quantity = 0
    assert product_matches_search_filters(product, matching_filters) is False
    assert product_matches_search_filters(product, out_of_stock_filters) is True
