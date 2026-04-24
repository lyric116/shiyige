from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.products import serialize_product_list_item
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.product import Category, Product, ProductTag
from backend.app.schemas.search import SemanticSearchRequest
from backend.app.services.behavior import (
    BEHAVIOR_SEARCH,
    get_optional_user_from_request,
    log_behavior,
)
from backend.app.services.cache import (
    SEARCH_SUGGESTIONS_CACHE_TTL,
    build_cache_key,
    get_cached_json,
    invalidate_recommendation_cache_for_user,
    set_cached_json,
)
from backend.app.services.search_filters import build_search_filters, serialize_search_filters
from backend.app.services.vector_search import semantic_search_products
from backend.app.services.vector_store import build_runtime_marker

router = APIRouter(tags=["search"])


def normalize_keyword(query: str) -> str:
    return query.strip()


def build_search_query(keyword: str):
    return (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.tags),
        )
        .join(Category, Product.category_id == Category.id)
        .outerjoin(Product.tags)
        .where(
            or_(
                Product.name.contains(keyword),
                Product.subtitle.contains(keyword),
                Product.culture_summary.contains(keyword),
                Category.name.contains(keyword),
                ProductTag.tag.contains(keyword),
            )
        )
        .distinct()
    )


def rank_product(product: Product, keyword: str) -> tuple[int, int]:
    normalized_keyword = keyword.lower()
    name = (product.name or "").lower()
    subtitle = (product.subtitle or "").lower()
    category_name = (product.category.name if product.category else "").lower()
    tags = " ".join(tag.tag for tag in product.tags).lower()
    culture_summary = (product.culture_summary or "").lower()

    if normalized_keyword in name:
        return (0, product.id)
    if normalized_keyword in subtitle:
        return (1, product.id)
    if normalized_keyword in tags:
        return (2, product.id)
    if normalized_keyword in category_name:
        return (3, product.id)
    if normalized_keyword in culture_summary:
        return (4, product.id)
    return (5, product.id)


def filter_and_sort_products(
    products: list[Product],
    *,
    min_price: Decimal | None,
    max_price: Decimal | None,
    sort: str,
    keyword: str,
) -> list[Product]:
    filtered_products: list[Product] = []
    for product in products:
        lowest_price = product.lowest_price
        if min_price is not None and (lowest_price is None or lowest_price < min_price):
            continue
        if max_price is not None and (lowest_price is None or lowest_price > max_price):
            continue
        filtered_products.append(product)

    if sort == "price_asc":
        filtered_products.sort(key=lambda product: product.lowest_price or Decimal("0"))
    elif sort == "price_desc":
        filtered_products.sort(
            key=lambda product: product.lowest_price or Decimal("0"),
            reverse=True,
        )
    elif sort == "newest":
        filtered_products.sort(key=lambda product: product.id, reverse=True)
    else:
        filtered_products.sort(key=lambda product: rank_product(product, keyword))

    return filtered_products


@router.get("/search/suggestions")
def list_search_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=10),
):
    keyword = normalize_keyword(q)
    if not keyword:
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"query": "", "items": []},
            status_code=200,
        )

    cache_key = build_cache_key("search", "suggestions", keyword, limit)
    cached_items = get_cached_json(cache_key)
    if isinstance(cached_items, list):
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"query": keyword, "items": cached_items},
            status_code=200,
        )

    products = db.scalars(build_search_query(keyword)).unique().all()
    ranked_products = filter_and_sort_products(
        products,
        min_price=None,
        max_price=None,
        sort="default",
        keyword=keyword,
    )

    items: list[dict[str, object]] = []
    seen_keywords: set[str] = set()
    for product in ranked_products:
        if product.name in seen_keywords:
            continue
        items.append(
            {
                "keyword": product.name,
                "product_id": product.id,
                "category_id": product.category_id,
            }
        )
        seen_keywords.add(product.name)
        if len(items) >= limit:
            break

    set_cached_json(
        cache_key,
        items,
        ttl_seconds=SEARCH_SUGGESTIONS_CACHE_TTL,
    )
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"query": keyword, "items": items},
        status_code=200,
    )


@router.get("/search")
def search_products(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort: str = "default",
):
    keyword = normalize_keyword(q)
    if not keyword:
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"query": "", "items": [], "page": page, "page_size": page_size, "total": 0},
            status_code=200,
        )

    query = build_search_query(keyword)

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    products = db.scalars(query).unique().all()
    filtered_products = filter_and_sort_products(
        products,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        keyword=keyword,
    )

    total = len(filtered_products)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered_products[start:end]

    current_user = get_optional_user_from_request(request, db)
    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_SEARCH,
        target_type="search",
        ext_json={
            "query": keyword,
            "result_count": total,
            "category_id": category_id,
            "sort": sort,
        },
    )
    if current_user is not None:
        invalidate_recommendation_cache_for_user(current_user.id)
        db.commit()

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "query": keyword,
            "items": [serialize_product_list_item(product) for product in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        status_code=200,
    )


@router.post("/search/semantic")
def semantic_search(
    payload: SemanticSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    query = normalize_keyword(payload.query)
    pipeline = build_runtime_marker()
    filters = build_search_filters(
        category_id=payload.category_id,
        min_price=payload.min_price,
        max_price=payload.max_price,
        dynasty_style=payload.dynasty_style,
        craft_type=payload.craft_type,
        scene_tag=payload.scene_tag,
        festival_tag=payload.festival_tag,
        stock_only=payload.stock_only,
    )
    if not query:
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"query": "", "items": [], "total": 0, "pipeline": pipeline},
            status_code=200,
        )

    results = semantic_search_products(
        db,
        query=query,
        limit=payload.limit,
        category_id=payload.category_id,
        min_price=payload.min_price,
        max_price=payload.max_price,
        dynasty_style=payload.dynasty_style,
        craft_type=payload.craft_type,
        scene_tag=payload.scene_tag,
        festival_tag=payload.festival_tag,
        stock_only=payload.stock_only,
    )

    current_user = get_optional_user_from_request(request, db)
    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_SEARCH,
        target_type="semantic_search",
        ext_json={
            "query": query,
            "mode": "semantic",
            "result_count": len(results),
            "pipeline": pipeline["active_search_backend"],
            "filters": serialize_search_filters(filters),
        },
    )
    if current_user is not None:
        invalidate_recommendation_cache_for_user(current_user.id)
        db.commit()

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "query": query,
            "items": [
                {
                    **serialize_product_list_item(result.product),
                    "score": round(result.score, 6),
                    "reason": result.reason,
                }
                for result in results
            ],
            "total": len(results),
            "pipeline": pipeline,
        },
        status_code=200,
    )
