import uuid

import httpx


def register_and_login_api(live_server, email: str, password: str) -> str:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": f"rec-ui-{uuid.uuid4().hex[:6]}",
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


def fetch_product_by_keyword(live_server, keyword: str) -> dict:
    product_list_response = httpx.get(
        f"{live_server}/api/v1/products",
        params={"q": keyword},
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


def create_user_preference_trace(live_server, access_token: str, product: dict, query: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}

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


def test_recommendation_and_semantic_search_ui(browser, live_server) -> None:
    password = "secret-pass-123"
    first_email = f"rec-ui-a-{uuid.uuid4().hex[:8]}@example.com"
    second_email = f"rec-ui-b-{uuid.uuid4().hex[:8]}@example.com"

    first_token = register_and_login_api(live_server, first_email, password)
    second_token = register_and_login_api(live_server, second_email, password)

    hanfu_product = fetch_product_by_keyword(live_server, "明制襦裙")
    accessory_product = fetch_product_by_keyword(live_server, "点翠发簪")

    create_user_preference_trace(live_server, first_token, hanfu_product, "春日汉服")
    create_user_preference_trace(live_server, second_token, accessory_product, "古风发簪")

    first_recommendation_response = httpx.get(
        f"{live_server}/api/v1/products/recommendations",
        headers={"Authorization": f"Bearer {first_token}"},
        timeout=5.0,
        trust_env=False,
    )
    second_recommendation_response = httpx.get(
        f"{live_server}/api/v1/products/recommendations",
        headers={"Authorization": f"Bearer {second_token}"},
        timeout=5.0,
        trust_env=False,
    )
    assert first_recommendation_response.status_code == 200
    assert second_recommendation_response.status_code == 200

    first_recommendations = first_recommendation_response.json()["data"]["items"][:3]
    second_recommendations = second_recommendation_response.json()["data"]["items"][:3]
    assert [item["id"] for item in first_recommendations] != [
        item["id"] for item in second_recommendations
    ]

    first_recommendation = first_recommendations[0]
    second_recommendation = second_recommendations[0]
    second_recommendation_ids = {item["id"] for item in second_recommendations}
    first_recommendation_ids = {item["id"] for item in first_recommendations}
    first_unique_recommendation = next(
        item for item in first_recommendations if item["id"] not in second_recommendation_ids
    )
    second_unique_recommendation = next(
        item for item in second_recommendations if item["id"] not in first_recommendation_ids
    )

    related_response = httpx.get(
        f"{live_server}/api/v1/products/{accessory_product['id']}/related",
        params={"limit": 3},
        timeout=5.0,
        trust_env=False,
    )
    assert related_response.status_code == 200
    related_item = related_response.json()["data"]["items"][0]

    semantic_response = httpx.post(
        f"{live_server}/api/v1/search/semantic",
        json={
            "query": "适合春日出游的素雅汉服",
            "limit": 3,
        },
        timeout=5.0,
        trust_env=False,
    )
    assert semantic_response.status_code == 200
    semantic_item = semantic_response.json()["data"]["items"][0]

    first_context = browser.new_context(base_url=live_server)
    first_page = first_context.new_page()
    login_through_page(first_page, live_server, first_email, password)
    first_page.wait_for_function(
        "([expectedName, expectedReason]) => {"
        "  const container = document.querySelector('#home-featured-products');"
        "  return Boolean(container?.textContent?.includes(expectedName))"
        "    && Boolean(container?.textContent?.includes(expectedReason));"
        "}",
        arg=[first_recommendation["name"], first_recommendation["reason"]],
        timeout=5000,
    )
    assert "猜你喜欢" in first_page.locator("#home-recommendation-title").text_content()
    assert (
        first_recommendation["name"] in first_page.locator("#home-featured-products").text_content()
    )
    assert (
        first_recommendation["reason"]
        in first_page.locator("#home-featured-products").text_content()
    )
    assert (
        first_recommendation["source_label"]
        in first_page.locator("#home-featured-products").text_content()
    )
    assert (
        first_unique_recommendation["name"]
        in first_page.locator("#home-featured-products").text_content()
    )
    first_context.close()

    second_context = browser.new_context(base_url=live_server)
    second_page = second_context.new_page()
    login_through_page(second_page, live_server, second_email, password)
    second_page.wait_for_function(
        "([expectedName, expectedReason]) => {"
        "  const container = document.querySelector('#home-featured-products');"
        "  return Boolean(container?.textContent?.includes(expectedName))"
        "    && Boolean(container?.textContent?.includes(expectedReason));"
        "}",
        arg=[second_recommendation["name"], second_recommendation["reason"]],
        timeout=5000,
    )
    assert (
        second_recommendation["name"]
        in second_page.locator("#home-featured-products").text_content()
    )
    assert (
        second_recommendation["reason"]
        in second_page.locator("#home-featured-products").text_content()
    )
    assert (
        second_recommendation["source_label"]
        in second_page.locator("#home-featured-products").text_content()
    )
    assert (
        second_unique_recommendation["name"]
        in second_page.locator("#home-featured-products").text_content()
    )
    assert (
        first_unique_recommendation["name"]
        not in second_page.locator("#home-featured-products").text_content()
    )
    second_context.close()

    product_context = browser.new_context(base_url=live_server)
    product_page = product_context.new_page()
    product_page.goto(
        f"{live_server}/product.html?id={accessory_product['id']}",
        wait_until="domcontentloaded",
    )
    product_page.locator("#related-products .product-card").first.wait_for(timeout=5000)
    assert related_item["name"] in product_page.locator("#related-products").text_content()
    assert related_item["reason"] in product_page.locator("#related-products").text_content()
    assert related_item["source_label"] in product_page.locator("#related-products").text_content()
    product_context.close()

    search_context = browser.new_context(base_url=live_server)
    search_page = search_context.new_page()
    search_page.goto(f"{live_server}/category.html", wait_until="domcontentloaded")
    search_page.locator("#catalog-search-input").fill("适合春日出游的素雅汉服")
    search_page.locator("#search-mode-select").select_option("semantic")
    search_page.locator("#search-entry-submit").click()
    search_page.wait_for_function(
        "([expectedHeader, expectedName, expectedReason]) => {"
        "  const header = document.querySelector('#category-name')?.textContent?.trim();"
        "  const container = document.querySelector('#products-container')?.textContent || '';"
        "  return header === expectedHeader"
        "    && container.includes(expectedName)"
        "    && container.includes(expectedReason);"
        "}",
        arg=[
            "语义搜索：适合春日出游的素雅汉服",
            semantic_item["name"],
            semantic_item["reason"],
        ],
        timeout=5000,
    )
    assert (
        search_page.locator("#category-name").text_content() == "语义搜索：适合春日出游的素雅汉服"
    )
    assert semantic_item["name"] in search_page.locator("#products-container").text_content()
    assert semantic_item["reason"] in search_page.locator("#products-container").text_content()
    assert "语义相关" in search_page.locator("#products-container").text_content()
    assert "文化标签匹配" in search_page.locator("#products-container").text_content()
    search_context.close()
