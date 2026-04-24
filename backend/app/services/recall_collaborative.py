from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.services.collaborative_filtering import (
    recall_collaborative_user_candidates,
    recall_item_cooccurrence_candidates,
)


def recall_collaborative_candidates(
    db: Session,
    *,
    user_id: int,
    consumed_product_ids: set[int],
    recent_product_ids: list[int],
    top_terms: list[str],
    limit: int = 24,
    settings: AppSettings | None = None,
    client=None,
) -> dict[str, list]:
    return {
        "collaborative_user": recall_collaborative_user_candidates(
            db,
            user_id=user_id,
            consumed_product_ids=consumed_product_ids,
            top_terms=top_terms,
            limit=limit,
            settings=settings,
            client=client,
        ),
        "item_cooccurrence": recall_item_cooccurrence_candidates(
            db,
            seed_product_ids=recent_product_ids,
            consumed_product_ids=consumed_product_ids,
            top_terms=top_terms,
            limit=limit,
        ),
    }
