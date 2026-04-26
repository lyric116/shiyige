import pytest
from sqlalchemy import select

from backend.app.models.admin import OperationLog
from backend.app.models.recommendation import ProductEmbedding


@pytest.mark.asyncio
async def test_admin_reindex_endpoint_rebuilds_product_embeddings(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-reindex@example.com",
        username="admin-reindex",
    )
    headers = admin_auth_headers_factory(admin_user)

    with api_session_factory() as session:
        assert session.scalar(select(ProductEmbedding.id).limit(1)) is None

    response = await api_client.post(
        "/api/v1/admin/reindex/products",
        headers=headers,
        json={"force": True},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "reindex completed"
    assert body["data"]["result"]["indexed"] == 20
    assert body["data"]["result"]["skipped"] == 0
    assert len(body["data"]["result"]["product_ids"]) == 20

    with api_session_factory() as session:
        embeddings = session.scalars(
            select(ProductEmbedding).order_by(ProductEmbedding.product_id)
        ).all()
        operation_log = session.scalar(
            select(OperationLog)
            .where(OperationLog.admin_user_id == admin_user.id)
            .order_by(OperationLog.id.desc())
        )

        assert len(embeddings) == 20
        assert embeddings[0].embedding_vector
        assert operation_log is not None
        assert operation_log.action == "admin_reindex_products"
