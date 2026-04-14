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
            "username": f"checkout-{uuid.uuid4().hex[:6]}",
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


def seed_checkout_prerequisites(live_server, access_token: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}

    address_response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "结算测试用户",
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
            "quantity": 2,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert add_cart_response.status_code == 201


def test_checkout_page_uses_real_cart_address_and_order_flow(browser, live_server) -> None:
    email = f"checkout-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret-pass-123"
    access_token = register_and_login_api(live_server, email, password)
    headers = {"Authorization": f"Bearer {access_token}"}
    seed_checkout_prerequisites(live_server, access_token)

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, email, password)
    page.goto(f"{live_server}/cart.html", wait_until="domcontentloaded")
    page.get_by_text("点翠发簪").wait_for(timeout=5000)
    page.locator("#checkout-btn").click()
    page.wait_for_url(f"{live_server}/checkout.html", wait_until="domcontentloaded", timeout=5000)

    page.locator("#address-select").wait_for(timeout=5000)
    page.wait_for_function(
        "() => document.querySelector('#selected-address-card')?.textContent?.includes('结算测试用户')"
    )
    page.wait_for_function(
        "() => document.querySelector('#order-items')?.textContent?.includes('点翠发簪')"
    )
    page.wait_for_function(
        "() => document.querySelector('#total')?.textContent?.trim() === '¥268.00'"
    )
    assert "结算测试用户" in page.locator("#selected-address-card").text_content()
    assert "点翠发簪" in page.locator("#order-items").text_content()
    assert page.locator("#total").text_content() == "¥268.00"

    page.locator("#note").fill("请尽快发货")
    page.locator("#place-order-btn").click()

    page.locator("#orderSuccessModal").wait_for(timeout=5000)
    page.wait_for_function(
      "() => document.querySelector('#order-number')?.textContent?.startsWith('SYG')"
    )

    orders_response = httpx.get(
        f"{live_server}/api/v1/orders",
        headers=headers,
        timeout=5.0,
        trust_env=False,
    )
    assert orders_response.status_code == 200
    orders = orders_response.json()["data"]["items"]
    assert len(orders) == 1
    assert orders[0]["status"] == "PAID"
    assert orders[0]["buyer_note"] == "请尽快发货"
    assert orders[0]["payment_records"][0]["payment_method"] == "alipay"

    cart_response = httpx.get(
        f"{live_server}/api/v1/cart",
        headers=headers,
        timeout=5.0,
        trust_env=False,
    )
    assert cart_response.status_code == 200
    assert cart_response.json()["data"]["cart"]["items"] == []

    context.close()
