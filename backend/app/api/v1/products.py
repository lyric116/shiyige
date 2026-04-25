from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.users import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.product import Category, Product, ProductSku, ProductTag
from backend.app.models.user import User
from backend.app.services.behavior import (
    BEHAVIOR_VIEW_PRODUCT,
    get_optional_user_from_request,
    log_behavior,
)
from backend.app.services.cache import (
    PRODUCT_DETAIL_CACHE_TTL,
    RECOMMENDATIONS_CACHE_TTL,
    RELATED_PRODUCTS_CACHE_TTL,
    build_cache_key,
    build_recommendation_cache_key,
    get_cached_json,
    invalidate_recommendation_cache_for_user,
    set_cached_json,
)
from backend.app.services.recommendation_logging import (
    RequestTimer,
    log_recommendation_action,
    log_recommendation_request,
)
from backend.app.services.recommendation_pipeline import run_recommendation_pipeline
from backend.app.services.recommendations import recommend_products_for_user
from backend.app.services.vector_search import find_related_products
from backend.app.services.vector_store import build_runtime_marker, probe_vector_store_runtime

router = APIRouter(tags=["catalog"])

RECOMMENDATION_SOURCE_LABELS = {
    "personalized": "个性化",
    "similar": "相似商品",
    "hot": "热门",
    "new": "新品探索",
    "seasonal": "节令主题",
}


def serialize_category(category: Category) -> dict[str, object]:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
    }


def serialize_product_list_item(product: Product) -> dict[str, object]:
    default_sku = product.default_sku
    return {
        "id": product.id,
        "name": product.name,
        "subtitle": product.subtitle,
        "cover_url": product.cover_url,
        "culture_summary": product.culture_summary,
        "category": serialize_category(product.category),
        "price": product.lowest_price,
        "member_price": default_sku.member_price if default_sku else None,
        "tags": [tag.tag for tag in product.tags],
    }


def serialize_product_detail(product: Product) -> dict[str, object]:
    default_sku = product.default_sku
    return {
        "id": product.id,
        "name": product.name,
        "subtitle": product.subtitle,
        "cover_url": product.cover_url,
        "description": product.description,
        "culture_summary": product.culture_summary,
        "dynasty_style": product.dynasty_style,
        "craft_type": product.craft_type,
        "festival_tag": product.festival_tag,
        "scene_tag": product.scene_tag,
        "status": product.status,
        "category": serialize_category(product.category),
        "price": product.lowest_price,
        "member_price": default_sku.member_price if default_sku else None,
        "tags": [tag.tag for tag in product.tags],
        "media": [
            {
                "id": media.id,
                "media_type": media.media_type,
                "url": media.url,
                "sort_order": media.sort_order,
            }
            for media in sorted(product.media_items, key=lambda item: (item.sort_order, item.id))
        ],
        "skus": [
            {
                "id": sku.id,
                "sku_code": sku.sku_code,
                "name": sku.name,
                "specs": sku.specs_json,
                "price": sku.price,
                "member_price": sku.member_price,
                "is_default": sku.is_default,
                "is_active": sku.is_active,
                "inventory": sku.inventory.quantity if sku.inventory else 0,
            }
            for sku in product.skus
        ],
    }


def build_recommendation_source_meta(result, *, slot: str) -> dict[str, str]:
    recall_channels = list(getattr(result, "recall_channels", []))
    reason = str(getattr(result, "reason", ""))

    if slot in {"related", "cart", "order_complete"} or "related_products" in recall_channels:
        source_type = "similar"
    elif "collaborative_user" in recall_channels or "item_cooccurrence" in recall_channels:
        source_type = "personalized"
    elif "content_profile" in recall_channels or "sparse_interest" in recall_channels:
        source_type = "personalized"
    elif "trending" in recall_channels and ("节" in reason or "节令" in reason):
        source_type = "seasonal"
    elif "trending" in recall_channels:
        source_type = "hot"
    elif "new_arrival" in recall_channels or "cold_start" in recall_channels:
        source_type = "new"
    elif "节" in reason or "节令" in reason:
        source_type = "seasonal"
    elif slot == "home":
        source_type = "personalized"
    else:
        source_type = "similar"

    return {
        "source_type": source_type,
        "source_label": RECOMMENDATION_SOURCE_LABELS[source_type],
    }


@router.get("/categories")
def list_categories(
    request: Request,
    db: Session = Depends(get_db),
):
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order.asc(), Category.id.asc())
    ).all()

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": [serialize_category(category) for category in categories]
        },
        status_code=200,
    )


def serialize_recommendation_item(
    result,
    *,
    debug: bool = False,
    slot: str = "home",
) -> dict[str, object]:
    feature_summary = dict(getattr(result, "feature_summary", {}))
    ranking_features = dict(getattr(result, "ranking_features", {}))
    business_summary = feature_summary.get("business", {})
    is_exploration = bool(
        business_summary.get("exploration_candidate")
        if isinstance(business_summary, dict)
        else ranking_features.get("exploration_candidate", 0.0)
    )
    item = {
        **serialize_product_list_item(result.product),
        "score": round(result.score, 6),
        "final_score": round(result.score, 6),
        "reason": result.reason,
        "recall_channels": list(getattr(result, "recall_channels", [])),
        "is_exploration": is_exploration,
        **build_recommendation_source_meta(result, slot=slot),
    }
    if debug:
        item.update(
            {
                "matched_terms": list(getattr(result, "matched_terms", [])),
                "feature_highlights": list(getattr(result, "feature_highlights", [])),
                "ranking_features": ranking_features,
                "rank_features": ranking_features,
                "feature_summary": feature_summary,
                "score_breakdown": dict(getattr(result, "score_breakdown", {})),
                "ranker_name": getattr(result, "ranker_name", "baseline"),
                "ranker_model_version": getattr(result, "ranker_model_version", "baseline"),
                "ltr_fallback_used": bool(getattr(result, "ltr_fallback_used", False)),
            }
        )
    return item


def serialize_related_product_item(result) -> dict[str, object]:
    source_breakdown = dict(getattr(result, "source_breakdown", {}))
    return {
        **serialize_product_list_item(result.product),
        "score": round(result.score, 6),
        "final_score": round(result.score, 6),
        "reason": result.reason,
        "matched_terms": list(getattr(result, "matched_terms", [])),
        "dense_similarity": dict(source_breakdown.get("dense_similarity", {})),
        "co_view_co_buy": dict(source_breakdown.get("co_view_co_buy", {})),
        "cultural_match": dict(source_breakdown.get("cultural_match", {})),
        "source_breakdown": source_breakdown,
        "diversity_result": dict(getattr(result, "diversity_result", {})),
        **build_recommendation_source_meta(result, slot="related"),
    }


@router.get("/products/recommendations")
@router.get("/recommendations")
def get_product_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=6, ge=1, le=20),
    slot: str = Query(default="home", min_length=2, max_length=50),
    debug: bool = Query(default=False),
):
    pipeline = build_runtime_marker()
    cache_key = build_recommendation_cache_key(
        user_id=current_user.id,
        slot=slot,
        limit=limit,
        backend=str(pipeline["active_recommendation_backend"]),
    )
    cached_items = get_cached_json(cache_key)
    if not debug and isinstance(cached_items, list):
        log_recommendation_request(
            db,
            request=request,
            user_id=current_user.id,
            slot=slot,
            pipeline_version=str(pipeline["recommendation_pipeline_version"]),
            model_version=str(pipeline.get("active_ranker", "cache")),
            candidate_count=len(cached_items),
            final_items=[
                {
                    "product_id": item["id"],
                    "score": item.get("score", 0.0),
                    "reason": item.get("reason", ""),
                    "recall_channels": item.get("recall_channels", []),
                }
                for item in cached_items
            ],
            latency_ms=0.0,
            fallback_used=bool(pipeline["degraded_to_baseline"]),
        )
        db.commit()
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"items": cached_items, "pipeline": {**pipeline, "slot": slot}},
            status_code=200,
        )

    timer = RequestTimer.start()
    runtime = probe_vector_store_runtime()
    if runtime.active_recommendation_backend == "multi_recall":
        pipeline_run = run_recommendation_pipeline(
            db,
            user_id=current_user.id,
            limit=limit,
        )
        items = [
            serialize_recommendation_item(candidate, debug=debug, slot=slot)
            for candidate in pipeline_run.candidates[:limit]
        ]
        pipeline.update(
            {
                "active_ranker": pipeline_run.active_ranker,
                "ranker_model_version": pipeline_run.ranker_model_version,
                "ltr_fallback_used": pipeline_run.ltr_fallback_used,
            }
        )
    else:
        results = recommend_products_for_user(
            db,
            user_id=current_user.id,
            limit=limit,
            force_baseline=True,
        )
        items = [
            serialize_recommendation_item(result, debug=debug, slot=slot)
            for result in results
        ]
        pipeline.update(
            {
                "active_ranker": "baseline",
                "ranker_model_version": "baseline",
                "ltr_fallback_used": False,
            }
        )

    if not debug:
        set_cached_json(
            cache_key,
            items,
            ttl_seconds=RECOMMENDATIONS_CACHE_TTL,
        )
    log_recommendation_request(
        db,
        request=request,
        user_id=current_user.id,
        slot=slot,
        pipeline_version=str(pipeline["recommendation_pipeline_version"]),
        model_version=str(
            pipeline.get(
                "ranker_model_version",
                pipeline.get("active_ranker", "baseline"),
            )
        ),
        candidate_count=len(items),
        final_items=[
            {
                "product_id": item["id"],
                "score": item.get("score", 0.0),
                "reason": item.get("reason", ""),
                "recall_channels": item.get("recall_channels", []),
            }
            for item in items
        ],
        latency_ms=timer.elapsed_ms(),
        fallback_used=bool(pipeline["degraded_to_baseline"]),
    )
    db.commit()
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"items": items, "pipeline": {**pipeline, "slot": slot}},
        status_code=200,
    )


@router.get("/products/{product_id}")
def get_product_detail(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    cache_key = build_cache_key("products", "detail", product_id)
    cached_product = get_cached_json(cache_key)
    if isinstance(cached_product, dict):
        current_user = get_optional_user_from_request(request, db)
        log_behavior(
            db,
            user=current_user,
            behavior_type=BEHAVIOR_VIEW_PRODUCT,
            target_id=product_id,
            target_type="product",
            ext_json={
                "product_name": cached_product.get("name"),
                "category_id": cached_product.get("category", {}).get("id"),
                "sku_count": len(cached_product.get("skus", [])),
            },
        )
        if current_user is not None:
            log_recommendation_action(
                db,
                user_id=current_user.id,
                product_id=product_id,
                action_type="click",
            )
            invalidate_recommendation_cache_for_user(current_user.id)
            db.commit()

        return build_response(
            request=request,
            code=0,
            message="ok",
            data={"product": cached_product},
            status_code=200,
        )

    product = db.scalar(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.media_items),
            selectinload(Product.tags),
        )
        .where(Product.id == product_id)
    )

    if product is None:
        return build_response(
            request=request,
            code=40001,
            message="product not found",
            data=None,
            status_code=404,
        )

    current_user = get_optional_user_from_request(request, db)
    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_VIEW_PRODUCT,
        target_id=product.id,
        target_type="product",
        ext_json={
            "product_name": product.name,
            "category_id": product.category_id,
            "sku_count": len(product.skus),
        },
    )
    if current_user is not None:
        log_recommendation_action(
            db,
            user_id=current_user.id,
            product_id=product.id,
            action_type="click",
        )
        invalidate_recommendation_cache_for_user(current_user.id)
        db.commit()

    serialized_product = serialize_product_detail(product)
    set_cached_json(
        cache_key,
        serialized_product,
        ttl_seconds=PRODUCT_DETAIL_CACHE_TTL,
    )
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"product": serialized_product},
        status_code=200,
    )


@router.get("/products/{product_id}/related")
def get_related_products(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(default=4, ge=1, le=12),
):
    runtime = build_runtime_marker()
    cache_key = build_cache_key(
        "products",
        "related",
        product_id,
        runtime["active_search_backend"],
        limit,
    )
    cached_items = get_cached_json(cache_key)
    if isinstance(cached_items, list):
        return build_response(
            request=request,
            code=0,
            message="ok",
            data={
                "items": cached_items,
                "pipeline": runtime,
            },
            status_code=200,
        )

    product = db.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        return build_response(
            request=request,
            code=40001,
            message="product not found",
            data=None,
            status_code=404,
        )

    results = find_related_products(
        db,
        product_id=product_id,
        limit=limit,
    )
    items = [serialize_related_product_item(result) for result in results]
    set_cached_json(
        cache_key,
        items,
        ttl_seconds=RELATED_PRODUCTS_CACHE_TTL,
    )
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": items,
            "pipeline": runtime,
        },
        status_code=200,
    )


@router.get("/products")
def list_products(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    tag: str | None = None,
    sort: str = "default",
    q: str | None = None,
):
    query = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.tags),
        )
        .distinct()
    )

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if q:
        query = query.where(
            or_(
                Product.name.contains(q),
                Product.subtitle.contains(q),
                Product.culture_summary.contains(q),
            )
        )

    if tag:
        query = query.join(Product.tags).where(ProductTag.tag == tag)

    products = db.scalars(query).unique().all()

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
        filtered_products.sort(key=lambda product: product.id)

    total = len(filtered_products)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered_products[start:end]

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": [serialize_product_list_item(product) for product in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        status_code=200,
    )
