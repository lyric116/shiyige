import pytest

from backend.app.models.admin import OperationLog


@pytest.mark.asyncio
async def test_admin_vector_index_status_endpoint_returns_status_payload(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-vector-status@example.com",
        username="admin-vector-status",
    )
    headers = admin_auth_headers_factory(admin_user)

    monkeypatch.setattr(
        "backend.app.api.v1.admin_vector_index.get_product_index_status",
        lambda db: {
            "qdrant_available": True,
            "collection_name": "shiyige_products_v1",
            "collection_exists": True,
            "active_product_count": 20,
            "indexed_product_count": 20,
            "qdrant_point_count": 20,
            "failed_products": [],
        },
    )

    response = await api_client.get("/api/v1/admin/vector-index/products/status", headers=headers)
    alias_response = await api_client.get("/api/v1/admin/vector-index/status", headers=headers)

    assert response.status_code == 200
    assert alias_response.status_code == 200
    body = response.json()
    assert body["message"] == "ok"
    assert body["data"]["status"]["qdrant_point_count"] == 20
    assert alias_response.json()["data"]["status"]["collection_name"] == "shiyige_products_v1"

    with api_session_factory() as session:
        operation_log = session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert operation_log is not None
        assert operation_log.action == "admin_vector_index_status"


@pytest.mark.asyncio
async def test_admin_vector_index_sync_endpoint_dispatches_mode(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-vector-sync@example.com",
        username="admin-vector-sync",
    )
    headers = admin_auth_headers_factory(admin_user)
    calls: list[tuple[str, object]] = []

    def fake_sync(db, *, mode, product_ids):
        calls.append((mode, product_ids))
        return {
            "mode": mode,
            "indexed": 1,
            "payload_updates": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0,
            "product_ids": product_ids or [],
            "failed_product_ids": [],
            "collection_name": "shiyige_products_v1",
            "dense_model_name": "dense-test",
            "sparse_model_name": "sparse-test",
            "colbert_model_name": "colbert-test",
        }

    monkeypatch.setattr(
        "backend.app.api.v1.admin_vector_index.sync_products_to_qdrant",
        fake_sync,
    )

    response = await api_client.post(
        "/api/v1/admin/vector-index/products/sync",
        headers=headers,
        json={"mode": "incremental", "product_ids": [3]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "vector index sync completed"
    assert body["data"]["result"]["indexed"] == 1
    assert calls == [("incremental", [3])]

    with api_session_factory() as session:
        operation_log = session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert operation_log is not None
        assert operation_log.action == "admin_vector_index_sync"


@pytest.mark.asyncio
async def test_admin_vector_index_rebuild_and_product_reindex_aliases_dispatch_expected_modes(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-vector-alias@example.com",
        username="admin-vector-alias",
    )
    headers = admin_auth_headers_factory(admin_user)
    calls: list[tuple[str, object]] = []

    def fake_sync(db, *, mode, product_ids):
        calls.append((mode, product_ids))
        return {
            "mode": mode,
            "indexed": 1,
            "payload_updates": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0,
            "product_ids": product_ids or [],
            "failed_product_ids": [],
            "collection_name": "shiyige_products_v1",
            "dense_model_name": "dense-test",
            "sparse_model_name": "sparse-test",
            "colbert_model_name": "colbert-test",
        }

    monkeypatch.setattr(
        "backend.app.api.v1.admin_vector_index.sync_products_to_qdrant",
        fake_sync,
    )

    rebuild_response = await api_client.post(
        "/api/v1/admin/vector-index/rebuild",
        headers=headers,
    )
    reindex_response = await api_client.post(
        "/api/v1/admin/vector-index/products/9/reindex",
        headers=headers,
    )

    assert rebuild_response.status_code == 200
    assert reindex_response.status_code == 200
    assert rebuild_response.json()["message"] == "vector index rebuild completed"
    assert reindex_response.json()["message"] == "product reindex completed"
    assert calls == [("full", None), ("incremental", [9])]

    with api_session_factory() as session:
        operation_log = session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert operation_log is not None
        assert operation_log.action == "admin_vector_index_reindex_product"
