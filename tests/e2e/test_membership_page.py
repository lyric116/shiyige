import uuid

import httpx


def register_and_login_api(live_server, email: str, password: str) -> str:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": f"member-ui-{uuid.uuid4().hex[:6]}",
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


def seed_paid_member_order(live_server, access_token: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}

    address_response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "会员测试用户",
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
        params={"q": "明制襦裙"},
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

    order_response = httpx.post(
        f"{live_server}/api/v1/orders",
        headers=headers,
        json={
            "address_id": address_id,
            "buyer_note": "会员中心回归测试",
            "idempotency_key": f"member-page-{uuid.uuid4().hex[:8]}",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["data"]["order"]["id"]

    pay_response = httpx.post(
        f"{live_server}/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
        timeout=5.0,
        trust_env=False,
    )
    assert pay_response.status_code == 200


def test_membership_page_uses_real_points_levels_and_member_price(browser, live_server) -> None:
    email = f"membership-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret-pass-123"
    access_token = register_and_login_api(live_server, email, password)
    seed_paid_member_order(live_server, access_token)

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, email, password)
    page.goto(f"{live_server}/membership.html", wait_until="domcontentloaded")
    page.wait_for_function(
        (
            "() => {"
            "  const card = document.querySelector('.membership-card')?.textContent || '';"
            "  const history = document.querySelector('#points-history-body')?.textContent || '';"
            "  return card.includes('白银会员')"
            " && card.includes('1808')"
            " && history.includes('支付获得积分');"
            "}"
        ),
        timeout=5000,
    )

    assert "白银会员" in page.locator(".membership-card").text_content()
    assert "1808" in page.locator(".membership-card").text_content()
    assert "消费享1.2倍积分" in page.locator(".member-benefits").text_content()
    assert "支付获得积分" in page.locator("#points-history-body").text_content()

    page.goto(f"{live_server}/product.html?id=1", wait_until="domcontentloaded")
    page.wait_for_function(
        (
            "() => document.querySelector('#member-price .text-danger')"
            "?.textContent?.trim() === '¥799.00'"
        ),
        timeout=5000,
    )
    assert page.locator("#member-price .text-danger").text_content() == "¥799.00"

    context.close()
