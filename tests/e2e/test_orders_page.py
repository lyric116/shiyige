import uuid

import httpx


def login_through_page(page, live_server, email: str, password: str) -> None:
    page.goto(f"{live_server}/login.html", wait_until="domcontentloaded")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.locator("#login-form button[type='submit']").click()
    page.wait_for_url(
        f"{live_server}/index.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )


def register_and_login_api(live_server, email: str, password: str) -> str:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": f"user-{uuid.uuid4().hex[:6]}",
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


def create_pending_order(live_server, access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}

    address_response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "订单测试用户",
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

    order_response = httpx.post(
        f"{live_server}/api/v1/orders",
        headers=headers,
        json={
            "address_id": address_id,
            "buyer_note": "订单页回归测试",
            "idempotency_key": f"orders-page-{uuid.uuid4().hex[:8]}",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert order_response.status_code == 201
    return order_response.json()["data"]["order"]


def test_orders_page_shows_empty_state_for_new_user(browser, live_server) -> None:
    email = f"orders-empty-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret-pass-123"
    register_and_login_api(live_server, email, password)

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, email, password)
    page.goto(f"{live_server}/orders.html", wait_until="domcontentloaded")
    page.locator("#orders-empty-state").wait_for(timeout=5000)
    assert "暂时还没有订单" in page.locator("#orders-empty-state").text_content()

    context.close()


def test_orders_page_reads_real_orders_and_can_pay(browser, live_server) -> None:
    email = f"orders-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret-pass-123"
    access_token = register_and_login_api(live_server, email, password)
    order = create_pending_order(live_server, access_token)
    headers = {"Authorization": f"Bearer {access_token}"}

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, email, password)
    page.goto(f"{live_server}/orders.html", wait_until="domcontentloaded")
    page.locator("#orders-list .order-list-item").wait_for(timeout=5000)
    page.locator("#order-no").wait_for(timeout=5000)

    assert order["order_no"] in page.locator("#order-no").text_content()
    assert "点翠发簪" in page.locator("#order-detail").text_content()
    assert "待支付" in page.locator("#order-status").text_content()

    page.locator("#order-pay-button").click()
    page.get_by_text("订单支付成功").wait_for(timeout=5000)
    page.wait_for_function(
        "() => document.querySelector('#order-status')?.textContent?.includes('已支付')"
    )
    assert "balance" in page.locator("#payment-records").text_content()

    detail_response = httpx.get(
        f"{live_server}/api/v1/orders/{order['id']}",
        headers=headers,
        timeout=5.0,
        trust_env=False,
    )
    assert detail_response.status_code == 200
    paid_order = detail_response.json()["data"]["order"]
    assert paid_order["status"] == "PAID"
    assert len(paid_order["payment_records"]) == 1

    context.close()
