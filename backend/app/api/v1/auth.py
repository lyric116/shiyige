from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.core.security import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from backend.app.models.user import User, UserProfile
from backend.app.schemas.auth import LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    }


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_user_by_subject(db: Session, subject: str) -> User | None:
    try:
        user_id = int(subject)
    except ValueError:
        return None
    return db.get(User, user_id)


@router.post("/register")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    username = payload.username.strip()

    existing_email = get_user_by_email(db, email)
    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    existing_username = get_user_by_username(db, username)
    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="username already registered"
        )

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    user.profile = UserProfile(display_name=username)

    db.add(user)
    db.commit()
    db.refresh(user)

    return build_response(
        request=request,
        code=0,
        message="registered successfully",
        data={"user": serialize_user(user)},
        status_code=201,
    )


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    user = get_user_by_email(db, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user inactive")

    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id))
    response = build_response(
        request=request,
        code=0,
        message="login successful",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": serialize_user(user),
        },
        status_code=200,
    )
    set_refresh_cookie(response, refresh_token)
    return response


@router.post("/refresh")
def refresh_token(
    request: Request,
    db: Session = Depends(get_db),
):
    refresh_token_value = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh token"
        )

    token_payload = decode_token(refresh_token_value)
    if token_payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )

    user = get_user_by_subject(db, token_payload.sub)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not available")

    access_token = create_access_token(subject=str(user.id), role=user.role)
    return build_response(
        request=request,
        code=0,
        message="token refreshed",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": serialize_user(user),
        },
        status_code=200,
    )


@router.post("/logout")
def logout(request: Request):
    response = build_response(
        request=request,
        code=0,
        message="logout successful",
        data=None,
        status_code=200,
    )
    clear_refresh_cookie(response)
    return response
