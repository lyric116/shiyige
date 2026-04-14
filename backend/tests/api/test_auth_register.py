import pytest
from sqlalchemy import select

from backend.app.core.security import verify_password
from backend.app.models.user import User, UserProfile


@pytest.mark.asyncio
async def test_register_creates_user_with_profile_and_hashed_password(
    api_client,
    api_session_factory,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new-user@example.com",
            "username": "newuser",
            "password": "secret-pass-123",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["code"] == 0
    assert body["message"] == "registered successfully"
    assert body["data"]["user"]["email"] == "new-user@example.com"
    assert body["data"]["user"]["username"] == "newuser"
    assert body["data"]["user"]["role"] == "user"
    assert body["data"]["user"]["is_active"] is True
    assert body["request_id"] == response.headers["X-Request-ID"]

    with api_session_factory() as session:
        user = session.scalar(select(User).where(User.email == "new-user@example.com"))
        profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))

        assert user is not None
        assert user.password_hash != "secret-pass-123"
        assert verify_password("secret-pass-123", user.password_hash) is True
        assert profile is not None
        assert profile.display_name == "newuser"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(api_client, api_session_factory, create_user) -> None:
    create_user(email="existing@example.com", username="existing-user")

    response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "username": "another-user",
            "password": "secret-pass-123",
        },
    )

    body = response.json()
    assert response.status_code == 409
    assert body["code"] == 40001
    assert body["message"] == "email already registered"
