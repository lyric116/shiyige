import uuid

import httpx


def register_and_login_api(live_server, email: str, password: str) -> str:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": f"review-ui-{uuid.uuid4().hex[:6]}",
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


def fetch_product_by_keyword(live_server, keyword: str) -> dict:
    product_list_response = httpx.get(
        f"{live_server}/api/v1/products",
        params={"q": keyword, "page": 1, "page_size": 1},
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
    return product_detail_response.json()["data"]["product"]


def create_paid_review(
    live_server,
    access_token: str,
    product: dict,
    *,
    rating: int,
    content: str,
    image_urls: list[str] | None = None,
    is_anonymous: bool = False,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    default_sku = next(sku for sku in product["skus"] if sku["is_default"])

    address_response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "评价测试用户",
            "phone": "13800138000",
            "region": "浙江省 杭州市",
            "detail_address": f"西湖区测试路 {uuid.uuid4().hex[:4]} 号",
            "postal_code": "310000",
            "is_default": True,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert address_response.status_code == 201
    address_id = address_response.json()["data"]["address"]["id"]

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
            "buyer_note": "商品评价前端联调测试",
            "idempotency_key": f"review-page-{uuid.uuid4().hex[:8]}",
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

    review_response = httpx.post(
        f"{live_server}/api/v1/products/{product['id']}/reviews",
        headers=headers,
        json={
            "rating": rating,
            "content": content,
            "image_urls": image_urls or [],
            "is_anonymous": is_anonymous,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert review_response.status_code == 201


def test_product_reviews_section_uses_real_review_api(browser, live_server) -> None:
    product = fetch_product_by_keyword(live_server, "点翠发簪")
    password = "secret-pass-123"

    first_token = register_and_login_api(
        live_server,
        f"review-a-{uuid.uuid4().hex[:8]}@example.com",
        password,
    )
    second_token = register_and_login_api(
        live_server,
        f"review-b-{uuid.uuid4().hex[:8]}@example.com",
        password,
    )
    third_token = register_and_login_api(
        live_server,
        f"review-c-{uuid.uuid4().hex[:8]}@example.com",
        password,
    )

    create_paid_review(
        live_server,
        first_token,
        product,
        rating=5,
        content="第一条真实评价，附带晒单图片。",
        image_urls=["https://example.com/review-a.jpg"],
    )
    create_paid_review(
        live_server,
        second_token,
        product,
        rating=4,
        content="第二条真实评价，匿名展示。",
        is_anonymous=True,
    )
    create_paid_review(
        live_server,
        third_token,
        product,
        rating=3,
        content="第三条真实评价，用于分页。",
    )

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/product.html?id={product['id']}", wait_until="domcontentloaded")
    page.locator("#reviews-tab").click()
    page.wait_for_function(
        "() => {"
        "  const totalCopy = document.querySelector('#reviews-total-copy')?.textContent || '';"
        "  const itemCount = document.querySelectorAll('#reviews-container .review-item').length;"
        "  return totalCopy.includes('3 条评价') && itemCount === 2;"
        "}",
        timeout=5000,
    )

    assert page.locator("#reviews-average-rating").text_content() == "4.0"
    assert page.locator("#reviews-total-copy").text_content() == "基于 3 条评价"
    assert "".join(page.locator("#reviews-rating-bars").text_content().split()) == "5星14星13星12星01星0"

    reviews_text = page.locator("#reviews-container").text_content()
    assert "第三条真实评价，用于分页。" in reviews_text
    assert "第二条真实评价，匿名展示。" in reviews_text
    assert "匿名用户" in reviews_text
    assert "第一条真实评价，附带晒单图片。" not in reviews_text

    page.locator("#load-more-reviews-btn").click()
    page.wait_for_function(
        "() => {"
        "  const itemCount = document.querySelectorAll('#reviews-container .review-item').length;"
        "  const containerText = document.querySelector('#reviews-container')?.textContent || '';"
        "  return itemCount === 3 && containerText.includes('第一条真实评价，附带晒单图片。');"
        "}",
        timeout=5000,
    )

    assert page.locator("#reviews-container .review-images img").count() == 1
    assert page.locator("#reviews-load-more-wrapper").is_visible() is False

    context.close()
