import uuid

import httpx


def register_through_page(page, live_server: str, username: str, email: str, password: str) -> None:
    page.goto(f"{live_server}/register.html", wait_until="domcontentloaded")
    page.locator("#username").fill(username)
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.locator("#confirm_password").fill(password)
    page.locator("#agree-terms").check()
    page.locator("#register-form button[type='submit']").click()
    page.wait_for_url(
        f"{live_server}/login.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )


def login_through_page(page, live_server: str, email: str, password: str) -> None:
    page.goto(f"{live_server}/login.html", wait_until="domcontentloaded")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.locator("#login-form button[type='submit']").click()
    page.wait_for_url(
        f"{live_server}/index.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )


def create_default_address(live_server: str, access_token: str) -> dict:
    response = httpx.post(
        f"{live_server}/api/v1/users/addresses",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "recipient_name": "全链路演示用户",
            "phone": "13800138000",
            "region": "北京市 东城区",
            "detail_address": "景山前街 4 号",
            "postal_code": "100009",
            "is_default": True,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert response.status_code == 201
    return response.json()["data"]["address"]


def fetch_product_by_keyword(live_server: str, keyword: str) -> dict:
    list_response = httpx.get(
        f"{live_server}/api/v1/products",
        params={"q": keyword, "page": 1, "page_size": 1},
        timeout=5.0,
        trust_env=False,
    )
    assert list_response.status_code == 200
    product_id = list_response.json()["data"]["items"][0]["id"]

    detail_response = httpx.get(
        f"{live_server}/api/v1/products/{product_id}",
        timeout=5.0,
        trust_env=False,
    )
    assert detail_response.status_code == 200
    return detail_response.json()["data"]["product"]


def get_recommendations(live_server: str, access_token: str) -> list[dict]:
    response = httpx.get(
        f"{live_server}/api/v1/products/recommendations",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5.0,
        trust_env=False,
    )
    assert response.status_code == 200
    return response.json()["data"]["items"]


def create_review(live_server: str, access_token: str, product_id: int, content: str) -> None:
    response = httpx.post(
        f"{live_server}/api/v1/products/{product_id}/reviews",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "rating": 5,
            "content": content,
            "image_urls": [],
            "is_anonymous": False,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert response.status_code == 201


def create_preference_trace(live_server: str, access_token: str, product: dict, query: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    default_sku = next(sku for sku in product["skus"] if sku["is_default"])

    detail_response = httpx.get(
        f"{live_server}/api/v1/products/{product['id']}",
        headers=headers,
        timeout=5.0,
        trust_env=False,
    )
    assert detail_response.status_code == 200

    search_response = httpx.get(
        f"{live_server}/api/v1/search",
        params={"q": query},
        headers=headers,
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


def test_full_demo_flow(browser, live_server) -> None:
    email = f"full-demo-{uuid.uuid4().hex[:8]}@example.com"
    username = f"demo{uuid.uuid4().hex[:6]}"
    password = "secret-pass-123"
    semantic_query = "适合春日出游的刺绣汉服"
    review_content = "完整链路演示后的真实评价：版型雅致，刺绣细节很出彩。"

    product = fetch_product_by_keyword(live_server, "明制襦裙")
    semantic_response = httpx.post(
        f"{live_server}/api/v1/search/semantic",
        json={"query": semantic_query, "limit": 3},
        timeout=5.0,
        trust_env=False,
    )
    assert semantic_response.status_code == 200
    semantic_item = semantic_response.json()["data"]["items"][0]

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    register_through_page(page, live_server, username, email, password)
    login_through_page(page, live_server, email, password)

    access_token = page.evaluate("window.sessionStorage.getItem('shiyige_access_token')")
    assert access_token is not None

    initial_recommendations = get_recommendations(live_server, access_token)[:3]
    assert len(initial_recommendations) == 3
    create_default_address(live_server, access_token)

    page.locator(".search-input").first.fill("明制")
    page.locator('datalist option[value="明制襦裙"]').wait_for(
        state="attached",
        timeout=5000,
    )
    page.locator(".search-form").first.locator('button[type="submit"]').click()
    page.wait_for_function(
        "() => document.querySelector('#category-name')?.textContent?.trim() === '搜索：明制'"
        " && document.querySelector('#products-container')?.textContent?.includes('明制襦裙')",
        timeout=5000,
    )

    page.locator("#catalog-search-input").fill(semantic_query)
    page.locator("#search-mode-select").select_option("semantic")
    page.locator("#search-entry-submit").click()
    page.wait_for_function(
        "([expectedName, expectedReason]) => {"
        "  const header = document.querySelector('#category-name')?.textContent?.trim();"
        "  const content = document.querySelector('#products-container')?.textContent || '';"
        "  return header === '语义搜索：适合春日出游的刺绣汉服'"
        "    && content.includes(expectedName)"
        "    && content.includes(expectedReason);"
        "}",
        arg=[semantic_item["name"], semantic_item["reason"]],
        timeout=5000,
    )
    assert "语义相关" in page.locator("#products-container").text_content()
    assert "文化标签匹配" in page.locator("#products-container").text_content()

    page.goto(f"{live_server}/product.html?id={product['id']}", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#product-name')?.textContent?.trim() === '明制襦裙'",
        timeout=5000,
    )
    page.locator("#quantity").fill("2")
    page.locator("#add-to-cart-form button[type='submit']").click()
    page.get_by_text("商品已成功加入购物车").wait_for(timeout=5000)
    page.goto(f"{live_server}/cart.html", wait_until="domcontentloaded")
    page.get_by_text("明制襦裙").wait_for(timeout=5000)
    page.locator("#checkout-btn").click()
    page.wait_for_url(f"{live_server}/checkout.html", wait_until="domcontentloaded", timeout=5000)
    page.wait_for_function(
        (
            "() => document.querySelector('#selected-address-card')"
            "?.textContent?.includes('全链路演示用户')"
            " && document.querySelector('#order-items')?.textContent?.includes('明制襦裙')"
        ),
        timeout=5000,
    )
    page.locator("#note").fill("完整演示链路自动下单")
    page.locator("#place-order-btn").click()
    page.locator("#orderSuccessModal").wait_for(timeout=5000)
    page.wait_for_function(
        (
            "() => document.querySelector('#order-success-recommendation-section')"
            " && !document.querySelector('#order-success-recommendation-section')"
            "?.classList.contains('d-none')"
            " && document.querySelector('#order-success-recommendations')"
            "?.textContent?.length > 0"
        ),
        timeout=5000,
    )
    order_no = page.locator("#order-number").text_content()
    assert order_no is not None and order_no.startswith("SYG")

    page.goto(f"{live_server}/orders.html", wait_until="domcontentloaded")
    page.locator("#orders-list .order-list-item").wait_for(timeout=5000)
    page.wait_for_function(
        "expectedOrderNo => {"
        "  const orderNo = document.querySelector('#order-no')?.textContent || '';"
        "  const detail = document.querySelector('#order-detail')?.textContent || '';"
        "  const status = document.querySelector('#order-status')?.textContent || '';"
        "  return orderNo.includes(expectedOrderNo)"
        "    && detail.includes('明制襦裙')"
        "    && status.includes('已支付');"
        "}",
        arg=order_no,
        timeout=5000,
    )

    create_review(live_server, access_token, product["id"], review_content)

    page.goto(f"{live_server}/product.html?id={product['id']}", wait_until="domcontentloaded")
    page.locator("#reviews-tab").click()
    page.wait_for_function(
        "expectedReview => {"
        "  const container = document.querySelector('#reviews-container')?.textContent || '';"
        "  const summary = document.querySelector('#reviews-total-copy')?.textContent || '';"
        "  return container.includes(expectedReview) && summary.includes('1 条评价');"
        "}",
        arg=review_content,
        timeout=5000,
    )

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

    create_preference_trace(live_server, access_token, product, "春日汉服")
    updated_recommendations = get_recommendations(live_server, access_token)[:3]
    assert len(updated_recommendations) == 3
    assert updated_recommendations[0]["reason"]
    assert updated_recommendations[0]["source_label"]
    assert any(item["id"] != product["id"] for item in updated_recommendations)

    page.goto(f"{live_server}/index.html", wait_until="domcontentloaded")
    page.wait_for_function(
        "([expectedName, expectedReason]) => {"
        "  const container = document.querySelector('#home-featured-products')?.textContent || '';"
        "  const copy = document.querySelector('#home-recommendation-copy')?.textContent || '';"
        "  return container.includes(expectedName)"
        "    && container.includes(expectedReason)"
        "    && copy.includes('个性化推荐');"
        "}",
        arg=[updated_recommendations[0]["name"], updated_recommendations[0]["reason"]],
        timeout=5000,
    )
    assert (
        updated_recommendations[0]["source_label"]
        in page.locator("#home-featured-products").text_content()
    )

    context.close()
