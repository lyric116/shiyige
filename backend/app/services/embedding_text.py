from __future__ import annotations

import hashlib

from backend.app.models.product import Product


def normalize_text_piece(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def build_product_embedding_text(product: Product) -> str:
    tags = sorted(
        {
            normalized
            for normalized in (normalize_text_piece(tag.tag) for tag in product.tags)
            if normalized
        }
    )

    sections: list[str] = []
    field_pairs = [
        ("商品名称", normalize_text_piece(product.name)),
        ("类目", normalize_text_piece(product.category.name) if product.category else None),
        ("标签", " ".join(tags) if tags else None),
        ("描述", normalize_text_piece(product.description)),
        ("文化摘要", normalize_text_piece(product.culture_summary)),
        ("风格词", normalize_text_piece(product.dynasty_style)),
        ("场景词", normalize_text_piece(product.scene_tag)),
        ("工艺词", normalize_text_piece(product.craft_type)),
    ]

    for label, value in field_pairs:
        if value:
            sections.append(f"{label}: {value}")

    return "\n".join(sections)


def build_embedding_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_product_embedding_payload(product: Product) -> dict[str, str]:
    embedding_text = build_product_embedding_text(product)
    return {
        "embedding_text": embedding_text,
        "content_hash": build_embedding_content_hash(embedding_text),
    }
