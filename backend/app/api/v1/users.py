from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.core.security import (
    TokenPayload,
    get_current_token,
    hash_password,
    verify_password,
)
from backend.app.models.user import User, UserAddress, UserProfile
from backend.app.schemas.address import UserAddressRequest
from backend.app.schemas.user import ChangePasswordRequest, UpdateUserProfileRequest

router = APIRouter(prefix="/users", tags=["users"])


def serialize_user(user: User) -> dict[str, object]:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "profile": {
            "display_name": profile.display_name if profile else None,
            "phone": profile.phone if profile else None,
            "birthday": profile.birthday.isoformat() if profile and profile.birthday else None,
            "bio": profile.bio if profile else None,
            "avatar_url": profile.avatar_url if profile else None,
        },
    }


def get_user_from_token(
    token_payload: TokenPayload,
    db: Session,
) -> User:
    if token_payload.token_type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token")

    try:
        user_id = int(token_payload.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token"
        ) from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not available")
    return user


def get_current_user(
    token_payload: TokenPayload = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> User:
    return get_user_from_token(token_payload=token_payload, db=db)


def get_or_create_profile(user: User) -> UserProfile:
    if user.profile is None:
        user.profile = UserProfile()
    return user.profile


def serialize_address(address: UserAddress) -> dict[str, object]:
    return {
        "id": address.id,
        "recipient_name": address.recipient_name,
        "phone": address.phone,
        "region": address.region,
        "detail_address": address.detail_address,
        "postal_code": address.postal_code,
        "is_default": address.is_default,
    }


def get_user_address(db: Session, user_id: int, address_id: int) -> UserAddress | None:
    return db.scalar(
        select(UserAddress).where(
            UserAddress.user_id == user_id,
            UserAddress.id == address_id,
        )
    )


def clear_other_default_addresses(
    db: Session, user_id: int, keep_address_id: int | None = None
) -> None:
    addresses = db.scalars(select(UserAddress).where(UserAddress.user_id == user_id)).all()
    for address in addresses:
        if keep_address_id is not None and address.id == keep_address_id:
            continue
        address.is_default = False


@router.get("/me")
def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"user": serialize_user(current_user)},
        status_code=200,
    )


@router.put("/me")
def update_me(
    payload: UpdateUserProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    username = payload.username.strip()

    existing_email = db.scalar(select(User).where(User.email == email, User.id != current_user.id))
    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    existing_username = db.scalar(
        select(User).where(User.username == username, User.id != current_user.id)
    )
    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="username already registered"
        )

    current_user.email = email
    current_user.username = username

    profile = get_or_create_profile(current_user)
    profile.display_name = payload.display_name.strip() if payload.display_name else None
    profile.phone = payload.phone.strip() if payload.phone else None
    profile.birthday = payload.birthday
    profile.bio = payload.bio.strip() if payload.bio else None
    profile.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return build_response(
        request=request,
        code=0,
        message="profile updated",
        data={"user": serialize_user(current_user)},
        status_code=200,
    )


@router.put("/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="current password is incorrect"
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()

    return build_response(
        request=request,
        code=0,
        message="password updated",
        data=None,
        status_code=200,
    )


@router.get("/addresses")
def list_addresses(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    addresses = db.scalars(
        select(UserAddress)
        .where(UserAddress.user_id == current_user.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.id.asc())
    ).all()
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"items": [serialize_address(address) for address in addresses]},
        status_code=200,
    )


@router.post("/addresses")
def create_address(
    payload: UserAddressRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_addresses = db.scalars(
        select(UserAddress).where(UserAddress.user_id == current_user.id)
    ).all()
    should_be_default = payload.is_default or not existing_addresses

    if should_be_default:
        clear_other_default_addresses(db, current_user.id)

    address = UserAddress(
        user_id=current_user.id,
        recipient_name=payload.recipient_name.strip(),
        phone=payload.phone.strip(),
        region=payload.region.strip(),
        detail_address=payload.detail_address.strip(),
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        is_default=should_be_default,
    )
    db.add(address)
    db.commit()
    db.refresh(address)

    return build_response(
        request=request,
        code=0,
        message="address created",
        data={"address": serialize_address(address)},
        status_code=201,
    )


@router.put("/addresses/{address_id}")
def update_address(
    address_id: int,
    payload: UserAddressRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = get_user_address(db, current_user.id, address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")

    if payload.is_default:
        clear_other_default_addresses(db, current_user.id, keep_address_id=address.id)

    address.recipient_name = payload.recipient_name.strip()
    address.phone = payload.phone.strip()
    address.region = payload.region.strip()
    address.detail_address = payload.detail_address.strip()
    address.postal_code = payload.postal_code.strip() if payload.postal_code else None
    address.is_default = payload.is_default

    db.add(address)
    db.commit()
    db.refresh(address)

    return build_response(
        request=request,
        code=0,
        message="address updated",
        data={"address": serialize_address(address)},
        status_code=200,
    )


@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = get_user_address(db, current_user.id, address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")

    was_default = address.is_default
    db.delete(address)
    db.commit()

    if was_default:
        replacement = db.scalar(
            select(UserAddress)
            .where(UserAddress.user_id == current_user.id)
            .order_by(UserAddress.id.asc())
        )
        if replacement is not None:
            clear_other_default_addresses(db, current_user.id, keep_address_id=replacement.id)
            replacement.is_default = True
            db.add(replacement)
            db.commit()

    return build_response(
        request=request,
        code=0,
        message="address deleted",
        data=None,
        status_code=200,
    )
