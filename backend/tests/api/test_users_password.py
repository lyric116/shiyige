import pytest
from sqlalchemy import select

from backend.app.core.security import verify_password
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_change_password_updates_hash(
    api_client,
    api_session_factory,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="password@example.com",
        username="password-user",
        password="secret-pass-123",
    )

    response = await api_client.put(
        "/api/v1/users/password",
        headers=auth_headers_factory(user),
        json={
            "current_password": "secret-pass-123",
            "new_password": "new-secret-pass-456",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "password updated"

    with api_session_factory() as session:
        updated_user = session.scalar(select(User).where(User.id == user.id))
        assert updated_user is not None
        assert verify_password("new-secret-pass-456", updated_user.password_hash) is True


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password(
    api_client,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="password@example.com",
        username="password-user",
        password="secret-pass-123",
    )

    response = await api_client.put(
        "/api/v1/users/password",
        headers=auth_headers_factory(user),
        json={
            "current_password": "wrong-password",
            "new_password": "new-secret-pass-456",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == 40001
    assert body["message"] == "current password is incorrect"
