import pytest
from sqlalchemy import select

from backend.app.models.admin import OperationLog
from backend.app.models.product import Category, Product


@pytest.mark.asyncio
async def test_admin_products_list_returns_seeded_catalog(
    api_client,
    create_admin_user,
    admin_auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-products@example.com",
        username="admin-products",
    )

    response = await api_client.get(
        "/api/v1/admin/products",
        headers=admin_auth_headers_factory(admin_user),
        params={"q": "点翠发簪"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "点翠发簪"
    assert body["data"]["items"][0]["default_sku"]["inventory"] == 35


@pytest.mark.asyncio
async def test_admin_can_create_and_update_product(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-product-write@example.com",
        username="admin-product-write",
    )
    headers = admin_auth_headers_factory(admin_user)

    with api_session_factory() as session:
        category = session.scalar(select(Category).where(Category.slug == "hanfu"))
        assert category is not None

    create_response = await api_client.post(
        "/api/v1/admin/products",
        headers=headers,
        json={
            "category_id": category.id,
            "name": "后台新建汉服",
            "subtitle": "后台创建测试款",
            "cover_url": "https://example.com/admin-product-cover.jpg",
            "description": "用于后台商品管理接口测试。",
            "culture_summary": "用于验证后台商品写接口。",
            "dynasty_style": "明制",
            "craft_type": "刺绣",
            "festival_tag": "春日",
            "scene_tag": "拍照",
            "status": 1,
            "tags": ["后台", "测试", "汉服"],
            "media_urls": [
                "https://example.com/admin-product-1.jpg",
                "https://example.com/admin-product-2.jpg",
            ],
            "default_sku": {
                "sku_code": "ADMIN-SKU-001",
                "name": "默认款",
                "price": "699.00",
                "member_price": "649.00",
                "inventory": 9,
                "is_active": True,
            },
        },
    )
    create_body = create_response.json()

    assert create_response.status_code == 201
    assert create_body["message"] == "product created"
    assert create_body["data"]["product"]["name"] == "后台新建汉服"
    assert create_body["data"]["product"]["default_sku"]["inventory"] == 9

    product_id = create_body["data"]["product"]["id"]
    update_response = await api_client.put(
        f"/api/v1/admin/products/{product_id}",
        headers=headers,
        json={
            "category_id": category.id,
            "name": "后台更新汉服",
            "subtitle": "后台更新测试款",
            "cover_url": "https://example.com/admin-product-cover-updated.jpg",
            "description": "后台商品更新成功。",
            "culture_summary": "后台更新后的文化说明。",
            "dynasty_style": "宋制",
            "craft_type": "织造",
            "festival_tag": "夏日",
            "scene_tag": "出游",
            "status": 0,
            "tags": ["后台", "更新"],
            "media_urls": ["https://example.com/admin-product-updated.jpg"],
            "default_sku": {
                "sku_code": "ADMIN-SKU-001",
                "name": "默认款升级版",
                "price": "799.00",
                "member_price": "729.00",
                "inventory": 15,
                "is_active": True,
            },
        },
    )
    update_body = update_response.json()

    assert update_response.status_code == 200
    assert update_body["message"] == "product updated"
    assert update_body["data"]["product"]["name"] == "后台更新汉服"
    assert update_body["data"]["product"]["default_sku"]["inventory"] == 15
    assert update_body["data"]["product"]["tags"] == ["后台", "更新"]

    with api_session_factory() as session:
        stored_product = session.get(Product, product_id)
        assert stored_product is not None
        assert stored_product.name == "后台更新汉服"
        assert stored_product.default_sku is not None
        assert stored_product.default_sku.inventory is not None
        assert stored_product.default_sku.inventory.quantity == 15

        operation_logs = session.scalars(
            select(OperationLog)
            .where(OperationLog.admin_user_id == admin_user.id)
            .order_by(OperationLog.id.asc())
        ).all()
        assert [log.action for log in operation_logs[-2:]] == [
            "admin_product_create",
            "admin_product_update",
        ]
