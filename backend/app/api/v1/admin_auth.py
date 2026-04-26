from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.core.security import (
    TokenPayload,
    create_access_token,
    get_current_token,
    verify_password,
)
from backend.app.models.admin import AdminUser, OperationLog
from backend.app.schemas.auth import LoginRequest

ADMIN_ALLOWED_ROLES = ("super_admin", "ops_admin")
ADMIN_SUBJECT_PREFIX = "admin:"

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def serialize_admin_user(admin_user: AdminUser) -> dict[str, object]:
    return {
        "id": admin_user.id,
        "email": admin_user.email,
        "username": admin_user.username,
        "role": admin_user.role,
        "is_active": admin_user.is_active,
        "last_login_at": admin_user.last_login_at.isoformat() if admin_user.last_login_at else None,
    }


def build_admin_subject(admin_user_id: int) -> str:
    return f"{ADMIN_SUBJECT_PREFIX}{admin_user_id}"


def parse_admin_subject(subject: str) -> int:
    if not subject.startswith(ADMIN_SUBJECT_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")

    raw_admin_id = subject.removeprefix(ADMIN_SUBJECT_PREFIX)
    try:
        return int(raw_admin_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin token",
        ) from exc


def get_admin_user_by_email(db: Session, email: str) -> AdminUser | None:
    return db.scalar(select(AdminUser).where(AdminUser.email == email))


def create_operation_log(
    db: Session,
    *,
    admin_user: AdminUser,
    request: Request,
    action: str,
    status_text: str = "success",
    detail_json: dict[str, object] | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
) -> None:
    db.add(
        OperationLog(
            admin_user_id=admin_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_path=str(request.url.path),
            request_method=request.method,
            status=status_text,
            detail_json=detail_json,
        )
    )


def get_admin_from_token(token_payload: TokenPayload, db: Session) -> AdminUser:
    if token_payload.token_type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token")

    admin_user = db.get(AdminUser, parse_admin_subject(token_payload.sub))
    if admin_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin not available")
    if not admin_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin inactive")
    return admin_user


def get_current_admin(
    token_payload: TokenPayload = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> AdminUser:
    if token_payload.role not in ADMIN_ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
    return get_admin_from_token(token_payload=token_payload, db=db)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    admin_user = get_admin_user_by_email(db, email)
    if admin_user is None or not verify_password(payload.password, admin_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    if not admin_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin inactive")

    admin_user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    create_operation_log(
        db,
        admin_user=admin_user,
        request=request,
        action="login",
        target_type="admin_user",
        target_id=admin_user.id,
        detail_json={"role": admin_user.role},
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    access_token = create_access_token(
        subject=build_admin_subject(admin_user.id),
        role=admin_user.role,
    )
    return build_response(
        request=request,
        code=0,
        message="login successful",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "admin": serialize_admin_user(admin_user),
        },
        status_code=200,
    )


@router.get("/me")
def get_me(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
):
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"admin": serialize_admin_user(current_admin)},
        status_code=200,
    )


@router.post("/logout")
def logout(request: Request):
    return build_response(
        request=request,
        code=0,
        message="logout successful",
        data=None,
        status_code=200,
    )
