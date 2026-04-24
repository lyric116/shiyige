from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.admin_auth import create_operation_log, get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.models.product import Product
from backend.app.models.recommendation import ProductEmbedding
from backend.app.models.user import User
from backend.app.services.embedding import get_embedding_provider
from backend.app.services.recommendation_pipeline import run_recommendation_pipeline
from backend.app.services.recommendations import (
    collect_product_ids_from_log,
    load_products_for_interest_profile,
    load_user_behavior_logs,
)

router = APIRouter(prefix="/admin/recommendations", tags=["admin-recommendations"])


def round_vector_preview(values: list[float] | None, *, size: int = 8) -> list[float]:
    if not values:
        return []
    return [round(float(value), 4) for value in values[:size]]


def isoformat_or_none(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def serialize_user(user: User) -> dict[str, object]:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "display_name": profile.display_name if profile else None,
    }


def serialize_behavior_logs(
    logs,
    products_by_id: dict[int, object],
    *,
    limit: int = 8,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for log in list(reversed(logs))[:limit]:
        product_names = [
            products_by_id[product_id].name
            for product_id in collect_product_ids_from_log(log)
            if product_id in products_by_id
        ]
        items.append(
            {
                "id": log.id,
                "created_at": isoformat_or_none(log.created_at),
                "behavior_type": log.behavior_type,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "query": (log.ext_json or {}).get("query"),
                "product_names": product_names,
                "ext_json": log.ext_json or {},
            }
        )
    return items


def serialize_consumed_products(
    product_ids: set[int],
    products_by_id: dict[int, object],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for product_id in sorted(product_ids):
        product = products_by_id.get(product_id)
        items.append(
            {
                "id": product_id,
                "name": product.name if product is not None else f"商品 {product_id}",
            }
        )
    return items


def serialize_candidates(candidates, *, limit: int) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates[:limit], start=1):
        product = candidate.product
        embedding = product.embedding
        items.append(
            {
                "rank": index,
                "product_id": product.id,
                "name": product.name,
                "category": product.category.name if product.category else None,
                "tags": [tag.tag for tag in product.tags],
                "reason": candidate.reason,
                "matched_terms": candidate.matched_terms,
                "score": round(candidate.score, 6),
                "vector_similarity": round(
                    getattr(candidate, "similarity", getattr(candidate, "vector_similarity", 0.0)),
                    6,
                ),
                "vector_score": round(candidate.vector_score, 6),
                "term_bonus": round(candidate.term_bonus, 6),
                "recall_channels": list(getattr(candidate, "recall_channels", [])),
                "channel_details": [
                    {
                        "channel": detail.recall_channel,
                        "score": round(detail.recall_score, 6),
                        "rank": detail.rank_in_channel,
                        "matched_terms": list(detail.matched_terms),
                        "reason_parts": list(detail.reason_parts),
                        "metadata": dict(detail.metadata),
                    }
                    for detail in getattr(candidate, "channel_details", [])
                ],
                "embedding_dimension": len(embedding.embedding_vector or []) if embedding else 0,
                "embedding_vector_preview": round_vector_preview(
                    embedding.embedding_vector if embedding else None
                ),
                "embedding_text_preview": (embedding.embedding_text[:200] if embedding else ""),
                "content_hash": embedding.content_hash if embedding else None,
            }
        )
    return items


@router.get("/debug")
def debug_recommendations(
    request: Request,
    email: str = Query(min_length=3, max_length=255),
    limit: int = Query(default=5, ge=1, le=20),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required")

    user = db.scalar(
        select(User)
        .options(selectinload(User.profile))
        .where(User.email == normalized_email)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    embedding_provider = get_embedding_provider()
    pipeline_run = run_recommendation_pipeline(
        db,
        user_id=user.id,
        limit=limit,
        provider=embedding_provider,
        candidate_limit=max(limit * 4, 12),
    )
    profile = pipeline_run.profile

    logs = load_user_behavior_logs(db, user.id)
    referenced_product_ids: set[int] = set()
    for log in logs:
        referenced_product_ids.update(collect_product_ids_from_log(log))

    top_terms = pipeline_run.top_terms
    consumed_product_ids = pipeline_run.consumed_product_ids
    referenced_product_ids.update(consumed_product_ids)
    products_by_id = load_products_for_interest_profile(db, referenced_product_ids)

    active_products = db.scalar(select(func.count(Product.id)).where(Product.status == 1)) or 0
    candidates = pipeline_run.candidates
    indexed_products = db.scalar(select(func.count(ProductEmbedding.id))) or 0

    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_debug_recommendations",
        target_type="user_interest_profile",
        target_id=user.id,
        detail_json={
            "email": normalized_email,
            "limit": limit,
            "behavior_count": profile.behavior_count,
        },
    )
    db.commit()

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "user": serialize_user(user),
            "provider": embedding_provider.describe(),
            "profile": {
                "behavior_count": profile.behavior_count,
                "last_event_at": isoformat_or_none(profile.last_event_at),
                "last_built_at": isoformat_or_none(profile.last_built_at),
                "model_name": profile.model_name,
                "content_hash": profile.content_hash,
                "top_terms": top_terms,
                "consumed_products": serialize_consumed_products(
                    consumed_product_ids,
                    products_by_id,
                ),
                "profile_text": profile.profile_text or "",
                "vector_dimension": len(profile.embedding_vector or []),
                "vector_preview": round_vector_preview(profile.embedding_vector),
            },
            "metrics": {
                "indexed_products": indexed_products,
                "active_products": active_products,
                "candidate_count": len(candidates),
                "cold_start": pipeline_run.cold_start,
            },
            "recent_behaviors": serialize_behavior_logs(logs, products_by_id),
            "recommendations": serialize_candidates(candidates, limit=limit),
        },
        status_code=200,
    )
