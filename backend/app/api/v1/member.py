from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.v1.users import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.user import User
from backend.app.services.member import (
    build_member_benefits,
    build_member_summary,
    ensure_point_account,
    get_point_account,
    list_member_levels,
    serialize_member_level,
    serialize_point_log,
)

router = APIRouter(prefix="/member", tags=["member"])


def serialize_member_user(user: User) -> dict[str, object]:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": profile.display_name if profile else None,
    }


@router.get("/profile")
def get_member_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_point_account(db, current_user.id)
    db.commit()

    account = get_point_account(db, current_user.id)
    assert account is not None
    levels = list_member_levels(db)

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "profile": {
                "user": serialize_member_user(current_user),
                **build_member_summary(account, levels),
            }
        },
        status_code=200,
    )


@router.get("/points")
def get_member_points(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_point_account(db, current_user.id)
    db.commit()

    account = get_point_account(db, current_user.id, include_logs=True)
    assert account is not None
    levels = list_member_levels(db)
    logs = sorted(account.point_logs, key=lambda item: (item.created_at, item.id), reverse=True)

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "summary": build_member_summary(account, levels),
            "items": [serialize_point_log(log) for log in logs],
        },
        status_code=200,
    )


@router.get("/benefits")
def get_member_benefits(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_point_account(db, current_user.id)
    db.commit()

    account = get_point_account(db, current_user.id)
    assert account is not None
    current_level = account.member_level
    assert current_level is not None
    levels = list_member_levels(db)

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "current_level": serialize_member_level(current_level, is_current=True),
            "items": [
                {
                    **serialize_member_level(level, is_current=level.id == current_level.id),
                    "benefits": build_member_benefits(level),
                }
                for level in levels
            ],
        },
        status_code=200,
    )
