import pytest
from sqlalchemy import select

from backend.app.models.user import User


@pytest.mark.asyncio
async def test_update_profile_persists_user_and_profile_changes(
    api_client,
    api_session_factory,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="profile@example.com",
        username="profile-user",
        password="secret-pass-123",
    )

    response = await api_client.put(
        "/api/v1/users/me",
        headers=auth_headers_factory(user),
        json={
            "email": "updated@example.com",
            "username": "updated-user",
            "display_name": "更新昵称",
            "phone": "13800138000",
            "birthday": "1999-09-09",
            "bio": "喜欢传统文化",
            "avatar_url": "https://example.com/avatar.png",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "profile updated"
    assert body["data"]["user"]["email"] == "updated@example.com"
    assert body["data"]["user"]["username"] == "updated-user"
    assert body["data"]["user"]["profile"]["display_name"] == "更新昵称"
    assert body["data"]["user"]["profile"]["phone"] == "13800138000"
    assert body["data"]["user"]["profile"]["birthday"] == "1999-09-09"
    assert body["data"]["user"]["profile"]["bio"] == "喜欢传统文化"
    assert body["data"]["user"]["profile"]["avatar_url"] == "https://example.com/avatar.png"

    with api_session_factory() as session:
        updated_user = session.scalar(select(User).where(User.id == user.id))
        assert updated_user is not None
        assert updated_user.email == "updated@example.com"
        assert updated_user.username == "updated-user"
        assert updated_user.profile is not None
        assert updated_user.profile.display_name == "更新昵称"


@pytest.mark.asyncio
async def test_update_profile_rejects_duplicate_email(
    api_client,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    current_user = create_user(
        email="current@example.com",
        username="current-user",
        password="secret-pass-123",
    )
    create_user(
        email="taken@example.com",
        username="taken-user",
        password="secret-pass-123",
    )

    response = await api_client.put(
        "/api/v1/users/me",
        headers=auth_headers_factory(current_user),
        json={
            "email": "taken@example.com",
            "username": "current-user",
            "display_name": "current-user",
            "phone": None,
            "birthday": None,
            "bio": None,
            "avatar_url": None,
        },
    )

    body = response.json()
    assert response.status_code == 409
    assert body["code"] == 40001
    assert body["message"] == "email already registered"
