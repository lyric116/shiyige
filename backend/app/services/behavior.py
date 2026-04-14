from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core.security import decode_token
from backend.app.models.user import User, UserBehaviorLog


BEHAVIOR_VIEW_PRODUCT = "view_product"
BEHAVIOR_SEARCH = "search"
BEHAVIOR_ADD_TO_CART = "add_to_cart"
BEHAVIOR_CREATE_ORDER = "create_order"
BEHAVIOR_PAY_ORDER = "pay_order"


def get_optional_user_from_request(request: Request, db: Session) -> User | None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    try:
        payload = decode_token(token)
    except HTTPException:
        return None

    if payload.token_type != "access":
        return None

    try:
        user_id = int(payload.sub)
    except ValueError:
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def log_behavior(
    db: Session,
    *,
    user: User | None,
    behavior_type: str,
    target_id: int | None = None,
    target_type: str | None = None,
    ext_json: dict[str, Any] | None = None,
) -> None:
    if user is None:
        return

    db.add(
        UserBehaviorLog(
            user_id=user.id,
            behavior_type=behavior_type,
            target_id=target_id,
            target_type=target_type,
            ext_json=ext_json,
        )
    )
