from backend.app.models.product import Category, Product, ProductTag
from backend.app.services.embedding_text import (
    build_embedding_content_hash,
    build_product_embedding_payload,
    build_product_embedding_text,
    build_product_embedding_texts,
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

    texts = build_product_embedding_texts(product)
    embedding_text = build_product_embedding_text(product)

    assert texts.title_text.splitlines() == [
        "商品名称: 明制襦裙",
        "副标题: 海棠红刺绣款",
    ]
    assert embedding_text.splitlines() == [
        "商品名称: 明制襦裙",
        "副标题: 海棠红刺绣款",
        "类目: 汉服",
        "文化说明: 体现礼制与审美并重的着装传统。",
        "朝代风格: 明制",
        "工艺: 刺绣",
        "使用场景: 出游",
        "标签: 明制 春日 汉服",
    ]
    expected_keywords = "明制襦裙 | 海棠红刺绣款 | 汉服 | 明制 | 刺绣 | 出游 | 明制 | 春日 | 汉服"
    assert texts.keyword_text == expected_keywords
    assert "商品描述: 适合春日出游与传统活动。" in texts.rerank_text
    assert f"关键词: {expected_keywords}" in texts.rerank_text


def test_build_product_embedding_payload_exposes_multi_text_fields_and_hash() -> None:
    category = Category(name="文创产品", slug="wenchuang", description="文化创意")
    product = Product(
        category=category,
        name="端午香囊礼盒",
        subtitle="艾草与织绣香囊组合",
        culture_summary="结合端午祈福与传统香事。",
        festival_tag="端午",
        scene_tag="送礼",
        status=1,
    )
    product.tags = [
        ProductTag(tag="香囊"),
        ProductTag(tag="节礼"),
    ]

    payload = build_product_embedding_payload(product)

    assert payload["embedding_text"] == payload["semantic_text"]
    assert payload["title_text"].splitlines()[0] == "商品名称: 端午香囊礼盒"
    assert "节令: 端午" in payload["semantic_text"]
    assert "礼赠属性: 端午 送礼 节礼 香囊" in payload["semantic_text"]
    assert payload["content_hash"]


def test_embedding_content_hash_is_stable_for_same_text_and_changes_when_content_changes() -> None:
    first_text = "商品名称: 明制襦裙\n类目: 汉服"
    second_text = "商品名称: 明制襦裙\n类目: 汉服"
    third_text = "商品名称: 点翠发簪\n类目: 饰品"

    assert build_embedding_content_hash(first_text) == build_embedding_content_hash(second_text)
    assert build_embedding_content_hash(first_text) != build_embedding_content_hash(third_text)
