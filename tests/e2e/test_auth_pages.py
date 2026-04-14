import httpx


def test_register_page_uses_real_register_api(browser, live_server) -> None:
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/register.html", wait_until="domcontentloaded")
    page.locator("#username").fill("e2euser")
    page.locator("#email").fill("e2e@example.com")
    page.locator("#password").fill("secret-pass-123")
    page.locator("#confirm_password").fill("secret-pass-123")
    page.locator("#agree-terms").check()
    page.locator("#register-form button[type='submit']").click()

    page.wait_for_url(
        f"{live_server}/login.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )

    login_response = httpx.post(
        f"{live_server}/api/v1/auth/login",
        json={
            "email": "e2e@example.com",
            "password": "secret-pass-123",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert login_response.status_code == 200
    context.close()


def test_login_page_uses_real_login_api_and_stores_session(browser, live_server) -> None:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "secret-pass-123",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert register_response.status_code == 201

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    page.goto(f"{live_server}/login.html", wait_until="domcontentloaded")
    page.locator("#email").fill("login@example.com")
    page.locator("#password").fill("secret-pass-123")
    page.locator("#login-form button[type='submit']").click()

    page.wait_for_url(
        f"{live_server}/index.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )

    access_token = page.evaluate("window.sessionStorage.getItem('shiyige_access_token')")
    cookies = context.cookies()

    assert access_token is not None
    assert any(cookie["name"] == "refresh_token" for cookie in cookies)
    context.close()
