def test_search_flow_uses_keyword_api_and_shows_matching_results(browser, live_server) -> None:
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/index.html", wait_until="domcontentloaded")
    page.locator(".search-input").first.fill("点翠")
    page.locator('datalist option[value="点翠发簪"]').wait_for(
        state="attached",
        timeout=5000,
    )
    page.locator(".search-form").first.locator('button[type="submit"]').click()

    page.locator("#category-name").wait_for(timeout=5000)
    assert page.locator("#category-name").text_content() == "搜索：点翠"
    page.get_by_text("点翠发簪").wait_for(timeout=5000)
    assert "明制襦裙" not in page.locator("#products-container").text_content()

    context.close()
