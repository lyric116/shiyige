def test_home_page_loads_categories_and_featured_products(browser, live_server) -> None:
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/index.html", wait_until="domcontentloaded")
    page.locator("#home-category-list").get_by_role("heading", name="礼盒").wait_for(timeout=5000)
    page.get_by_text("端午祈福礼盒").wait_for(timeout=5000)

    context.close()


def test_category_page_loads_real_product_list(browser, live_server) -> None:
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/category.html?id=4", wait_until="domcontentloaded")
    page.locator("#category-name").wait_for(timeout=5000)

    assert page.locator("#category-name").text_content() == "饰品"
    page.get_by_text("点翠发簪").wait_for(timeout=5000)
    assert "明制襦裙" not in page.locator("#products-container").text_content()

    context.close()
