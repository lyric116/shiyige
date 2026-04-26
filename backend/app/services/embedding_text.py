from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal

from backend.app.models.product import Product


@dataclass(frozen=True)
class ProductEmbeddingTextSet:
    title_text: str
    semantic_text: str
    keyword_text: str
    rerank_text: str


def normalize_text_piece(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def build_product_embedding_texts(product: Product) -> ProductEmbeddingTextSet:
    normalized_tags = sorted(
        {
            normalized
            for normalized in (normalize_text_piece(tag.tag) for tag in product.tags)
            if normalized
        }
    )
    category_name = normalize_text_piece(product.category.name) if product.category else None
    subtitle = normalize_text_piece(product.subtitle)
    description = normalize_text_piece(product.description)
    culture_summary = normalize_text_piece(product.culture_summary)
    dynasty_style = normalize_text_piece(product.dynasty_style)
    craft_type = normalize_text_piece(product.craft_type)
    festival_tag = normalize_text_piece(product.festival_tag)
    scene_tag = normalize_text_piece(product.scene_tag)
    price_band = build_price_band_text(product.lowest_price)
    gift_attribute = build_gift_attribute_text(
        tags=normalized_tags,
        festival_tag=festival_tag,
        scene_tag=scene_tag,
    )
    pairing_attribute = build_pairing_attribute_text(normalized_tags)

    title_lines = [
        line
        for line in [
            format_section("商品名称", normalize_text_piece(product.name)),
            format_section("副标题", subtitle),
        ]
        if line
    ]
    semantic_lines = [
        line
        for line in [
            format_section("商品名称", normalize_text_piece(product.name)),
            format_section("副标题", subtitle),
            format_section("类目", category_name),
            format_section("文化说明", culture_summary),
            format_section("朝代风格", dynasty_style),
            format_section("工艺", craft_type),
            format_section("节令", festival_tag),
            format_section("使用场景", scene_tag),
            format_section("标签", " ".join(normalized_tags) if normalized_tags else None),
            format_section("价格带", price_band),
            format_section("礼赠属性", gift_attribute),
            format_section("搭配属性", pairing_attribute),
        ]
        if line
    ]
    keyword_tokens = [
        token
        for token in [
            normalize_text_piece(product.name),
            subtitle,
            category_name,
            dynasty_style,
            craft_type,
            festival_tag,
            scene_tag,
            price_band,
            gift_attribute,
            pairing_attribute,
        ]
        if token
    ]
    keyword_tokens.extend(normalized_tags)
    keyword_text = " | ".join(keyword_tokens)
    rerank_lines = [
        *title_lines,
        *[
            line
            for line in [
                format_section("商品描述", description),
                format_section("文化说明", culture_summary),
                format_section("朝代风格", dynasty_style),
                format_section("工艺", craft_type),
                format_section("节令", festival_tag),
                format_section("使用场景", scene_tag),
                format_section("标签", " ".join(normalized_tags) if normalized_tags else None),
                format_section("价格带", price_band),
                format_section("礼赠属性", gift_attribute),
                format_section("搭配属性", pairing_attribute),
                format_section("关键词", keyword_text),
            ]
            if line
        ],
    ]

    return ProductEmbeddingTextSet(
        title_text="\n".join(title_lines),
        semantic_text="\n".join(semantic_lines),
        keyword_text=keyword_text,
        rerank_text="\n".join(rerank_lines),
    )


def format_section(label: str, value: str | None) -> str | None:
    if not value:
        return None
    return f"{label}: {value}"


def build_price_band_text(price: Decimal | None) -> str | None:
    if price is None:
        return None
    if price < Decimal("100"):
        return "百元内入门礼物"
    if price < Decimal("300"):
        return "百元到三百元雅致礼物"
    if price < Decimal("800"):
        return "中高价收藏级文创"
    return "高价收藏礼赠"


def build_gift_attribute_text(
    *,
    tags: list[str],
    festival_tag: str | None,
    scene_tag: str | None,
) -> str | None:
    gift_terms: list[str] = []
    if festival_tag:
        gift_terms.append(festival_tag)
    if scene_tag and any(keyword in scene_tag for keyword in ("送礼", "礼赠", "拜访", "节庆")):
        gift_terms.append(scene_tag)
    gift_tags = [
        tag for tag in tags if any(keyword in tag for keyword in ("礼", "赠", "祝福", "香囊"))
    ]
    gift_terms.extend(gift_tags)
    if not gift_terms:
        return None
    return " ".join(dict.fromkeys(gift_terms))


def build_pairing_attribute_text(tags: list[str]) -> str | None:
    pairing_tags = [
        tag
        for tag in tags
        if any(keyword in tag for keyword in ("套装", "搭配", "成套", "系列", "对佩"))
    ]
    if not pairing_tags:
        return None
    return " ".join(dict.fromkeys(pairing_tags))


def build_product_embedding_text(product: Product) -> str:
    return build_product_embedding_texts(product).semantic_text


def build_embedding_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_product_embedding_payload(product: Product) -> dict[str, str]:
    texts = build_product_embedding_texts(product)
    hash_source = "\n".join(
        [
            f"title_text={texts.title_text}",
            f"semantic_text={texts.semantic_text}",
            f"keyword_text={texts.keyword_text}",
            f"rerank_text={texts.rerank_text}",
        ]
    )
    return {
        "title_text": texts.title_text,
        "semantic_text": texts.semantic_text,
        "keyword_text": texts.keyword_text,
        "rerank_text": texts.rerank_text,
        "embedding_text": texts.semantic_text,
        "content_hash": build_embedding_content_hash(hash_source),
    }
