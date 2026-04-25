from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserBehaviorLog
from backend.app.services.cache import (
    PRECOMPUTED_RECOMMENDATION_CACHE_TTL,
    PRECOMPUTED_RECOMMENDATION_STATUS_TTL,
    build_precomputed_recommendation_cache_key,
    build_precomputed_recommendation_status_key,
    get_cached_json,
    set_cached_json,
)
from backend.app.services.recommendation_delivery import resolve_recommendation_payload

PRECOMPUTED_RECOMMENDATION_SLOTS = ("home", "cart")


def isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def build_default_precompute_summary() -> dict[str, object]:
    return {
        "enabled": True,
        "supported_slots": list(PRECOMPUTED_RECOMMENDATION_SLOTS),
        "ttl_seconds": PRECOMPUTED_RECOMMENDATION_CACHE_TTL,
        "last_warmed_at": None,
        "last_backend": None,
        "last_limit": None,
        "last_warmed_user_count": 0,
        "last_snapshot_count": 0,
        "last_slots": [],
        "last_user_ids": [],
        "hit_count": 0,
        "miss_count": 0,
        "hit_rate": 0.0,
        "slot_stats": {},
    }


def get_recommendation_precompute_summary() -> dict[str, object]:
    payload = get_cached_json(build_precomputed_recommendation_status_key())
    if isinstance(payload, dict):
        summary = build_default_precompute_summary()
        summary.update(payload)
        hit_count = int(summary.get("hit_count") or 0)
        miss_count = int(summary.get("miss_count") or 0)
        total = hit_count + miss_count
        summary["hit_rate"] = round(hit_count / total, 4) if total else 0.0
        return summary
    return build_default_precompute_summary()


def persist_recommendation_precompute_summary(summary: dict[str, object]) -> None:
    hit_count = int(summary.get("hit_count") or 0)
    miss_count = int(summary.get("miss_count") or 0)
    total = hit_count + miss_count
    summary["hit_rate"] = round(hit_count / total, 4) if total else 0.0
    set_cached_json(
        build_precomputed_recommendation_status_key(),
        summary,
        ttl_seconds=PRECOMPUTED_RECOMMENDATION_STATUS_TTL,
    )


def record_recommendation_precompute_served(
    *,
    slot: str,
    hit: bool,
) -> dict[str, object]:
    summary = get_recommendation_precompute_summary()
    summary["hit_count"] = int(summary.get("hit_count") or 0) + int(hit)
    summary["miss_count"] = int(summary.get("miss_count") or 0) + int(not hit)
    slot_stats = dict(summary.get("slot_stats") or {})
    slot_summary = dict(slot_stats.get(slot) or {"hit_count": 0, "miss_count": 0})
    slot_summary["hit_count"] = int(slot_summary.get("hit_count") or 0) + int(hit)
    slot_summary["miss_count"] = int(slot_summary.get("miss_count") or 0) + int(not hit)
    slot_total = int(slot_summary["hit_count"]) + int(slot_summary["miss_count"])
    slot_summary["hit_rate"] = round(
        int(slot_summary["hit_count"]) / slot_total,
        4,
    ) if slot_total else 0.0
    slot_stats[slot] = slot_summary
    summary["slot_stats"] = slot_stats
    persist_recommendation_precompute_summary(summary)
    return summary


def get_precomputed_recommendation_snapshot(
    *,
    user_id: int,
    slot: str,
    limit: int,
    backend: str,
) -> dict[str, object] | None:
    payload = get_cached_json(
        build_precomputed_recommendation_cache_key(
            user_id=user_id,
            slot=slot,
            limit=limit,
            backend=backend,
        )
    )
    if not isinstance(payload, dict):
        return None
    items = payload.get("items")
    pipeline = payload.get("pipeline")
    if not isinstance(items, list) or not isinstance(pipeline, dict):
        return None
    return payload


def normalize_precompute_slots(slots: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized: list[str] = []
    for raw_slot in slots or []:
        slot = str(raw_slot).strip().lower()
        if slot in PRECOMPUTED_RECOMMENDATION_SLOTS and slot not in normalized:
            normalized.append(slot)
    return normalized or ["home"]


def resolve_precompute_user_ids(
    db: Session,
    *,
    user_ids: list[int] | None,
    max_users: int,
) -> list[int]:
    if user_ids:
        rows = db.scalars(
            select(User.id)
            .where(
                User.id.in_(sorted(set(user_ids))),
                User.role == "user",
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
        ).all()
        return [int(user_id) for user_id in rows[:max_users]]

    recent_rows = db.execute(
        select(
            UserBehaviorLog.user_id,
            func.max(UserBehaviorLog.created_at).label("last_event_at"),
        )
        .where(UserBehaviorLog.user_id.is_not(None))
        .group_by(UserBehaviorLog.user_id)
        .order_by(func.max(UserBehaviorLog.created_at).desc())
        .limit(max_users)
    ).all()
    resolved = [int(user_id) for user_id, _last_event_at in recent_rows if user_id is not None]

    if len(resolved) >= max_users:
        return resolved[:max_users]

    fallback_query = (
        select(User.id)
        .where(
            User.role == "user",
            User.is_active.is_(True),
        )
        .order_by(User.id.asc())
        .limit(max_users - len(resolved))
    )
    if resolved:
        fallback_query = fallback_query.where(User.id.not_in(resolved))
    fallback_rows = db.scalars(fallback_query).all()
    return [*resolved, *(int(user_id) for user_id in fallback_rows)]


def warm_precomputed_recommendations(
    db: Session,
    *,
    slots: list[str] | tuple[str, ...] | None = None,
    limit: int = 6,
    user_ids: list[int] | None = None,
    max_users: int = 20,
) -> dict[str, object]:
    normalized_slots = normalize_precompute_slots(slots)
    resolved_user_ids = resolve_precompute_user_ids(
        db,
        user_ids=user_ids,
        max_users=max_users,
    )
    snapshot_count = 0
    last_backend = "baseline"

    for slot in normalized_slots:
        for user_id in resolved_user_ids:
            payload = resolve_recommendation_payload(
                db,
                user_id=user_id,
                limit=limit,
                slot=slot,
                debug=False,
            )
            last_backend = str(payload.pipeline.get("active_recommendation_backend", "baseline"))
            snapshot = {
                "user_id": user_id,
                "slot": slot,
                "limit": limit,
                "backend": last_backend,
                "generated_at": datetime.utcnow().isoformat(),
                "pipeline": dict(payload.pipeline),
                "items": list(payload.items),
            }
            set_cached_json(
                build_precomputed_recommendation_cache_key(
                    user_id=user_id,
                    slot=slot,
                    limit=limit,
                    backend=last_backend,
                ),
                snapshot,
                ttl_seconds=PRECOMPUTED_RECOMMENDATION_CACHE_TTL,
            )
            snapshot_count += 1

    summary = get_recommendation_precompute_summary()
    summary.update(
        {
            "last_warmed_at": datetime.utcnow().isoformat(),
            "last_backend": last_backend,
            "last_limit": limit,
            "last_warmed_user_count": len(resolved_user_ids),
            "last_snapshot_count": snapshot_count,
            "last_slots": normalized_slots,
            "last_user_ids": resolved_user_ids[:10],
        }
    )
    persist_recommendation_precompute_summary(summary)
    return {
        "slots": normalized_slots,
        "user_ids": resolved_user_ids,
        "snapshot_count": snapshot_count,
        "summary": summary,
    }
