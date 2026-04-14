from backend.app.models.product import Category, Product, ProductTag
from backend.app.services.embedding_text import (
    build_embedding_content_hash,
    build_product_embedding_text,
)


def test_build_product_embedding_text_uses_fixed_rule_and_stable_order() -> None:
    category = Category(name="汉服", slug="hanfu", description="传统汉服")
    product = Product(
        category=category,
        name="明制襦裙",
        subtitle="海棠红刺绣款",
        description="适合春日出游与传统活动。",
        culture_summary="体现礼制与审美并重的着装传统。",
        dynasty_style="明制",
        craft_type="刺绣",
        scene_tag="出游",
        status=1,
    )
    product.tags = [
        ProductTag(tag="春日"),
        ProductTag(tag="汉服"),
        ProductTag(tag="明制"),
    ]

    embedding_text = build_product_embedding_text(product)

    assert embedding_text.splitlines() == [
        "商品名称: 明制襦裙",
        "类目: 汉服",
        "标签: 明制 春日 汉服",
        "描述: 适合春日出游与传统活动。",
        "文化摘要: 体现礼制与审美并重的着装传统。",
        "风格词: 明制",
        "场景词: 出游",
        "工艺词: 刺绣",
    ]


def test_embedding_content_hash_is_stable_for_same_text_and_changes_when_content_changes() -> None:
    first_text = "商品名称: 明制襦裙\n类目: 汉服"
    second_text = "商品名称: 明制襦裙\n类目: 汉服"
    third_text = "商品名称: 点翠发簪\n类目: 饰品"

    assert build_embedding_content_hash(first_text) == build_embedding_content_hash(second_text)
    assert build_embedding_content_hash(first_text) != build_embedding_content_hash(third_text)
