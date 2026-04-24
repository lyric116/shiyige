import uuid

import httpx


def register_and_login_user_api(live_server, email: str, password: str) -> str:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": "admin-order-user",
            "email": email,
            "password": password,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert register_response.status_code == 201

    login_response = httpx.post(
        f"{live_server}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=5.0,
        trust_env=False,
    )
    assert login_response.status_code == 200
    return login_response.json()["data"]["access_token"]


def seed_paid_order(live_server, access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}

    address_response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "后台订单演示用户",
            "phone": "13800138000",
            "region": "北京市 东城区",
            "detail_address": "景山前街 4 号",
            "postal_code": "100009",
            "is_default": True,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert address_response.status_code == 201
    address_id = address_response.json()["data"]["address"]["id"]

    product_list_response = httpx.get(
        f"{live_server}/api/v1/products",
        params={"q": "点翠发簪"},
        timeout=5.0,
        trust_env=False,
    )
    assert product_list_response.status_code == 200
    product_id = product_list_response.json()["data"]["items"][0]["id"]

    product_detail_response = httpx.get(
        f"{live_server}/api/v1/products/{product_id}",
        timeout=5.0,
        trust_env=False,
    )
    assert product_detail_response.status_code == 200
    product = product_detail_response.json()["data"]["product"]
    default_sku = next(sku for sku in product["skus"] if sku["is_default"])

    search_response = httpx.get(
        f"{live_server}/api/v1/search",
        headers=headers,
        params={"q": "古风发簪"},
        timeout=5.0,
        trust_env=False,
    )
    assert search_response.status_code == 200

    add_cart_response = httpx.post(
        f"{live_server}/api/v1/cart/items",
        headers=headers,
        json={
            "product_id": product["id"],
            "sku_id": default_sku["id"],
            "quantity": 1,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert add_cart_response.status_code == 201

    create_order_response = httpx.post(
        f"{live_server}/api/v1/orders",
        headers=headers,
        json={
            "address_id": address_id,
            "buyer_note": "后台最小页面联调测试",
            "idempotency_key": f"admin-page-{uuid.uuid4().hex[:8]}",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert create_order_response.status_code == 201
    order = create_order_response.json()["data"]["order"]

    pay_response = httpx.post(
        f"{live_server}/api/v1/orders/{order['id']}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
        timeout=5.0,
        trust_env=False,
    )
    assert pay_response.status_code == 200
    return pay_response.json()["data"]["order"]


def test_admin_basic_pages_use_real_admin_apis(browser, live_server) -> None:
    user_email = f"admin-order-{uuid.uuid4().hex[:8]}@example.com"
    user_token = register_and_login_user_api(live_server, user_email, "secret-pass-123")
    order = seed_paid_order(live_server, user_token)

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/admin/login.html", wait_until="domcontentloaded")
    page.locator("#admin-email").fill("admin@shiyige-demo.com")
    page.locator("#admin-password").fill("admin123456")
    page.locator("#admin-login-form button[type='submit']").click()
    page.wait_for_url(
        f"{live_server}/admin/index.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )
    page.wait_for_function(
        "() => document.querySelector('#summary-products')?.textContent?.trim() === '20'"
        " && document.querySelector('#summary-orders')?.textContent?.trim() === '1'"
        " && document.querySelector('#summary-users')?.textContent?.trim() === '1'"
        " && document.querySelector('#recommendation-kpis')?.textContent?.includes('CTR')",
        timeout=10000,
    )

    assert page.locator("#summary-products").text_content() == "20"
    assert page.locator("#summary-orders").text_content() == "1"
    assert page.locator("#summary-users").text_content() == "1"
    assert page.locator("#summary-paid-orders").text_content() == "1"
    assert "CTR" in page.locator("#recommendation-kpis").text_content()
    assert "当前激活方案" in page.locator("#dashboard-active-experiment").text_content()

    page.goto(f"{live_server}/admin/products.html", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#products-table-body')?.textContent?.includes('点翠发簪')",
        timeout=5000,
    )
    assert "点翠发簪" in page.locator("#products-table-body").text_content()

    page.goto(f"{live_server}/admin/orders.html", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#orders-table-body')?.textContent?.includes('admin-order-user')"
        " && document.querySelector('#orders-table-body')?.textContent?.includes('PAID')",
        timeout=5000,
    )
    orders_text = page.locator("#orders-table-body").text_content()
    assert order["order_no"] in orders_text
    assert "admin-order-user" in orders_text
    assert "PAID" in orders_text

    page.goto(f"{live_server}/admin/reindex.html", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#vector-status-metrics')?.textContent?.includes('Collection')",
        timeout=5000,
    )
    page.locator("#reindex-products-btn").click()
    page.wait_for_function(
        "() => document.querySelector('#reindex-result')?.textContent?.includes('模式：full')",
        timeout=5000,
    )
    assert "已索引 20 条" in page.locator("#reindex-result").text_content()
    assert "Collection" in page.locator("#vector-status-metrics").text_content()

    page.goto(f"{live_server}/admin/recommendation-debug.html", wait_until="domcontentloaded")
    page.locator("#debug-user-email").fill(user_email)
    page.locator("#debug-limit").fill("3")
    page.locator("#recommendation-debug-submit").click()
    page.locator("#debug-recommendation-list .debug-card").first.wait_for(timeout=5000)

    assert user_email in page.locator("#debug-user-profile-grid").text_content()
    assert "点翠发簪" in page.locator("#debug-user-profile-grid").text_content()
    assert "add_to_cart" in page.locator("#debug-behavior-table-body").text_content()
    assert "召回通道" in page.locator("#debug-recommendation-list").text_content()

    page.goto(f"{live_server}/admin/recommendation-config.html", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#recommendation-config-list')?.textContent?.includes('full_pipeline')",
        timeout=5000,
    )
    assert "baseline" in page.locator("#recommendation-config-list").text_content()
    assert "full_pipeline" in page.locator("#recommendation-config-list").text_content()

    context.close()
