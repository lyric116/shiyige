def test_product_page_loads_real_product_detail(browser, live_server) -> None:
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/product.html?id=18", wait_until="domcontentloaded")
    page.get_by_text("上元灯会礼盒").wait_for(timeout=5000)

    assert page.locator("#product-name").text_content() == "上元灯会礼盒"
    assert page.locator("#product-category").text_content() == "礼盒"
    assert page.locator("#product-price").text_content() == "¥319.00"
    assert "节庆氛围套装" in page.locator("#product-specs").text_content()
    page.get_by_text("端午祈福礼盒").wait_for(timeout=5000)
    assert "明制襦裙" not in page.locator("#product-container").text_content()

    context.close()
