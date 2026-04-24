from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qdrant_client import models

from backend.app.models.product import Product
from backend.app.services.embedding_text import normalize_text_piece
from backend.app.services.product_index_document import product_has_available_stock


@dataclass(frozen=True, slots=True)
class SearchFilters:
    category_id: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    dynasty_style: str | None = None
    craft_type: str | None = None
    scene_tag: str | None = None
    festival_tag: str | None = None
    stock_only: bool = True


def build_search_filters(
    *,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    dynasty_style: str | None = None,
    craft_type: str | None = None,
    scene_tag: str | None = None,
    festival_tag: str | None = None,
    stock_only: bool = True,
) -> SearchFilters:
    return SearchFilters(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        dynasty_style=normalize_filter_value(dynasty_style),
        craft_type=normalize_filter_value(craft_type),
        scene_tag=normalize_filter_value(scene_tag),
        festival_tag=normalize_filter_value(festival_tag),
        stock_only=stock_only,
    )


def build_qdrant_search_filter(filters: SearchFilters) -> models.Filter:
    must_conditions: list[models.Condition] = [
        models.FieldCondition(
            key="status",
            match=models.MatchValue(value="active"),
        )
    ]

    if filters.category_id is not None:
        must_conditions.append(
            models.FieldCondition(
                key="category_id",
                match=models.MatchValue(value=filters.category_id),
            )
        )
    if filters.min_price is not None or filters.max_price is not None:
        must_conditions.append(
            models.FieldCondition(
                key="price_min",
                range=models.Range(
                    gte=float(filters.min_price) if filters.min_price is not None else None,
                    lte=float(filters.max_price) if filters.max_price is not None else None,
                ),
            )
        )
    if filters.dynasty_style:
        must_conditions.append(
            models.FieldCondition(
                key="dynasty_style",
                match=models.MatchValue(value=filters.dynasty_style),
            )
        )
    if filters.craft_type:
        must_conditions.append(
            models.FieldCondition(
                key="craft_type",
                match=models.MatchValue(value=filters.craft_type),
            )
        )
    if filters.scene_tag:
        must_conditions.append(
            models.FieldCondition(
                key="scene_tag",
                match=models.MatchValue(value=filters.scene_tag),
            )
        )
    if filters.festival_tag:
        must_conditions.append(
            models.FieldCondition(
                key="festival_tag",
                match=models.MatchValue(value=filters.festival_tag),
            )
        )
    if filters.stock_only:
        must_conditions.append(
            models.FieldCondition(
                key="stock_available",
                match=models.MatchValue(value=True),
            )
        )

    return models.Filter(must=must_conditions)


def product_matches_search_filters(product: Product, filters: SearchFilters) -> bool:
    if product.status != 1:
        return False
    if filters.category_id is not None and product.category_id != filters.category_id:
        return False

    lowest_price = product.lowest_price
    if filters.min_price is not None and (lowest_price is None or lowest_price < filters.min_price):
        return False
    if filters.max_price is not None and (lowest_price is None or lowest_price > filters.max_price):
        return False

    if (
        filters.dynasty_style
        and normalize_filter_value(product.dynasty_style) != filters.dynasty_style
    ):
        return False
    if filters.craft_type and normalize_filter_value(product.craft_type) != filters.craft_type:
        return False
    if filters.scene_tag and normalize_filter_value(product.scene_tag) != filters.scene_tag:
        return False
    if (
        filters.festival_tag
        and normalize_filter_value(product.festival_tag) != filters.festival_tag
    ):
        return False
    if filters.stock_only and not product_has_available_stock(product):
        return False
    return True


def serialize_search_filters(filters: SearchFilters) -> dict[str, object]:
    return {
        "category_id": filters.category_id,
        "min_price": str(filters.min_price) if filters.min_price is not None else None,
        "max_price": str(filters.max_price) if filters.max_price is not None else None,
        "dynasty_style": filters.dynasty_style,
        "craft_type": filters.craft_type,
        "scene_tag": filters.scene_tag,
        "festival_tag": filters.festival_tag,
        "stock_only": filters.stock_only,
    }


def normalize_filter_value(value: str | None) -> str | None:
    return normalize_text_piece(value)
