import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Use a pure-passlib scheme to avoid bcrypt backend incompatibilities in the
# local Python 3.13 environment while preserving the same security API.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 30
REFRESH_TOKEN_TTL_DAYS = 7
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60


class TokenPayload(BaseModel):
    sub: str
    token_type: str
    exp: int
    role: str | None = None


def get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "development-secret-key")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    role: str | None = None,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "token_type": token_type,
        "exp": int(expires_at.timestamp()),
    }
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def create_access_token(
    subject: str,
    role: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    ttl = expires_delta or timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    return _create_token(subject=subject, token_type="access", expires_delta=ttl, role=role)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    ttl = expires_delta or timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    return _create_token(subject=subject, token_type="refresh", expires_delta=ttl)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        ) from exc


async def get_current_token(token: str | None = Depends(oauth2_scheme)) -> TokenPayload:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing token",
        )
    return decode_token(token)


def require_role(*roles: str):
    async def dependency(token_payload: TokenPayload = Depends(get_current_token)) -> TokenPayload:
        if token_payload.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission denied",
            )
        return token_payload

    return dependency
