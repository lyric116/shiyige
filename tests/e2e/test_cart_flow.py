import uuid

import httpx


def test_product_page_and_cart_page_use_real_cart_api(browser, live_server) -> None:
    email = f"cart-{uuid.uuid4().hex[:8]}@example.com"
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": "cartflow",
            "email": email,
            "password": "secret-pass-123",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert register_response.status_code == 201

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/login.html", wait_until="domcontentloaded")
    page.locator("#email").fill(email)
    page.locator("#password").fill("secret-pass-123")
    page.locator("#login-form button[type='submit']").click()
    page.wait_for_url(f"{live_server}/index.html", wait_until="domcontentloaded", timeout=5000)

    page.goto(f"{live_server}/product.html?id=13", wait_until="domcontentloaded")
    page.get_by_text("点翠发簪").wait_for(timeout=5000)
    page.locator("#quantity").fill("2")
    page.locator("#add-to-cart-form button[type='submit']").click()
    page.get_by_text("商品已成功加入购物车").wait_for(timeout=5000)

    page.goto(f"{live_server}/cart.html", wait_until="domcontentloaded")
    page.get_by_text("点翠发簪").wait_for(timeout=5000)
    page.wait_for_function(
        "() => document.querySelector('#cart-recommendation-panel')"
        "  && !document.querySelector('#cart-recommendation-panel')?.classList.contains('d-none')"
        "  && document.querySelector('#cart-recommendation-list')?.textContent?.includes('相似商品')",
        timeout=5000,
    )
    assert page.locator(".cart-quantity").input_value() == "2"
    assert "购物车搭配推荐" in page.locator("#cart-recommendation-panel").text_content()

    page.locator(".cart-quantity-increase").click()
    page.wait_for_function(
        "() => document.querySelector('.cart-quantity')?.value === '3'"
    )
    assert page.locator("#cart-total").text_content() == "¥397.00"

    page.locator(".cart-item-remove").click()
    page.locator("#empty-cart").wait_for(timeout=5000)
    assert "您的购物车是空的" in page.locator("#empty-cart").text_content()

    context.close()
