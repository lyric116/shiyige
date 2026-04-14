import pytest
from sqlalchemy import select

from backend.app.core.security import decode_token
from backend.app.models.admin import AdminUser, OperationLog


@pytest.mark.asyncio
async def test_admin_login_returns_access_token_and_records_operation(
    api_client,
    api_session_factory,
    create_admin_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    admin_user = create_admin_user(
        email="admin-login@example.com",
        username="admin-login",
        password="secret-pass-123",
        role="super_admin",
    )

    response = await api_client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "admin-login@example.com",
            "password": "secret-pass-123",
        },
    )
    body = response.json()
    access_payload = decode_token(body["data"]["access_token"])

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "login successful"
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["admin"]["id"] == admin_user.id
    assert body["data"]["admin"]["role"] == "super_admin"
    assert access_payload.sub == f"admin:{admin_user.id}"
    assert access_payload.role == "super_admin"

    with api_session_factory() as session:
        stored_admin = session.get(AdminUser, admin_user.id)
        stored_log = session.scalar(
            select(OperationLog)
            .where(OperationLog.admin_user_id == admin_user.id)
            .order_by(OperationLog.id.desc())
        )

        assert stored_admin is not None
        assert stored_admin.last_login_at is not None
        assert stored_log is not None
        assert stored_log.action == "login"
        assert stored_log.request_path == "/api/v1/admin/auth/login"
        assert stored_log.request_method == "POST"
        assert stored_log.target_type == "admin_user"
        assert stored_log.target_id == admin_user.id


@pytest.mark.asyncio
async def test_admin_login_rejects_invalid_credentials(
    api_client,
    create_admin_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    create_admin_user(
        email="admin-invalid@example.com",
        username="admin-invalid",
        password="secret-pass-123",
        role="ops_admin",
    )

    response = await api_client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "admin-invalid@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "invalid credentials"


@pytest.mark.asyncio
async def test_admin_me_returns_current_admin_profile(
    api_client,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    admin_user = create_admin_user(
        email="admin-me@example.com",
        username="admin-me",
        role="ops_admin",
    )

    response = await api_client.get(
        "/api/v1/admin/auth/me",
        headers=admin_auth_headers_factory(admin_user),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "ok"
    assert body["data"]["admin"]["id"] == admin_user.id
    assert body["data"]["admin"]["email"] == "admin-me@example.com"
    assert body["data"]["admin"]["role"] == "ops_admin"


@pytest.mark.asyncio
async def test_admin_me_rejects_frontend_user_token(
    api_client,
    create_user,
    auth_headers_factory,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="normal-user@example.com",
        username="normal-user",
        password="secret-pass-123",
    )

    response = await api_client.get(
        "/api/v1/admin/auth/me",
        headers=auth_headers_factory(user),
    )

    assert response.status_code == 403
    assert response.json()["message"] == "permission denied"
