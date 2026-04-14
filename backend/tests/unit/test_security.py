from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_token,
    hash_password,
    require_role,
    verify_password,
)


def test_password_hash_and_verify_roundtrip() -> None:
    password_hash = hash_password("secret-password")

    assert password_hash != "secret-password"
    assert verify_password("secret-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_and_refresh_tokens_encode_expected_payloads(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    access_token = create_access_token("user-1", role="admin", expires_delta=timedelta(minutes=5))
    refresh_token = create_refresh_token("user-1", expires_delta=timedelta(days=1))

    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    assert access_payload.sub == "user-1"
    assert access_payload.token_type == "access"
    assert access_payload.role == "admin"
    assert refresh_payload.sub == "user-1"
    assert refresh_payload.token_type == "refresh"


@pytest.mark.asyncio
async def test_get_current_token_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_token(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "missing token"


@pytest.mark.asyncio
async def test_require_role_rejects_wrong_role(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    token = create_access_token("user-1", role="user")
    payload = decode_token(token)
    admin_dependency = require_role("admin")

    with pytest.raises(HTTPException) as exc_info:
        await admin_dependency(payload)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "permission denied"


@pytest.mark.asyncio
async def test_require_role_accepts_allowed_role(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    token = create_access_token("user-1", role="admin")
    payload = decode_token(token)
    admin_dependency = require_role("admin")

    resolved = await admin_dependency(payload)

    assert resolved.sub == "user-1"
    assert resolved.role == "admin"
